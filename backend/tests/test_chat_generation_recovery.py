from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_conversation import (
    ChatConversation,
    ChatGenerationStatus,
)
from app.services.chat_errors import ChatGenerationConflictError
from app.services.chat_generation_recovery import ChatGenerationRecovery


@pytest.fixture
def session():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def recovery(session):
    return ChatGenerationRecovery(session)


@pytest.fixture
def expired_conversation():
    now = datetime.now(UTC)

    return ChatConversation(
        id=1,
        user_id=1,
        title='Conversa expirada',
        generation_status=ChatGenerationStatus.GENERATING,
        generation_id=uuid4(),
        generation_started_at=now - timedelta(seconds=180),
        generation_expires_at=now - timedelta(seconds=60),
        cancel_requested_at=None,
        created_at=now - timedelta(seconds=180),
        updated_at=now - timedelta(seconds=180),
    )


def configure_conversations(session, conversations):
    result = MagicMock()
    result.all.return_value = conversations

    orphan_result = MagicMock()
    orphan_result.all.return_value = []

    session.scalars.side_effect = [
        result,
        orphan_result,
    ]


async def test_recover_expired_generation(
    recovery,
    session,
    expired_conversation,
):
    now = datetime.now(UTC)
    generation_id = expired_conversation.generation_id

    configure_conversations(
        session,
        [expired_conversation],
    )

    session.scalar.side_effect = [
        11,
        generation_id,
    ]

    recovered = await recovery.recover_expired(now)

    assert recovered == 1
    assert expired_conversation.generation_status == (
        ChatGenerationStatus.IDLE
    )
    assert expired_conversation.generation_id is None
    assert expired_conversation.generation_started_at is None
    assert expired_conversation.generation_expires_at is None
    assert expired_conversation.cancel_requested_at is None
    assert expired_conversation.updated_at == now

    assert session.scalar.await_count == 2

    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()


async def test_recovery_without_expired_generations(
    recovery,
    session,
):
    configure_conversations(session, [])

    recovered = await recovery.recover_expired(
        datetime.now(UTC),
    )

    assert recovered == 0

    session.scalar.assert_not_awaited()
    session.flush.assert_not_awaited()
    session.commit.assert_not_awaited()


async def test_recovery_is_idempotent(
    recovery,
    session,
    expired_conversation,
):
    now = datetime.now(UTC)

    configure_conversations(
        session,
        [expired_conversation],
    )

    session.scalar.side_effect = [
        11,
        expired_conversation.generation_id,
    ]

    first = await recovery.recover_expired(now)

    configure_conversations(session, [])

    second = await recovery.recover_expired(now)

    assert first == 1
    assert second == 0
    assert session.scalar.await_count == 2

    session.flush.assert_awaited_once()


@pytest.mark.parametrize(
    'missing_message',
    [True, False],
)
async def test_recovery_rejects_inconsistent_generation(
    recovery,
    session,
    expired_conversation,
    missing_message,
):
    configure_conversations(
        session,
        [expired_conversation],
    )

    if missing_message:
        session.scalar.side_effect = [None]
    else:
        session.scalar.side_effect = [11, None]

    with pytest.raises(ChatGenerationConflictError):
        await recovery.recover_expired(
            datetime.now(UTC),
        )

    assert expired_conversation.generation_status == (
        ChatGenerationStatus.GENERATING
    )
    assert expired_conversation.generation_id is not None

    session.flush.assert_not_awaited()
    session.commit.assert_not_awaited()


async def test_recover_orphan_attempts(
    recovery,
    session,
):
    conversations = MagicMock()
    conversations.all.return_value = []

    orphan_attempts = MagicMock()
    orphan_attempts.all.return_value = [
        uuid4(),
        uuid4(),
    ]

    session.scalars.side_effect = [
        conversations,
        orphan_attempts,
    ]

    recovered = await recovery.recover_expired(
        datetime.now(UTC),
    )

    assert recovered == 2
    assert session.scalars.await_count == 2

    session.scalar.assert_not_awaited()
    session.commit.assert_not_awaited()


async def test_recover_owned_expired_conversation(
    recovery,
    session,
    expired_conversation,
):
    now = datetime.now(UTC)
    generation_id = expired_conversation.generation_id

    session.scalar.side_effect = [
        expired_conversation,
        11,
        generation_id,
    ]

    recovered = await recovery.recover_owned_conversation(
        user_id=1,
        conversation_id=1,
        now=now,
    )

    assert recovered is True
    assert expired_conversation.generation_status == (
        ChatGenerationStatus.IDLE
    )
    assert expired_conversation.generation_id is None
    assert expired_conversation.generation_expires_at is None

    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()


async def test_recover_owned_conversation_without_match(
    recovery,
    session,
):
    session.scalar.return_value = None

    recovered = await recovery.recover_owned_conversation(
        user_id=1,
        conversation_id=1,
        now=datetime.now(UTC),
    )

    assert recovered is False

    session.scalar.assert_awaited_once()
    session.flush.assert_not_awaited()
    session.commit.assert_not_awaited()
