import json
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.chat_dependencies import get_chat_service
from app.core.dependencies import get_current_user
from app.main import app
from app.models.user import User
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessageCreatedEvent,
    ChatResponseDeltaEvent,
)
from app.services.chat_errors import (
    ChatConversationBusyError,
    ChatConversationNotFoundError,
    ChatDailyLimitError,
    ChatDisabledError,
    ChatGlobalConcurrencyError,
    ChatRateLimitError,
    ChatRegenerationConflictError,
    ChatUserConcurrencyError,
)
from app.services.chat_generation import PreparedGeneration
from app.services.chat_service import ChatService

BASE_URL = '/api/v1/chat'
MESSAGE_URL = f'{BASE_URL}/conversations/10/messages'

GENERATION_ID = UUID(
    '123e4567-e89b-12d3-a456-426614174000',
)


@pytest.fixture
def chat_service():
    service = AsyncMock(spec=ChatService)
    service.stream_generation = MagicMock()
    return service


@pytest.fixture
async def chat_client(chat_service):
    previous_overrides = app.dependency_overrides.copy()

    app.dependency_overrides[get_chat_service] = lambda: chat_service

    app.dependency_overrides[get_current_user] = lambda: User(
        id=7, is_active=True
    )

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


async def test_send_chat_message(
    chat_client,
    chat_service,
):
    prepared = MagicMock(spec=PreparedGeneration)

    created = ChatMessageCreatedEvent(
        type='message.created',
        conversation_id=10,
        generation_id=GENERATION_ID,
        assistant_message_id=21,
        user_message_id=20,
    )

    delta = ChatResponseDeltaEvent(
        type='response.delta',
        conversation_id=10,
        generation_id=GENERATION_ID,
        assistant_message_id=21,
        delta='Olá! Como posso ajudar?',
    )

    async def events():
        yield created
        yield delta

    chat_service.prepare_generation.return_value = prepared
    chat_service.stream_generation.return_value = events()

    response = await chat_client.post(
        MESSAGE_URL,
        json={'content': 'Olá'},
        headers={'Accept': 'text/event-stream'},
    )

    assert response.status_code == 200
    assert response.headers['content-type'].startswith(
        'text/event-stream',
    )
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-accel-buffering'] == 'no'

    frames = response.text.strip().split('\n\n')

    assert len(frames) == 2

    assert frames[0].startswith(
        'event: message.created\n',
    )
    assert frames[1].startswith(
        'event: response.delta\n',
    )

    payloads = [
        json.loads(
            frame.splitlines()[1].removeprefix('data: '),
        )
        for frame in frames
    ]

    assert payloads == [
        created.model_dump(mode='json'),
        delta.model_dump(mode='json'),
    ]

    chat_service.prepare_generation.assert_awaited_once_with(
        user_id=7,
        conversation_id=10,
        data=ChatMessageCreate(content='Olá'),
    )

    chat_service.stream_generation.assert_called_once_with(
        prepared,
    )


@pytest.mark.parametrize(
    ('error', 'expected_status'),
    [
        (ChatConversationNotFoundError, 404),
        (ChatConversationBusyError, 409),
        (ChatDailyLimitError, 429),
        (ChatRateLimitError, 429),
        (ChatUserConcurrencyError, 429),
        (ChatGlobalConcurrencyError, 503),
        (ChatDisabledError, 503),
    ],
)
async def test_send_chat_message_preparation_error(
    chat_client,
    chat_service,
    error,
    expected_status,
):
    chat_service.prepare_generation.side_effect = error()

    response = await chat_client.post(
        MESSAGE_URL,
        json={'content': 'Olá'},
    )

    assert response.status_code == expected_status
    assert response.headers['content-type'].startswith(
        'application/json',
    )
    assert 'detail' in response.json()

    chat_service.stream_generation.assert_not_called()


@pytest.mark.parametrize(
    'payload',
    [
        {},
        {'content': ''},
        {'content': '   '},
        {'content': 'a' * 8001},
        {'content': 'Olá', 'user_id': 999},
    ],
)
async def test_send_chat_message_invalid_payload(
    chat_client,
    chat_service,
    payload,
):
    response = await chat_client.post(
        MESSAGE_URL,
        json=payload,
    )

    assert response.status_code == 422

    chat_service.prepare_generation.assert_not_awaited()
    chat_service.stream_generation.assert_not_called()


async def test_send_chat_message_invalid_conversation_id(
    chat_client,
    chat_service,
):
    response = await chat_client.post(
        f'{BASE_URL}/conversations/0/messages',
        json={'content': 'Olá'},
    )

    assert response.status_code == 422

    chat_service.prepare_generation.assert_not_awaited()
    chat_service.stream_generation.assert_not_called()


async def test_send_chat_message_requires_authentication(
    chat_client,
    chat_service,
):
    app.dependency_overrides.pop(get_current_user)

    response = await chat_client.post(
        MESSAGE_URL,
        json={'content': 'Olá'},
    )

    assert response.status_code == 401
    assert response.headers['www-authenticate'] == 'Bearer'

    chat_service.prepare_generation.assert_not_awaited()
    chat_service.stream_generation.assert_not_called()


REGENERATE_URL = f'{MESSAGE_URL}/21/regenerate'


async def test_regenerate_chat_message(
    chat_client,
    chat_service,
):
    prepared = MagicMock(spec=PreparedGeneration)

    created = ChatMessageCreatedEvent(
        type='message.created',
        conversation_id=10,
        generation_id=GENERATION_ID,
        assistant_message_id=22,
        user_message_id=20,
        regenerated_from_id=21,
    )

    delta = ChatResponseDeltaEvent(
        type='response.delta',
        conversation_id=10,
        generation_id=GENERATION_ID,
        assistant_message_id=22,
        delta='Uma nova resposta.',
    )

    async def events():
        yield created
        yield delta

    chat_service.prepare_regeneration.return_value = prepared
    chat_service.stream_generation.return_value = events()

    response = await chat_client.post(
        REGENERATE_URL,
        headers={'Accept': 'text/event-stream'},
    )

    assert response.status_code == 200
    assert response.headers['content-type'].startswith(
        'text/event-stream',
    )
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-accel-buffering'] == 'no'

    frames = response.text.strip().split('\n\n')

    assert len(frames) == 2

    assert frames[0].startswith(
        'event: message.created\n',
    )
    assert frames[1].startswith(
        'event: response.delta\n',
    )

    payloads = [
        json.loads(
            frame.splitlines()[1].removeprefix('data: '),
        )
        for frame in frames
    ]

    assert payloads == [
        created.model_dump(mode='json'),
        delta.model_dump(mode='json'),
    ]

    chat_service.prepare_regeneration.assert_awaited_once_with(
        user_id=7,
        conversation_id=10,
        message_id=21,
    )

    chat_service.stream_generation.assert_called_once_with(
        prepared,
    )

    chat_service.prepare_generation.assert_not_awaited()


@pytest.mark.parametrize(
    ('error', 'expected_status'),
    [
        (ChatConversationNotFoundError, 404),
        (ChatConversationBusyError, 409),
        (ChatRegenerationConflictError, 409),
        (ChatDailyLimitError, 429),
        (ChatRateLimitError, 429),
        (ChatUserConcurrencyError, 429),
        (ChatGlobalConcurrencyError, 503),
        (ChatDisabledError, 503),
    ],
)
async def test_regenerate_chat_message_preparation_error(
    chat_client,
    chat_service,
    error,
    expected_status,
):
    chat_service.prepare_regeneration.side_effect = error()

    response = await chat_client.post(
        REGENERATE_URL,
    )

    assert response.status_code == expected_status
    assert response.headers['content-type'].startswith(
        'application/json',
    )
    assert 'detail' in response.json()

    chat_service.stream_generation.assert_not_called()


@pytest.mark.parametrize(
    ('conversation_id', 'message_id'),
    [
        (0, 21),
        (10, 0),
        (10, -1),
        (10, 2_147_483_648),
    ],
)
async def test_regenerate_chat_message_invalid_ids(
    chat_client,
    chat_service,
    conversation_id,
    message_id,
):
    response = await chat_client.post(
        f'{BASE_URL}/conversations/{conversation_id}'
        f'/messages/{message_id}/regenerate',
    )

    assert response.status_code == 422

    chat_service.prepare_regeneration.assert_not_awaited()
    chat_service.stream_generation.assert_not_called()


async def test_regenerate_chat_requires_authentication(
    chat_client,
    chat_service,
):
    app.dependency_overrides.pop(get_current_user)

    response = await chat_client.post(
        REGENERATE_URL,
    )

    assert response.status_code == 401
    assert response.headers['www-authenticate'] == 'Bearer'

    chat_service.prepare_regeneration.assert_not_awaited()
    chat_service.stream_generation.assert_not_called()
