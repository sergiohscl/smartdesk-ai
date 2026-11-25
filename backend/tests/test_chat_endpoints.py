from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.chat_dependencies import get_chat_service
from app.core.dependencies import get_current_user
from app.main import app
from app.models.user import User
from app.schemas.chat import (
    ChatCancellationRequest,
    ChatCancellationResponse,
    ChatConversationCreate,
    ChatConversationListResponse,
    ChatConversationPublic,
    ChatConversationUpdate,
    ChatMessageListResponse,
    ChatMessagePublic,
    ChatUsageResponse,
)
from app.services.chat_errors import (
    ChatConversationBusyError,
    ChatConversationNotFoundError,
    ChatGenerationConflictError,
)
from app.services.chat_service import ChatService

BASE_URL = '/api/v1/chat'


@pytest.fixture
def chat_service():
    return AsyncMock(spec=ChatService)


@pytest.fixture
def chat_user():
    return User(
        id=7,
        is_active=True,
    )


@pytest.fixture
def conversation():
    now = datetime.now(UTC)

    return ChatConversationPublic(
        id=10,
        title='Suporte PostgreSQL',
        generation_status='idle',
        generation_id=None,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
async def chat_client(chat_service, chat_user):
    previous_overrides = app.dependency_overrides.copy()

    app.dependency_overrides[get_chat_service] = lambda: chat_service

    app.dependency_overrides[get_current_user] = lambda: chat_user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url='http://test',
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(
            previous_overrides,
        )


async def test_create_chat_conversation(
    chat_client,
    chat_service,
    conversation,
):
    chat_service.create_conversation.return_value = conversation

    response = await chat_client.post(
        f'{BASE_URL}/conversations',
        json={'title': 'Suporte PostgreSQL'},
    )

    assert response.status_code == 201
    assert response.json() == conversation.model_dump(
        mode='json',
    )

    chat_service.create_conversation.assert_awaited_once_with(
        user_id=7,
        data=ChatConversationCreate(
            title='Suporte PostgreSQL',
        ),
    )


async def test_create_chat_conversation_default_title(
    chat_client,
    chat_service,
    conversation,
):
    chat_service.create_conversation.return_value = conversation.model_copy(
        update={'title': 'Nova conversa'},
    )

    response = await chat_client.post(
        f'{BASE_URL}/conversations',
        json={},
    )

    assert response.status_code == 201
    assert response.json()['title'] == 'Nova conversa'

    chat_service.create_conversation.assert_awaited_once_with(
        user_id=7,
        data=ChatConversationCreate(),
    )


async def test_create_chat_rejects_external_owner(
    chat_client,
    chat_service,
):
    response = await chat_client.post(
        f'{BASE_URL}/conversations',
        json={
            'title': 'Nova conversa',
            'user_id': 999,
        },
    )

    assert response.status_code == 422

    chat_service.create_conversation.assert_not_awaited()


async def test_list_chat_conversations(
    chat_client,
    chat_service,
    conversation,
):
    chat_service.list_conversations.return_value = (
        ChatConversationListResponse(
            items=[conversation],
            total=21,
            page=2,
            page_size=20,
            pages=2,
        )
    )

    response = await chat_client.get(
        f'{BASE_URL}/conversations',
        params={'page': 2, 'page_size': 20},
    )

    assert response.status_code == 200

    data = response.json()

    assert data['total'] == 21
    assert data['page'] == 2
    assert data['pages'] == 2
    assert len(data['items']) == 1

    chat_service.list_conversations.assert_awaited_once_with(
        user_id=7,
        page=2,
        page_size=20,
    )


async def test_list_chat_conversations_default_pagination(
    chat_client,
    chat_service,
):
    chat_service.list_conversations.return_value = (
        ChatConversationListResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            pages=0,
        )
    )

    response = await chat_client.get(
        f'{BASE_URL}/conversations',
    )

    assert response.status_code == 200
    assert response.json()['items'] == []

    chat_service.list_conversations.assert_awaited_once_with(
        user_id=7,
        page=1,
        page_size=20,
    )


@pytest.mark.parametrize(
    'params',
    [
        {'page': 0},
        {'page_size': 0},
        {'page_size': 101},
    ],
)
async def test_list_chat_invalid_pagination(
    chat_client,
    chat_service,
    params,
):
    response = await chat_client.get(
        f'{BASE_URL}/conversations',
        params=params,
    )

    assert response.status_code == 422

    chat_service.list_conversations.assert_not_awaited()


async def test_get_chat_conversation(
    chat_client,
    chat_service,
    conversation,
):
    chat_service.get_conversation.return_value = conversation

    response = await chat_client.get(
        f'{BASE_URL}/conversations/10',
    )

    assert response.status_code == 200
    assert response.json()['id'] == 10

    chat_service.get_conversation.assert_awaited_once_with(
        user_id=7,
        conversation_id=10,
    )


async def test_get_chat_conversation_not_found(
    chat_client,
    chat_service,
):
    chat_service.get_conversation.side_effect = ChatConversationNotFoundError()

    response = await chat_client.get(
        f'{BASE_URL}/conversations/999',
    )

    assert response.status_code == 404
    assert response.json() == {
        'detail': 'Conversation not found.',
    }


@pytest.mark.parametrize(
    'conversation_id',
    ['0', '-1', 'invalid', '2147483648'],
)
async def test_get_chat_invalid_conversation_id(
    chat_client,
    chat_service,
    conversation_id,
):
    response = await chat_client.get(
        f'{BASE_URL}/conversations/{conversation_id}',
    )

    assert response.status_code == 422

    chat_service.get_conversation.assert_not_awaited()


async def test_chat_requires_authentication(
    chat_client,
    chat_service,
):
    app.dependency_overrides.pop(get_current_user)

    response = await chat_client.get(
        f'{BASE_URL}/conversations',
    )

    assert response.status_code == 401
    assert response.headers['www-authenticate'] == 'Bearer'

    chat_service.list_conversations.assert_not_awaited()


async def test_update_chat_conversation(
    chat_client,
    chat_service,
    conversation,
):
    updated = conversation.model_copy(
        update={'title': 'Novo titulo'},
    )

    chat_service.update_conversation.return_value = updated

    response = await chat_client.patch(
        f'{BASE_URL}/conversations/10',
        json={'title': 'Novo titulo'},
    )

    assert response.status_code == 200
    assert response.json() == updated.model_dump(
        mode='json',
    )

    chat_service.update_conversation.assert_awaited_once_with(
        user_id=7,
        conversation_id=10,
        data=ChatConversationUpdate(
            title='Novo titulo',
        ),
    )


async def test_update_chat_conversation_not_found(
    chat_client,
    chat_service,
):
    chat_service.update_conversation.side_effect = (
        ChatConversationNotFoundError()
    )

    response = await chat_client.patch(
        f'{BASE_URL}/conversations/999',
        json={'title': 'Novo titulo'},
    )

    assert response.status_code == 404
    assert response.json() == {
        'detail': 'Conversation not found.',
    }


@pytest.mark.parametrize(
    'payload',
    [
        {},
        {'title': None},
        {'title': '   '},
        {'title': 'a' * 151},
        {'title': 'Novo titulo', 'user_id': 999},
    ],
)
async def test_update_chat_invalid_payload(
    chat_client,
    chat_service,
    payload,
):
    response = await chat_client.patch(
        f'{BASE_URL}/conversations/10',
        json=payload,
    )

    assert response.status_code == 422

    chat_service.update_conversation.assert_not_awaited()


async def test_delete_chat_conversation(
    chat_client,
    chat_service,
):
    chat_service.delete_conversation.return_value = None

    response = await chat_client.delete(
        f'{BASE_URL}/conversations/10',
    )

    assert response.status_code == 204
    assert response.content == b''

    chat_service.delete_conversation.assert_awaited_once_with(
        user_id=7,
        conversation_id=10,
    )


async def test_delete_chat_conversation_not_found(
    chat_client,
    chat_service,
):
    chat_service.delete_conversation.side_effect = (
        ChatConversationNotFoundError()
    )

    response = await chat_client.delete(
        f'{BASE_URL}/conversations/999',
    )

    assert response.status_code == 404
    assert response.json() == {
        'detail': 'Conversation not found.',
    }


async def test_delete_chat_conversation_busy(
    chat_client,
    chat_service,
):
    chat_service.delete_conversation.side_effect = ChatConversationBusyError()

    response = await chat_client.delete(
        f'{BASE_URL}/conversations/10',
    )

    assert response.status_code == 409
    assert response.json() == {
        'detail': 'Conversation has an active generation.',
    }


async def test_list_chat_messages(
    chat_client,
    chat_service,
):
    now = datetime.now(UTC)

    message = ChatMessagePublic(
        id=20,
        conversation_id=10,
        role='user',
        status='completed',
        content='Como verificar o PostgreSQL?',
        model=None,
        generation_id=None,
        input_tokens=None,
        output_tokens=None,
        reply_to_message_id=None,
        regenerated_from_id=None,
        is_active=True,
        created_at=now,
        completed_at=now,
    )

    history = ChatMessageListResponse(
        items=[message],
        total=21,
        page=2,
        page_size=20,
        pages=2,
    )

    chat_service.list_messages.return_value = history

    response = await chat_client.get(
        f'{BASE_URL}/conversations/10/messages',
        params={'page': 2, 'page_size': 20},
    )

    assert response.status_code == 200
    assert response.json() == history.model_dump(
        mode='json',
    )

    chat_service.list_messages.assert_awaited_once_with(
        user_id=7,
        conversation_id=10,
        page=2,
        page_size=20,
    )


async def test_list_chat_messages_empty(
    chat_client,
    chat_service,
):
    chat_service.list_messages.return_value = ChatMessageListResponse(
        items=[],
        total=0,
        page=1,
        page_size=50,
        pages=0,
    )

    response = await chat_client.get(
        f'{BASE_URL}/conversations/10/messages',
    )

    assert response.status_code == 200
    assert response.json()['items'] == []
    assert response.json()['total'] == 0

    chat_service.list_messages.assert_awaited_once_with(
        user_id=7,
        conversation_id=10,
        page=1,
        page_size=50,
    )


async def test_list_chat_messages_not_found(
    chat_client,
    chat_service,
):
    chat_service.list_messages.side_effect = ChatConversationNotFoundError()

    response = await chat_client.get(
        f'{BASE_URL}/conversations/999/messages',
    )

    assert response.status_code == 404
    assert response.json() == {
        'detail': 'Conversation not found.',
    }


@pytest.mark.parametrize(
    'params',
    [
        {'page': 0},
        {'page_size': 101},
    ],
)
async def test_list_chat_messages_invalid_pagination(
    chat_client,
    chat_service,
    params,
):
    response = await chat_client.get(
        f'{BASE_URL}/conversations/10/messages',
        params=params,
    )

    assert response.status_code == 422

    chat_service.list_messages.assert_not_awaited()


@pytest.mark.parametrize(
    ('used', 'remaining', 'input_tokens', 'output_tokens'),
    [
        (0, 50, 0, 0),
        (12, 38, 4200, 1850),
        (50, 0, 15000, 6000),
    ],
)
async def test_get_chat_usage(
    chat_client,
    chat_service,
    used,
    remaining,
    input_tokens,
    output_tokens,
):
    usage = ChatUsageResponse(
        daily_limit=50,
        used=used,
        remaining=remaining,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        resets_at=datetime(
            2026,
            11,
            26,
            tzinfo=UTC,
        ),
    )

    chat_service.get_usage.return_value = usage

    response = await chat_client.get(
        f'{BASE_URL}/usage',
    )

    assert response.status_code == 200
    assert response.json() == usage.model_dump(
        mode='json',
    )

    chat_service.get_usage.assert_awaited_once_with(
        user_id=7,
    )


async def test_chat_usage_requires_authentication(
    chat_client,
    chat_service,
):
    app.dependency_overrides.pop(get_current_user)

    response = await chat_client.get(
        f'{BASE_URL}/usage',
    )

    assert response.status_code == 401
    assert response.headers['www-authenticate'] == 'Bearer'

    chat_service.get_usage.assert_not_awaited()


CANCEL_GENERATION_ID = UUID(
    '123e4567-e89b-12d3-a456-426614174000',
)


async def test_cancel_chat_generation(
    chat_client,
    chat_service,
):
    cancellation = ChatCancellationResponse(
        conversation_id=10,
        generation_id=CANCEL_GENERATION_ID,
        cancellation_requested=True,
    )

    chat_service.cancel_generation.return_value = cancellation

    response = await chat_client.post(
        f'{BASE_URL}/conversations/10/cancel',
        json={
            'generation_id': str(CANCEL_GENERATION_ID),
        },
    )

    assert response.status_code == 202
    assert response.json() == cancellation.model_dump(
        mode='json',
    )

    chat_service.cancel_generation.assert_awaited_once_with(
        user_id=7,
        conversation_id=10,
        data=ChatCancellationRequest(
            generation_id=CANCEL_GENERATION_ID,
        ),
    )


@pytest.mark.parametrize(
    ('error_type', 'expected_status', 'expected_detail'),
    [
        (
            ChatConversationNotFoundError,
            404,
            'Conversation not found.',
        ),
        (
            ChatGenerationConflictError,
            409,
            'Generation is no longer active.',
        ),
    ],
)
async def test_cancel_chat_generation_domain_error(
    chat_client,
    chat_service,
    error_type,
    expected_status,
    expected_detail,
):
    chat_service.cancel_generation.side_effect = error_type()

    response = await chat_client.post(
        f'{BASE_URL}/conversations/10/cancel',
        json={
            'generation_id': str(CANCEL_GENERATION_ID),
        },
    )

    assert response.status_code == expected_status
    assert response.json() == {
        'detail': expected_detail,
    }


@pytest.mark.parametrize(
    'payload',
    [
        {},
        {'generation_id': 'invalid-uuid'},
    ],
)
async def test_cancel_chat_generation_invalid_payload(
    chat_client,
    chat_service,
    payload,
):
    response = await chat_client.post(
        f'{BASE_URL}/conversations/10/cancel',
        json=payload,
    )

    assert response.status_code == 422

    chat_service.cancel_generation.assert_not_awaited()


async def test_cancel_chat_requires_authentication(
    chat_client,
    chat_service,
):
    app.dependency_overrides.pop(get_current_user)

    response = await chat_client.post(
        f'{BASE_URL}/conversations/10/cancel',
        json={
            'generation_id': str(CANCEL_GENERATION_ID),
        },
    )

    assert response.status_code == 401
    assert response.headers['www-authenticate'] == 'Bearer'

    chat_service.cancel_generation.assert_not_awaited()
