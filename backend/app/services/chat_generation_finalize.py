from datetime import UTC, datetime

from sqlalchemy import func, select, update
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
from app.models.chat_usage import ChatUsage
from app.schemas.chat import (
    ChatMessagePublic,
    ChatStreamErrorCode,
)
from app.services.chat_errors import ChatGenerationConflictError
from app.services.chat_generation import PreparedGeneration
from app.services.chat_generation_stream import GenerationResult

ATTEMPT_STATUS = {
    ChatMessageStatus.COMPLETED: ChatGenerationAttemptStatus.COMPLETED,
    ChatMessageStatus.TRUNCATED: ChatGenerationAttemptStatus.TRUNCATED,
    ChatMessageStatus.FAILED: ChatGenerationAttemptStatus.FAILED,
    ChatMessageStatus.CANCELLED: ChatGenerationAttemptStatus.CANCELLED,
}


class ChatGenerationFinalizer:
    """Persist generation results atomically."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _lock_conversation(
        self,
        prepared: PreparedGeneration,
    ) -> ChatConversation:
        statement = (
            select(ChatConversation)
            .where(
                ChatConversation.id == prepared.conversation_id,
                ChatConversation.user_id == prepared.user_id,
                ChatConversation.generation_id == prepared.generation_id,
                ChatConversation.generation_status
                == ChatGenerationStatus.GENERATING,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        conversation = await self._session.scalar(statement)

        if conversation is None:
            raise ChatGenerationConflictError

        return conversation

    async def _lock_message(
        self,
        prepared: PreparedGeneration,
    ) -> ChatMessage:
        statement = (
            select(ChatMessage)
            .where(
                ChatMessage.id == prepared.assistant_message_id,
                ChatMessage.conversation_id == prepared.conversation_id,
                ChatMessage.generation_id == prepared.generation_id,
                ChatMessage.reply_to_message_id == prepared.user_message_id,
                ChatMessage.role == ChatMessageRole.ASSISTANT,
                ChatMessage.status == ChatMessageStatus.PENDING,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        message = await self._session.scalar(statement)

        if message is None:
            raise ChatGenerationConflictError

        return message

    async def _lock_attempt(
        self,
        prepared: PreparedGeneration,
    ) -> ChatGenerationAttempt:
        statement = (
            select(ChatGenerationAttempt)
            .where(
                ChatGenerationAttempt.generation_id == prepared.generation_id,
                ChatGenerationAttempt.user_id == prepared.user_id,
                ChatGenerationAttempt.status
                == ChatGenerationAttemptStatus.RUNNING,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        attempt = await self._session.scalar(statement)

        if attempt is None:
            raise ChatGenerationConflictError

        return attempt

    async def _update_usage(
        self,
        attempt: ChatGenerationAttempt,
        result: GenerationResult,
    ) -> None:
        input_tokens = result.usage.input_tokens
        output_tokens = result.usage.output_tokens

        if input_tokens is None and output_tokens is None:
            return

        statement = (
            update(ChatUsage)
            .where(
                ChatUsage.user_id == attempt.user_id,
                ChatUsage.usage_date == attempt.usage_date,
            )
            .values(
                input_tokens=ChatUsage.input_tokens + (input_tokens or 0),
                output_tokens=ChatUsage.output_tokens + (output_tokens or 0),
                updated_at=func.now(),
            )
            .returning(ChatUsage.id)
        )

        usage_id = await self._session.scalar(statement)

        if usage_id is None:
            raise ChatGenerationConflictError

    @staticmethod
    def _update_message(
        message: ChatMessage,
        result: GenerationResult,
        now: datetime,
    ) -> None:
        message.content = result.content
        message.status = result.status
        message.input_tokens = result.usage.input_tokens
        message.output_tokens = result.usage.output_tokens
        message.completed_at = now
        message.is_active = result.status == ChatMessageStatus.COMPLETED

    @staticmethod
    def _update_attempt(
        attempt: ChatGenerationAttempt,
        result: GenerationResult,
        now: datetime,
    ) -> None:
        attempt.status = ATTEMPT_STATUS[result.status]
        attempt.finished_at = now
        attempt.input_tokens = result.usage.input_tokens
        attempt.output_tokens = result.usage.output_tokens

        if result.status == ChatMessageStatus.FAILED:
            error_code = (
                result.error_code or ChatStreamErrorCode.INTERNAL_ERROR
            )
            attempt.error_code = error_code.value
        else:
            attempt.error_code = None

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

    async def _deactivate_previous_response(
        self,
        prepared: PreparedGeneration,
        result: GenerationResult,
    ) -> None:
        if (
            prepared.regenerated_from_id is None
            or result.status != ChatMessageStatus.COMPLETED
        ):
            return

        statement = (
            select(ChatMessage)
            .where(
                ChatMessage.id == prepared.regenerated_from_id,
                ChatMessage.conversation_id == prepared.conversation_id,
                ChatMessage.reply_to_message_id == prepared.user_message_id,
                ChatMessage.role == ChatMessageRole.ASSISTANT,
                ChatMessage.status == ChatMessageStatus.COMPLETED,
                ChatMessage.is_active.is_(True),
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        original = await self._session.scalar(statement)

        if original is None:
            raise ChatGenerationConflictError

        original.is_active = False

        await self._session.flush()

    async def _persist_result(
        self,
        prepared: PreparedGeneration,
        result: GenerationResult,
    ) -> ChatMessagePublic:
        conversation = await self._lock_conversation(prepared)

        if conversation.cancel_requested_at is not None:
            result.cancel()

        message = await self._lock_message(prepared)
        attempt = await self._lock_attempt(prepared)

        now = datetime.now(UTC)

        await self._deactivate_previous_response(
            prepared,
            result,
        )

        self._update_message(message, result, now)
        self._update_attempt(attempt, result, now)
        self._release_conversation(conversation, now)

        await self._update_usage(attempt, result)
        await self._session.flush()

        return ChatMessagePublic.model_validate(message)

    async def finalize(
        self,
        *,
        prepared: PreparedGeneration,
        result: GenerationResult,
    ) -> ChatMessagePublic:
        """Finalize a generation and release its reservation."""

        try:
            message = await self._persist_result(prepared, result)
            await self._session.commit()
        except BaseException:
            await self._session.rollback()
            raise

        return message
