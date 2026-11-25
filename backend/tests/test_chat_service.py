from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_settings import SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import Settings
from app.models.chat_conversation import ChatConversation
from app.models.chat_message import (
    ChatMessage,
    ChatMessageRole,
    ChatMessageStatus,
)
from app.models.chat_usage import ChatUsage
from app.schemas.chat import (
    ChatConversationCreate,
    ChatConversationUpdate,
)
from app.services.chat_errors import (
    ChatConversationBusyError,
    ChatConversationNotFoundError,
)
from app.services.chat_service import ChatService
from app.services.providers import AIProvider


class IsolatedSettings(Settings):
    model_config = SettingsConfigDict(
        env_file=None,
        secrets_dir=None,
        env_prefix='SMARTDESK_CHAT_SERVICE_TEST_',
    )


@pytest.fixture
def session():
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    return session


@pytest.fixture
def service(session):
    settings = IsolatedSettings(
        DATABASE_URL='postgresql+asyncpg://fake:fake@localhost/fake',
        JWT_SECRET_KEY='fake-test-secret',
    )

    return ChatService(
        session=session,
        settings=settings,
        provider=MagicMock(spec=AIProvider),
    )


def make_conversation(conversation_id=1, user_id=1):
    now = datetime.now(UTC)

    return ChatConversation(
        id=conversation_id,
        user_id=user_id,
        title='Nova conversa',
        generation_status='idle',
        generation_id=None,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.parametrize(
    ('title', 'expected'),
    [
        (None, 'Nova conversa'),
        ('Suporte PostgreSQL', 'Suporte PostgreSQL'),
    ],
)
async def test_create_conversation(
    service,
    session,
    title,
    expected,
):
    async def refresh(conversation):
        now = datetime.now(UTC)
        conversation.id = 1
        conversation.generation_status = 'idle'
        conversation.generation_id = None
        conversation.created_at = now
        conversation.updated_at = now

    session.refresh.side_effect = refresh

    result = await service.create_conversation(
        user_id=1,
        data=ChatConversationCreate(title=title),
    )

    conversation = session.add.call_args.args[0]

    assert conversation.user_id == 1
    assert result.id == 1
    assert result.title == expected
    session.commit.assert_awaited_once()


async def test_get_conversation(service, session):
    session.execute.return_value = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = (
        make_conversation()
    )

    result = await service.get_conversation(
        user_id=1,
        conversation_id=1,
    )

    assert result.id == 1

    statement = session.execute.call_args.args[0]
    compiled = statement.compile()

    assert 'chat_conversations.user_id =' in str(compiled)
    assert 'chat_conversations.id =' in str(compiled)
    assert compiled.params['user_id_1'] == 1


async def test_get_conversation_not_found(service, session):
    session.execute.return_value = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(
        ChatConversationNotFoundError,
        match='Conversation not found.',
    ):
        await service.get_conversation(
            user_id=1,
            conversation_id=999,
        )


async def test_list_conversations(service, session):
    session.scalar.return_value = 21
    session.scalars.return_value = MagicMock()
    session.scalars.return_value.all.return_value = [
        make_conversation(1),
    ]

    result = await service.list_conversations(
        user_id=1,
        page=2,
        page_size=20,
    )

    assert result.total == 21
    assert result.pages == 2
    assert result.page == 2
    assert len(result.items) == 1

    statement = session.scalars.call_args.args[0]
    compiled = statement.compile()

    assert compiled.params['user_id_1'] == 1
    assert 'updated_at DESC' in str(compiled)
    assert 'id DESC' in str(compiled)


async def test_create_conversation_rolls_back(service, session):
    session.flush.side_effect = RuntimeError('Database failure.')

    with pytest.raises(
        RuntimeError,
        match='Database failure.',
    ):
        await service.create_conversation(
            user_id=1,
            data=ChatConversationCreate(),
        )

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


async def test_update_conversation(service, session):
    conversation = make_conversation()

    session.execute.return_value = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = conversation

    result = await service.update_conversation(
        user_id=1,
        conversation_id=1,
        data=ChatConversationUpdate(
            title='Novo título',
        ),
    )

    assert result.title == 'Novo título'
    assert conversation.title == 'Novo título'

    statement = session.execute.call_args.args[0]

    assert 'FOR UPDATE' in str(statement)
    assert statement.compile().params['user_id_1'] == 1

    session.commit.assert_awaited_once()


async def test_delete_conversation(service, session):
    session.execute.return_value = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = (
        make_conversation()
    )

    await service.delete_conversation(
        user_id=1,
        conversation_id=1,
    )

    assert session.execute.await_count == 2

    lookup = session.execute.await_args_list[0].args[0]
    deletion = session.execute.await_args_list[1].args[0]

    assert 'FOR UPDATE' in str(lookup)
    assert 'DELETE FROM chat_conversations' in str(deletion)
    assert deletion.compile().params['user_id_1'] == 1
    assert deletion.compile().params['id_1'] == 1

    session.commit.assert_awaited_once()


async def test_delete_generating_conversation(service, session):
    conversation = make_conversation()
    conversation.generation_status = 'generating'

    session.execute.return_value = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = conversation

    with pytest.raises(
        ChatConversationBusyError,
        match='active generation',
    ):
        await service.delete_conversation(
            user_id=1,
            conversation_id=1,
        )

    session.execute.assert_awaited_once()
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


@pytest.mark.parametrize('operation', ['update', 'delete'])
async def test_modify_conversation_not_found(
    service,
    session,
    operation,
):
    session.execute.return_value = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None

    if operation == 'update':
        action = service.update_conversation(
            user_id=1,
            conversation_id=999,
            data=ChatConversationUpdate(title='Novo título'),
        )
    else:
        action = service.delete_conversation(
            user_id=1,
            conversation_id=999,
        )

    with pytest.raises(
        ChatConversationNotFoundError,
        match='Conversation not found.',
    ):
        await action

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


async def test_update_conversation_rolls_back(service, session):
    session.execute.return_value = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = (
        make_conversation()
    )

    session.flush.side_effect = RuntimeError('Database failure.')

    with pytest.raises(
        RuntimeError,
        match='Database failure.',
    ):
        await service.update_conversation(
            user_id=1,
            conversation_id=1,
            data=ChatConversationUpdate(title='Novo título'),
        )

    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


def make_chat_message(message_id=1, conversation_id=1):
    now = datetime.now(UTC)

    return ChatMessage(
        id=message_id,
        conversation_id=conversation_id,
        role=ChatMessageRole.USER,
        status=ChatMessageStatus.COMPLETED,
        content='Como configurar o PostgreSQL?',
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


async def test_list_messages(service, session):
    session.execute.return_value = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = (
        make_conversation()
    )

    session.scalar.return_value = 52
    session.scalars.return_value = MagicMock()
    session.scalars.return_value.all.return_value = [
        make_chat_message(2),
        make_chat_message(1),
    ]

    result = await service.list_messages(
        user_id=1,
        conversation_id=1,
        page=2,
        page_size=50,
    )

    assert result.total == 52
    assert result.pages == 2
    assert result.page == 2
    assert result.page_size == 50
    assert [message.id for message in result.items] == [2, 1]

    statement = session.scalars.call_args.args[0]
    compiled = statement.compile()

    assert compiled.params['conversation_id_1'] == 1
    assert compiled.params['user_id_1'] == 1
    assert 'chat_messages.id DESC' in str(compiled)
    assert 'JOIN chat_conversations' in str(compiled)


async def test_list_messages_empty_conversation(service, session):
    session.execute.return_value = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = (
        make_conversation()
    )

    session.scalar.return_value = 0
    session.scalars.return_value = MagicMock()
    session.scalars.return_value.all.return_value = []

    result = await service.list_messages(
        user_id=1,
        conversation_id=1,
    )

    assert result.items == []
    assert result.total == 0
    assert result.pages == 0


async def test_list_messages_conversation_not_found(service, session):
    session.execute.return_value = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(
        ChatConversationNotFoundError,
        match='Conversation not found.',
    ):
        await service.list_messages(
            user_id=1,
            conversation_id=999,
        )

    session.scalar.assert_not_awaited()
    session.scalars.assert_not_awaited()


@pytest.mark.parametrize(
    ('page', 'page_size'),
    [
        (0, 50),
        (1, 101),
    ],
)
async def test_list_messages_invalid_pagination(
    service,
    session,
    page,
    page_size,
):
    with pytest.raises(
        ValueError,
        match='Invalid pagination parameters.',
    ):
        await service.list_messages(
            user_id=1,
            conversation_id=1,
            page=page,
            page_size=page_size,
        )

    session.execute.assert_not_awaited()


async def test_get_usage_without_record(service, session):
    session.execute.return_value = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None

    result = await service.get_usage(user_id=1)

    assert result.daily_limit == 50
    assert result.used == 0
    assert result.remaining == 50
    assert result.input_tokens == 0
    assert result.output_tokens == 0

    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.parametrize(
    ('used', 'remaining'),
    [
        (18, 32),
        (50, 0),
        (55, 0),
    ],
)
async def test_get_usage_with_record(
    service,
    session,
    used,
    remaining,
):
    today = datetime.now(UTC).date()

    usage = ChatUsage(
        user_id=1,
        usage_date=today,
        request_count=used,
        input_tokens=1200,
        output_tokens=400,
    )

    session.execute.return_value = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = usage

    result = await service.get_usage(user_id=1)

    assert result.daily_limit == 50
    assert result.used == used
    assert result.remaining == remaining
    assert result.input_tokens == 1200
    assert result.output_tokens == 400

    statement = session.execute.call_args.args[0]
    compiled = statement.compile()

    assert compiled.params['user_id_1'] == 1
    assert compiled.params['usage_date_1'] == today
    assert result.resets_at.tzinfo == UTC
    assert result.resets_at.hour == 0
    assert result.resets_at.minute == 0
    assert (result.resets_at.date() - today).days == 1
