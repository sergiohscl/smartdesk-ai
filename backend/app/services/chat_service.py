import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import aclosing
from datetime import UTC, datetime, time, timedelta

from anyio import fail_after, move_on_after
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import Settings
from app.models.chat_conversation import (
    ChatConversation,
    ChatGenerationStatus,
)
from app.models.chat_message import (
    ChatMessage,
    ChatMessageStatus,
)
from app.models.chat_usage import ChatUsage
from app.schemas.chat import (
    ChatCancellationRequest,
    ChatCancellationResponse,
    ChatConversationCreate,
    ChatConversationListResponse,
    ChatConversationPublic,
    ChatConversationUpdate,
    ChatMessageCreate,
    ChatMessageCreatedEvent,
    ChatMessageListResponse,
    ChatMessagePublic,
    ChatResponseCancelledEvent,
    ChatResponseCompletedEvent,
    ChatResponseDeltaEvent,
    ChatResponseErrorEvent,
    ChatResponseFailedEvent,
    ChatResponseTruncatedEvent,
    ChatStreamErrorCode,
    ChatStreamEvent,
    ChatUsageResponse,
)
from app.services.chat_context import ChatContext
from app.services.chat_errors import (
    ChatConversationBusyError,
    ChatConversationNotFoundError,
    ChatGenerationConflictError,
)
from app.services.chat_generation import (
    ChatGeneration,
    PreparedGeneration,
)
from app.services.chat_generation_finalize import (
    ChatGenerationFinalizer,
)
from app.services.chat_generation_recovery import (
    ChatGenerationRecovery,
)
from app.services.chat_generation_stream import (
    GenerationResult,
    consume_generation,
)
from app.services.providers.base import AIProvider


class ChatService:
    """Orchestrate SmartDesk Assistant operations."""

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        provider: AIProvider,
    ) -> None:
        self._session = session
        self._settings = settings
        self._provider = provider
        self._context = ChatContext(settings)
        self._finalizer = ChatGenerationFinalizer(session)
        self._recovery = ChatGenerationRecovery(session)
        self._generation = ChatGeneration(
            session,
            settings,
            provider,
        )

    async def create_conversation(
        self,
        *,
        user_id: int,
        data: ChatConversationCreate,
    ) -> ChatConversationPublic:
        """Create a conversation owned by the authenticated user."""

        conversation = ChatConversation(
            user_id=user_id,
            title=data.title or 'Nova conversa',
        )

        try:
            self._session.add(conversation)
            await self._refresh_conversation(conversation)

            result = ChatConversationPublic.model_validate(
                conversation,
            )

            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

        return result

    async def _get_owned_conversation(
        self,
        *,
        user_id: int,
        conversation_id: int,
        for_update: bool = False,
    ) -> ChatConversation:
        """Retrieve a conversation restricted to its owner."""

        statement = select(ChatConversation).where(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == user_id,
        )

        if for_update:
            statement = statement.with_for_update()
            statement = statement.execution_options(
                populate_existing=True,
            )

        result = await self._session.execute(statement)
        conversation = result.scalar_one_or_none()

        if conversation is None:
            raise ChatConversationNotFoundError

        return conversation

    async def get_conversation(
        self,
        *,
        user_id: int,
        conversation_id: int,
    ) -> ChatConversationPublic:
        """Return an owned conversation and recover expired generations."""

        conversation = await self._get_owned_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        now = datetime.now(UTC)

        if (
            conversation.generation_status == ChatGenerationStatus.GENERATING
            and conversation.generation_expires_at is not None
            and conversation.generation_expires_at <= now
        ):
            try:
                await self._recovery.recover_owned_conversation(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    now=now,
                )

                await self._session.commit()
            except BaseException:
                await self._session.rollback()
                raise

            await self._session.refresh(conversation)

        return ChatConversationPublic.model_validate(
            conversation,
        )

    async def list_conversations(
        self,
        *,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> ChatConversationListResponse:
        """List owned conversations with pagination."""

        if page < 1 or not 1 <= page_size <= 100:
            raise ValueError('Invalid pagination parameters.')

        owner_filter = ChatConversation.user_id == user_id

        count_statement = (
            select(func.count())
            .select_from(ChatConversation)
            .where(owner_filter)
        )

        total = await self._session.scalar(count_statement)
        total = total or 0

        statement = (
            select(ChatConversation)
            .where(owner_filter)
            .order_by(
                ChatConversation.updated_at.desc(),
                ChatConversation.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self._session.scalars(statement)

        return ChatConversationListResponse(
            items=[
                ChatConversationPublic.model_validate(item)
                for item in result.all()
            ],
            total=total,
            page=page,
            page_size=page_size,
            pages=(total + page_size - 1) // page_size,
        )

    async def update_conversation(
        self,
        *,
        user_id: int,
        conversation_id: int,
        data: ChatConversationUpdate,
    ) -> ChatConversationPublic:
        """Rename a conversation restricted to its owner."""

        try:
            conversation = await self._get_owned_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                for_update=True,
            )

            conversation.title = data.title

            await self._refresh_conversation(conversation)

            result = ChatConversationPublic.model_validate(
                conversation,
            )

            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

        return result

    async def delete_conversation(
        self,
        *,
        user_id: int,
        conversation_id: int,
    ) -> None:
        """Delete an idle conversation owned by the user."""

        try:
            conversation = await self._get_owned_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                for_update=True,
            )

            await self._delete_idle_conversation(conversation)
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

    async def _refresh_conversation(
        self,
        conversation: ChatConversation,
    ) -> None:
        """Flush and refresh persisted conversation state."""

        await self._session.flush()
        await self._session.refresh(conversation)

    async def _delete_idle_conversation(
        self,
        conversation: ChatConversation,
    ) -> None:
        """Delete a previously locked idle conversation."""

        if conversation.generation_status != 'idle':
            raise ChatConversationBusyError

        statement = delete(ChatConversation).where(
            ChatConversation.id == conversation.id,
            ChatConversation.user_id == conversation.user_id,
        )

        await self._session.execute(statement)

    async def list_messages(
        self,
        *,
        user_id: int,
        conversation_id: int,
        page: int = 1,
        page_size: int = 50,
    ) -> ChatMessageListResponse:
        """List messages from an owned conversation."""

        if page < 1 or not 1 <= page_size <= 100:
            raise ValueError('Invalid pagination parameters.')

        await self._get_owned_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )

        owner_filter = (
            ChatMessage.conversation_id == conversation_id,
            ChatConversation.user_id == user_id,
        )

        count_statement = (
            select(func.count())
            .select_from(ChatMessage)
            .join(
                ChatConversation,
                ChatConversation.id == ChatMessage.conversation_id,
            )
            .where(*owner_filter)
        )

        total = await self._session.scalar(count_statement)
        total = total or 0

        statement = (
            select(ChatMessage)
            .join(
                ChatConversation,
                ChatConversation.id == ChatMessage.conversation_id,
            )
            .where(*owner_filter)
            .order_by(ChatMessage.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self._session.scalars(statement)

        return ChatMessageListResponse(
            items=[
                ChatMessagePublic.model_validate(message)
                for message in result.all()
            ],
            total=total,
            page=page,
            page_size=page_size,
            pages=(total + page_size - 1) // page_size,
        )

    async def get_usage(
        self,
        *,
        user_id: int,
    ) -> ChatUsageResponse:
        """Return the current UTC daily usage for a user."""

        today = datetime.now(UTC).date()

        statement = select(ChatUsage).where(
            ChatUsage.user_id == user_id,
            ChatUsage.usage_date == today,
        )

        result = await self._session.execute(statement)
        usage = result.scalar_one_or_none()

        daily_limit = self._settings.CHAT_DAILY_USER_LIMIT

        used = usage.request_count if usage is not None else 0

        resets_at = datetime.combine(
            today + timedelta(days=1),
            time.min,
            tzinfo=UTC,
        )

        return ChatUsageResponse(
            daily_limit=daily_limit,
            used=used,
            remaining=max(0, daily_limit - used),
            input_tokens=usage.input_tokens if usage is not None else 0,
            output_tokens=usage.output_tokens if usage is not None else 0,
            resets_at=resets_at,
        )

    async def prepare_generation(
        self,
        *,
        user_id: int,
        conversation_id: int,
        data: ChatMessageCreate,
    ) -> PreparedGeneration:
        """Prepare a generation before starting the response stream."""

        return await self._generation.prepare(
            user_id=user_id,
            conversation_id=conversation_id,
            data=data,
        )

    @staticmethod
    def _build_terminal_event(
        prepared: PreparedGeneration,
        message: ChatMessagePublic,
        result: GenerationResult,
    ) -> ChatStreamEvent:
        fields = {
            'conversation_id': prepared.conversation_id,
            'generation_id': prepared.generation_id,
            'assistant_message_id': prepared.assistant_message_id,
            'message': message,
        }

        if message.status == ChatMessageStatus.COMPLETED:
            return ChatResponseCompletedEvent(
                type='response.completed',
                **fields,
            )

        if message.status == ChatMessageStatus.TRUNCATED:
            return ChatResponseTruncatedEvent(
                type='response.truncated',
                **fields,
            )

        if message.status == ChatMessageStatus.CANCELLED:
            return ChatResponseCancelledEvent(
                type='response.cancelled',
                **fields,
            )

        return ChatResponseFailedEvent(
            type='response.failed',
            error_code=(
                result.error_code or ChatStreamErrorCode.INTERNAL_ERROR
            ),
            **fields,
        )

    async def _is_cancellation_requested(
        self,
        prepared: PreparedGeneration,
    ) -> bool:
        statement = select(
            ChatConversation.cancel_requested_at,
        ).where(
            ChatConversation.id == prepared.conversation_id,
            ChatConversation.user_id == prepared.user_id,
            ChatConversation.generation_id == prepared.generation_id,
            ChatConversation.generation_status
            == ChatGenerationStatus.GENERATING,
        )

        try:
            result = await self._session.execute(statement)
            row = result.one_or_none()
        finally:
            await self._session.rollback()

        if row is None:
            return True

        return row[0] is not None

    async def _stream_deltas(
        self,
        prepared: PreparedGeneration,
        result: GenerationResult,
    ) -> AsyncIterator[ChatStreamEvent]:
        remaining = (prepared.expires_at - datetime.now(UTC)).total_seconds()

        async with aclosing(
            consume_generation(
                provider=self._provider,
                request=prepared.request,
                result=result,
                timeout_seconds=max(0.0, remaining),
                cancellation_check=lambda: self._is_cancellation_requested(
                    prepared
                ),
            ),
        ) as events:
            async for content in events:
                yield ChatResponseDeltaEvent(
                    type='response.delta',
                    conversation_id=prepared.conversation_id,
                    generation_id=prepared.generation_id,
                    assistant_message_id=prepared.assistant_message_id,
                    delta=content,
                )

    async def _finalize_disconnected_generation(
        self,
        prepared: PreparedGeneration,
        result: GenerationResult,
    ) -> None:
        result.cancel()

        try:
            with move_on_after(5, shield=True) as scope:
                await self._finalizer.finalize(
                    prepared=prepared,
                    result=result,
                )

            if scope.cancelled_caught:
                logging.getLogger(__name__).warning(
                    'Disconnected generation finalization timed out.',
                )
        except ChatGenerationConflictError:
            return
        except Exception:
            logging.getLogger(__name__).warning(
                'Could not finalize disconnected chat generation.',
            )

    async def abort_unstarted_generation(
        self,
        prepared: PreparedGeneration,
    ) -> None:
        """Cancel a reserved generation that never started streaming."""

        await self._finalize_disconnected_generation(
            prepared,
            GenerationResult(),
        )

    async def _finalize_stream_generation(
        self,
        prepared: PreparedGeneration,
        result: GenerationResult,
    ) -> ChatStreamEvent:
        try:
            with fail_after(5, shield=True):
                message = await self._finalizer.finalize(
                    prepared=prepared,
                    result=result,
                )
        except ChatGenerationConflictError:
            error_code = ChatStreamErrorCode.GENERATION_CONFLICT
        except Exception:
            logging.getLogger(__name__).warning(
                'Chat generation persistence failed.',
            )
            error_code = ChatStreamErrorCode.PERSISTENCE_ERROR
        else:
            return self._build_terminal_event(
                prepared,
                message,
                result,
            )

        return ChatResponseErrorEvent(
            type='response.error',
            conversation_id=prepared.conversation_id,
            generation_id=prepared.generation_id,
            assistant_message_id=prepared.assistant_message_id,
            error_code=error_code,
        )

    async def stream_generation(
        self,
        prepared: PreparedGeneration,
    ) -> AsyncIterator[ChatStreamEvent]:
        """Stream a prepared generation and persist its final result."""

        result = GenerationResult()

        try:
            yield ChatMessageCreatedEvent(
                type='message.created',
                conversation_id=prepared.conversation_id,
                generation_id=prepared.generation_id,
                assistant_message_id=prepared.assistant_message_id,
                user_message_id=prepared.user_message_id,
                regenerated_from_id=prepared.regenerated_from_id,
            )

            async with aclosing(
                self._stream_deltas(prepared, result),
            ) as events:
                async for event in events:
                    yield event
        except (asyncio.CancelledError, GeneratorExit):
            await self._finalize_disconnected_generation(
                prepared,
                result,
            )
            raise

        yield await self._finalize_stream_generation(
            prepared,
            result,
        )

    @staticmethod
    def _mark_cancellation_requested(
        conversation: ChatConversation,
        data: ChatCancellationRequest,
    ) -> None:
        """Validate and mark an active generation for cancellation."""

        if (
            conversation.generation_status != ChatGenerationStatus.GENERATING
            or conversation.generation_id != data.generation_id
        ):
            raise ChatGenerationConflictError

        if conversation.cancel_requested_at is None:
            conversation.cancel_requested_at = datetime.now(UTC)

    async def cancel_generation(
        self,
        *,
        user_id: int,
        conversation_id: int,
        data: ChatCancellationRequest,
    ) -> ChatCancellationResponse:
        """Request cancellation of an owned active generation."""

        try:
            conversation = await self._get_owned_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                for_update=True,
            )

            self._mark_cancellation_requested(
                conversation,
                data,
            )

            await self._session.commit()
        except BaseException:
            await self._session.rollback()
            raise

        return ChatCancellationResponse(
            conversation_id=conversation_id,
            generation_id=data.generation_id,
            cancellation_requested=True,
        )

    async def prepare_regeneration(
        self,
        *,
        user_id: int,
        conversation_id: int,
        message_id: int,
    ) -> PreparedGeneration:
        """Prepare regeneration of the latest active response."""

        return await self._generation.prepare_regeneration(
            user_id=user_id,
            conversation_id=conversation_id,
            message_id=message_id,
        )
