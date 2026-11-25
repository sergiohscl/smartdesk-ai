from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
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
from app.models.chat_usage import ChatUsage
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

CHAT_RESERVATION_LOCK_KEY = 0x534D415254434841


class ChatReservations:
    """Manage transactional generation reservations."""

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
    ) -> None:
        self._session = session
        self._settings = settings
        self._recovery = ChatGenerationRecovery(session)

    async def _acquire_lock(self) -> None:
        await self._session.execute(
            select(
                func.pg_advisory_xact_lock(
                    CHAT_RESERVATION_LOCK_KEY,
                ),
            ),
        )

    async def _lock_conversation(
        self,
        *,
        user_id: int,
        conversation_id: int,
    ) -> ChatConversation:
        statement = (
            select(ChatConversation)
            .where(
                ChatConversation.id == conversation_id,
                ChatConversation.user_id == user_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        result = await self._session.execute(statement)
        conversation = result.scalar_one_or_none()

        if conversation is None:
            raise ChatConversationNotFoundError

        if conversation.generation_status != ChatGenerationStatus.IDLE:
            raise ChatConversationBusyError

        return conversation

    async def _check_daily_limit(
        self,
        user_id: int,
        now: datetime,
    ) -> None:
        statement = select(ChatUsage.request_count).where(
            ChatUsage.user_id == user_id,
            ChatUsage.usage_date == now.date(),
        )

        used = await self._session.scalar(statement) or 0

        if used >= self._settings.CHAT_DAILY_USER_LIMIT:
            raise ChatDailyLimitError

    async def _check_rate_limit(
        self,
        user_id: int,
        now: datetime,
    ) -> None:
        statement = (
            select(func.count())
            .select_from(ChatGenerationAttempt)
            .where(
                ChatGenerationAttempt.user_id == user_id,
                ChatGenerationAttempt.reserved_at > now - timedelta(minutes=1),
            )
        )

        count = await self._session.scalar(statement) or 0

        if count >= self._settings.CHAT_REQUESTS_PER_MINUTE:
            raise ChatRateLimitError

    async def _check_concurrency(
        self,
        user_id: int,
    ) -> None:
        statement = (
            select(func.count())
            .select_from(ChatGenerationAttempt)
            .where(
                ChatGenerationAttempt.status
                == ChatGenerationAttemptStatus.RUNNING,
            )
        )

        user_count = (
            await self._session.scalar(
                statement.where(
                    ChatGenerationAttempt.user_id == user_id,
                ),
            )
            or 0
        )

        if user_count >= self._settings.CHAT_MAX_CONCURRENT_PER_USER:
            raise ChatUserConcurrencyError

        global_count = await self._session.scalar(statement) or 0

        if global_count >= self._settings.CHAT_MAX_CONCURRENT_GLOBAL:
            raise ChatGlobalConcurrencyError

    async def _check_limits(
        self,
        user_id: int,
        now: datetime,
    ) -> None:
        await self._check_daily_limit(user_id, now)
        await self._check_rate_limit(user_id, now)
        await self._check_concurrency(user_id)

    async def _increment_usage(
        self,
        user_id: int,
        now: datetime,
    ) -> None:
        statement = insert(ChatUsage).values(
            user_id=user_id,
            usage_date=now.date(),
            request_count=1,
            input_tokens=0,
            output_tokens=0,
        )

        statement = statement.on_conflict_do_update(
            index_elements=[
                ChatUsage.user_id,
                ChatUsage.usage_date,
            ],
            set_={
                'request_count': ChatUsage.request_count + 1,
                'updated_at': func.now(),
            },
        )

        await self._session.execute(statement)

    async def _persist_reservation(
        self,
        conversation: ChatConversation,
        now: datetime,
    ) -> UUID:
        generation_id = uuid4()
        expires_at = now + timedelta(
            seconds=self._settings.CHAT_TIMEOUT_SECONDS,
        )

        attempt = ChatGenerationAttempt(
            generation_id=generation_id,
            user_id=conversation.user_id,
            usage_date=now.date(),
            status=ChatGenerationAttemptStatus.RUNNING,
            model=self._settings.CHAT_MODEL,
            reserved_at=now,
            expires_at=expires_at,
        )

        conversation.generation_status = ChatGenerationStatus.GENERATING
        conversation.generation_id = generation_id
        conversation.generation_started_at = now
        conversation.generation_expires_at = expires_at
        conversation.cancel_requested_at = None

        self._session.add(attempt)
        await self._increment_usage(conversation.user_id, now)

        return generation_id

    async def recover_expired_generations(self) -> int:
        """Recover expired reservations in a dedicated transaction."""

        if not self._settings.CHAT_ENABLED:
            raise ChatDisabledError

        try:
            await self._acquire_lock()

            recovered = await self._recovery.recover_expired(
                datetime.now(UTC),
            )

            await self._session.commit()
        except BaseException:
            await self._session.rollback()
            raise

        return recovered

    async def reserve(
        self,
        *,
        user_id: int,
        conversation_id: int,
    ) -> UUID:
        """Reserve generation within the caller's transaction."""

        if not self._settings.CHAT_ENABLED:
            raise ChatDisabledError

        await self._acquire_lock()

        conversation = await self._lock_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        now = datetime.now(UTC)

        await self._check_limits(user_id, now)

        return await self._persist_reservation(
            conversation,
            now,
        )
