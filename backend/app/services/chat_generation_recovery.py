from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_conversation import (
    ChatConversation,
    ChatGenerationStatus,
)
from app.models.chat_generation_attempt import (
    ChatGenerationAttempt,
    ChatGenerationAttemptStatus,
)
from app.models.chat_message import (
    ChatMessage,
    ChatMessageRole,
    ChatMessageStatus,
)
from app.schemas.chat import ChatStreamErrorCode
from app.services.chat_errors import ChatGenerationConflictError


class ChatGenerationRecovery:
    """Recover expired generation reservations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _load_expired_conversations(
        self,
        now: datetime,
    ) -> list[ChatConversation]:
        statement = (
            select(ChatConversation)
            .where(
                ChatConversation.generation_status
                == ChatGenerationStatus.GENERATING,
                ChatConversation.generation_expires_at <= now,
            )
            .order_by(ChatConversation.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        result = await self._session.scalars(statement)

        return list(result.all())

    async def _expire_message(
        self,
        conversation: ChatConversation,
        now: datetime,
    ) -> None:
        statement = (
            update(ChatMessage)
            .where(
                ChatMessage.conversation_id == conversation.id,
                ChatMessage.generation_id == conversation.generation_id,
                ChatMessage.role == ChatMessageRole.ASSISTANT,
                ChatMessage.status == ChatMessageStatus.PENDING,
            )
            .values(
                status=ChatMessageStatus.FAILED,
                completed_at=now,
                is_active=False,
            )
            .returning(ChatMessage.id)
        )

        message_id = await self._session.scalar(statement)

        if message_id is None:
            raise ChatGenerationConflictError

    async def _expire_attempt(
        self,
        conversation: ChatConversation,
        now: datetime,
    ) -> None:
        statement = (
            update(ChatGenerationAttempt)
            .where(
                ChatGenerationAttempt.generation_id
                == conversation.generation_id,
                ChatGenerationAttempt.user_id == conversation.user_id,
                ChatGenerationAttempt.status
                == ChatGenerationAttemptStatus.RUNNING,
                ChatGenerationAttempt.expires_at <= now,
            )
            .values(
                status=ChatGenerationAttemptStatus.EXPIRED,
                finished_at=now,
                error_code=ChatStreamErrorCode.GENERATION_TIMEOUT.value,
            )
            .returning(ChatGenerationAttempt.generation_id)
        )

        generation_id = await self._session.scalar(statement)

        if generation_id is None:
            raise ChatGenerationConflictError

    @staticmethod
    def _release_conversation(
        conversation: ChatConversation,
        now: datetime,
    ) -> None:
        conversation.generation_status = ChatGenerationStatus.IDLE
        conversation.generation_id = None
        conversation.generation_started_at = None
        conversation.generation_expires_at = None
        conversation.cancel_requested_at = None
        conversation.updated_at = now

    async def _expire_orphan_attempts(
        self,
        now: datetime,
    ) -> int:
        active_conversation = (
            select(ChatConversation.id)
            .where(
                ChatConversation.generation_id
                == ChatGenerationAttempt.generation_id,
            )
            .exists()
        )

        statement = (
            update(ChatGenerationAttempt)
            .where(
                ChatGenerationAttempt.status
                == ChatGenerationAttemptStatus.RUNNING,
                ChatGenerationAttempt.expires_at <= now,
                ~active_conversation,
            )
            .values(
                status=ChatGenerationAttemptStatus.EXPIRED,
                finished_at=now,
                error_code=ChatStreamErrorCode.GENERATION_TIMEOUT.value,
            )
            .returning(ChatGenerationAttempt.generation_id)
        )

        result = await self._session.scalars(statement)

        return len(result.all())

    async def recover_owned_conversation(
        self,
        *,
        user_id: int,
        conversation_id: int,
        now: datetime,
    ) -> bool:
        """Recover one expired conversation owned by the user."""

        statement = (
            select(ChatConversation)
            .where(
                ChatConversation.id == conversation_id,
                ChatConversation.user_id == user_id,
                ChatConversation.generation_status
                == ChatGenerationStatus.GENERATING,
                ChatConversation.generation_expires_at <= now,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        conversation = await self._session.scalar(statement)

        if conversation is None:
            return False

        await self._expire_message(conversation, now)
        await self._expire_attempt(conversation, now)

        self._release_conversation(conversation, now)

        await self._session.flush()

        return True

    async def recover_expired(
        self,
        now: datetime,
    ) -> int:
        """Recover expired generations within the caller's transaction."""

        conversations = await self._load_expired_conversations(now)

        for conversation in conversations:
            await self._expire_message(conversation, now)
            await self._expire_attempt(conversation, now)

            self._release_conversation(conversation, now)

        if conversations:
            await self._session.flush()

        orphan_count = await self._expire_orphan_attempts(now)

        return len(conversations) + orphan_count
