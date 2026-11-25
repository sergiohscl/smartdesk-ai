from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from pydantic_settings import SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import Settings
from app.models.chat_conversation import (
    ChatConversation,
    ChatGenerationStatus,
)
from app.models.chat_generation_attempt import (
    ChatGenerationAttempt,
    ChatGenerationAttemptStatus,
)
from app.services.chat_errors import (
    ChatConversationBusyError,
    ChatConversationNotFoundError,
    ChatDailyLimitError,
    ChatDisabledError,
    ChatGlobalConcurrencyError,
    ChatRateLimitError,
    ChatUserConcurrencyError,
)
from app.services.chat_generation_recovery import (
    ChatGenerationRecovery,
)
from app.services.chat_reservations import ChatReservations


class IsolatedSettings(Settings):
    model_config = SettingsConfigDict(
        env_file=None,
        secrets_dir=None,
        env_prefix='SMARTDESK_RESERVATION_TEST_',
    )


@pytest.fixture
def settings():
    return IsolatedSettings(
        DATABASE_URL='postgresql+asyncpg://test:test@localhost/test',
        JWT_SECRET_KEY='test-secret',
        CHAT_ENABLED=True,
        CHAT_DAILY_USER_LIMIT=50,
        CHAT_REQUESTS_PER_MINUTE=5,
        CHAT_MAX_CONCURRENT_PER_USER=1,
        CHAT_MAX_CONCURRENT_GLOBAL=1,
    )


@pytest.fixture
def session():
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    return session


@pytest.fixture
def conversation():
    return ChatConversation(
        id=1,
        user_id=1,
        title='Nova conversa',
        generation_status=ChatGenerationStatus.IDLE,
    )


@pytest.fixture
def reservations(session, settings, conversation):
    result = MagicMock()
    result.scalar_one_or_none.return_value = conversation
    session.execute.return_value = result

    session.scalar.side_effect = [0, 0, 0, 0]

    return ChatReservations(session, settings)


async def test_reserve_generation(
    reservations,
    session,
    conversation,
    settings,
):
    generation_id = await reservations.reserve(
        user_id=1,
        conversation_id=1,
    )

    assert isinstance(generation_id, UUID)
    assert conversation.generation_id == generation_id
    assert conversation.generation_status == ChatGenerationStatus.GENERATING
    assert conversation.cancel_requested_at is None

    attempt = session.add.call_args.args[0]

    assert isinstance(attempt, ChatGenerationAttempt)
    assert attempt.generation_id == generation_id
    assert attempt.user_id == 1
    assert attempt.model == settings.CHAT_MODEL
    assert attempt.status == ChatGenerationAttemptStatus.RUNNING
    assert attempt.usage_date == attempt.reserved_at.date()
    assert attempt.expires_at == conversation.generation_expires_at

    lock_statement = session.execute.call_args_list[0].args[0]
    assert 'pg_advisory_xact_lock' in str(lock_statement)

    owner_statement = session.execute.call_args_list[1].args[0]
    assert 'FOR UPDATE' in str(owner_statement)
    assert owner_statement.compile().params['user_id_1'] == 1

    usage_statement = session.execute.call_args_list[2].args[0]
    assert 'ON CONFLICT' in str(usage_statement)
    assert 'chat_usage.request_count +' in str(usage_statement)

    session.commit.assert_not_awaited()


@pytest.mark.parametrize(
    ('counts', 'expected_error'),
    [
        ([50], ChatDailyLimitError),
        ([0, 5], ChatRateLimitError),
        ([0, 0, 1], ChatUserConcurrencyError),
        ([0, 0, 0, 1], ChatGlobalConcurrencyError),
    ],
)
async def test_reserve_rejects_exceeded_limits(
    reservations,
    session,
    conversation,
    counts,
    expected_error,
):
    session.scalar.side_effect = counts

    with pytest.raises(expected_error):
        await reservations.reserve(
            user_id=1,
            conversation_id=1,
        )

    assert conversation.generation_status == ChatGenerationStatus.IDLE
    assert conversation.generation_id is None
    assert session.execute.await_count == 2

    session.add.assert_not_called()
    session.commit.assert_not_awaited()


async def test_reserve_rejects_busy_conversation(
    reservations,
    session,
    conversation,
):
    conversation.generation_status = ChatGenerationStatus.GENERATING

    with pytest.raises(ChatConversationBusyError):
        await reservations.reserve(
            user_id=1,
            conversation_id=1,
        )

    session.scalar.assert_not_awaited()
    session.add.assert_not_called()


async def test_reserve_rejects_inaccessible_conversation(
    reservations,
    session,
):
    session.execute.return_value.scalar_one_or_none.return_value = None

    with pytest.raises(ChatConversationNotFoundError):
        await reservations.reserve(
            user_id=1,
            conversation_id=999,
        )

    session.scalar.assert_not_awaited()
    session.add.assert_not_called()


async def test_reserve_rejects_disabled_chat(
    session,
    settings,
):
    settings = settings.model_copy(
        update={'CHAT_ENABLED': False},
    )

    reservations = ChatReservations(session, settings)

    with pytest.raises(ChatDisabledError):
        await reservations.reserve(
            user_id=1,
            conversation_id=1,
        )

    session.execute.assert_not_awaited()
    session.add.assert_not_called()


@pytest.fixture(autouse=True)
def mock_generation_recovery(monkeypatch):
    recovery = AsyncMock(return_value=0)

    monkeypatch.setattr(
        ChatGenerationRecovery,
        'recover_expired',
        recovery,
    )

    return recovery


async def test_recovery_transaction_commit(
    session,
    settings,
    mock_generation_recovery,
):
    reservations = ChatReservations(session, settings)

    mock_generation_recovery.return_value = 2

    recovered = await reservations.recover_expired_generations()

    assert recovered == 2

    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


async def test_recovery_transaction_rollback(
    session,
    settings,
    mock_generation_recovery,
):
    reservations = ChatReservations(session, settings)

    mock_generation_recovery.side_effect = RuntimeError(
        'Recovery failed',
    )

    with pytest.raises(RuntimeError, match='Recovery failed'):
        await reservations.recover_expired_generations()

    session.commit.assert_not_awaited()
    session.rollback.assert_awaited_once()
