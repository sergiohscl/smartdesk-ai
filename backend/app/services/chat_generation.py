from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import Settings
from app.models.chat_conversation import ChatConversation
from app.models.chat_message import (
    ChatMessage,
    ChatMessageRole,
    ChatMessageStatus,
)
from app.schemas.chat import ChatMessageCreate
from app.services.chat_context import ChatContext
from app.services.chat_errors import ChatRegenerationConflictError
from app.services.chat_reservations import ChatReservations
from app.services.providers.base import AIProvider, ProviderRequest


@dataclass(frozen=True, slots=True)
class PreparedGeneration:
    user_id: int
    conversation_id: int
    generation_id: UUID
    user_message_id: int
    assistant_message_id: int
    request: ProviderRequest
    expires_at: datetime
    regenerated_from_id: int | None = None


class ChatGeneration:
    """Prepare and execute assistant generations."""

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
        self._reservations = ChatReservations(session, settings)

    async def _load_history(
        self,
        conversation_id: int,
        current_message_id: int,
    ) -> list[ChatMessage]:
        statement = (
            select(ChatMessage)
            .where(
                ChatMessage.conversation_id == conversation_id,
                ChatMessage.id != current_message_id,
                ChatMessage.status == ChatMessageStatus.COMPLETED,
                ChatMessage.is_active.is_(True),
            )
            .order_by(ChatMessage.id.asc())
        )

        result = await self._session.scalars(statement)

        return list(result.all())

    async def _create_user_message(
        self,
        conversation_id: int,
        data: ChatMessageCreate,
    ) -> ChatMessage:
        now = datetime.now(UTC)

        message = ChatMessage(
            conversation_id=conversation_id,
            role=ChatMessageRole.USER,
            content=data.content,
            status=ChatMessageStatus.COMPLETED,
            is_active=True,
            created_at=now,
            completed_at=now,
        )

        self._session.add(message)
        await self._session.flush()

        return message

    async def _create_assistant_message(
        self,
        user_message: ChatMessage,
        generation_id: UUID,
    ) -> ChatMessage:
        message = ChatMessage(
            conversation_id=user_message.conversation_id,
            role=ChatMessageRole.ASSISTANT,
            content='',
            status=ChatMessageStatus.PENDING,
            model=self._provider.model,
            generation_id=generation_id,
            reply_to_message_id=user_message.id,
            is_active=False,
            created_at=datetime.now(UTC),
        )

        self._session.add(message)
        await self._session.flush()

        return message

    async def _prepare_messages(
        self,
        *,
        user_id: int,
        conversation_id: int,
        generation_id: UUID,
        data: ChatMessageCreate,
    ) -> PreparedGeneration:
        user_message = await self._create_user_message(
            conversation_id,
            data,
        )

        history = await self._load_history(
            conversation_id,
            user_message.id,
        )

        request = self._context.build(
            current_message=user_message,
            history=history,
        )

        assistant_message = await self._create_assistant_message(
            user_message,
            generation_id,
        )

        expires_at = await self._session.scalar(
            select(ChatConversation.generation_expires_at).where(
                ChatConversation.id == conversation_id,
                ChatConversation.generation_id == generation_id,
            ),
        )

        if expires_at is None:
            raise RuntimeError('Generation expiration is missing.')

        return PreparedGeneration(
            user_id=user_id,
            conversation_id=conversation_id,
            generation_id=generation_id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            request=request,
            expires_at=expires_at,
        )

    async def prepare(
        self,
        *,
        user_id: int,
        conversation_id: int,
        data: ChatMessageCreate,
    ) -> PreparedGeneration:
        """Atomically reserve generation and persist initial messages."""

        await self._reservations.recover_expired_generations()

        try:
            generation_id = await self._reservations.reserve(
                user_id=user_id,
                conversation_id=conversation_id,
            )

            prepared = await self._prepare_messages(
                user_id=user_id,
                conversation_id=conversation_id,
                generation_id=generation_id,
                data=data,
            )

            await self._session.commit()
        except BaseException:
            await self._session.rollback()
            raise

        return prepared

    async def _load_regeneration_target(
        self,
        conversation_id: int,
        message_id: int,
    ) -> ChatMessage:
        statement = select(ChatMessage).where(
            ChatMessage.id == message_id,
            ChatMessage.conversation_id == conversation_id,
            ChatMessage.role == ChatMessageRole.ASSISTANT,
            ChatMessage.status == ChatMessageStatus.COMPLETED,
            ChatMessage.is_active.is_(True),
        )

        message = await self._session.scalar(statement)

        if message is None:
            raise ChatRegenerationConflictError

        return message

    async def _load_regeneration_question(
        self,
        original: ChatMessage,
    ) -> ChatMessage:
        statement = (
            select(ChatMessage)
            .where(
                ChatMessage.conversation_id == original.conversation_id,
                ChatMessage.role == ChatMessageRole.USER,
                ChatMessage.status == ChatMessageStatus.COMPLETED,
                ChatMessage.is_active.is_(True),
            )
            .order_by(ChatMessage.id.desc())
            .limit(1)
        )

        question = await self._session.scalar(statement)

        if question is None or question.id != original.reply_to_message_id:
            raise ChatRegenerationConflictError

        return question

    async def _prepare_regeneration_messages(
        self,
        *,
        user_id: int,
        conversation_id: int,
        generation_id: UUID,
        message_id: int,
    ) -> PreparedGeneration:
        original = await self._load_regeneration_target(
            conversation_id,
            message_id,
        )

        question = await self._load_regeneration_question(original)

        history = await self._load_history(
            conversation_id,
            question.id,
        )

        request = self._context.build(
            current_message=question,
            history=history,
        )

        assistant = await self._create_assistant_message(
            question,
            generation_id,
        )

        assistant.regenerated_from_id = original.id

        expires_at = await self._session.scalar(
            select(ChatConversation.generation_expires_at).where(
                ChatConversation.id == conversation_id,
                ChatConversation.generation_id == generation_id,
            ),
        )

        if expires_at is None:
            raise ChatRegenerationConflictError

        return PreparedGeneration(
            user_id=user_id,
            conversation_id=conversation_id,
            generation_id=generation_id,
            user_message_id=question.id,
            assistant_message_id=assistant.id,
            request=request,
            expires_at=expires_at,
            regenerated_from_id=original.id,
        )

    async def prepare_regeneration(
        self,
        *,
        user_id: int,
        conversation_id: int,
        message_id: int,
    ) -> PreparedGeneration:
        """Prepare a replacement response within one transaction."""

        await self._reservations.recover_expired_generations()

        try:
            generation_id = await self._reservations.reserve(
                user_id=user_id,
                conversation_id=conversation_id,
            )

            prepared = await self._prepare_regeneration_messages(
                user_id=user_id,
                conversation_id=conversation_id,
                generation_id=generation_id,
                message_id=message_id,
            )

            await self._session.commit()
        except BaseException:
            await self._session.rollback()
            raise

        return prepared
