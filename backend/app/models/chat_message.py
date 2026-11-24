from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.chat_conversation import ChatConversation


class ChatMessageRole(str, Enum):
    USER = 'user'
    ASSISTANT = 'assistant'


class ChatMessageStatus(str, Enum):
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    TRUNCATED = 'truncated'


class ChatMessage(Base):
    __tablename__ = 'chat_messages'

    __table_args__ = (
        UniqueConstraint(
            'conversation_id',
            'id',
            name='uq_chat_messages_conversation_message',
        ),
        ForeignKeyConstraint(
            ['conversation_id', 'reply_to_message_id'],
            ['chat_messages.conversation_id', 'chat_messages.id'],
            name='fk_chat_messages_reply_same_conversation',
            ondelete='CASCADE',
        ),
        ForeignKeyConstraint(
            ['conversation_id', 'regenerated_from_id'],
            ['chat_messages.conversation_id', 'chat_messages.id'],
            name='fk_chat_messages_regen_same_conversation',
            ondelete='CASCADE',
        ),
        CheckConstraint(
            'model IS NULL OR length(trim(model)) > 0',
            name='ck_chat_messages_model_not_empty',
        ),
        CheckConstraint(
            'completed_at IS NULL OR completed_at >= created_at',
            name='ck_chat_messages_completed_at',
        ),
        CheckConstraint(
            'input_tokens IS NULL OR input_tokens >= 0',
            name='ck_chat_messages_input_tokens',
        ),
        CheckConstraint(
            'output_tokens IS NULL OR output_tokens >= 0',
            name='ck_chat_messages_output_tokens',
        ),
        CheckConstraint(
            "(role = 'user' "
            "AND status = 'completed' "
            'AND length(trim(content)) > 0 '
            'AND model IS NULL '
            'AND generation_id IS NULL '
            'AND input_tokens IS NULL '
            'AND output_tokens IS NULL '
            'AND reply_to_message_id IS NULL '
            'AND regenerated_from_id IS NULL '
            'AND is_active = true) '
            'OR '
            "(role = 'assistant' "
            'AND model IS NOT NULL '
            'AND generation_id IS NOT NULL '
            'AND reply_to_message_id IS NOT NULL)',
            name='ck_chat_messages_role_fields',
        ),
        CheckConstraint(
            "(status = 'pending' AND completed_at IS NULL) "
            'OR '
            "(status <> 'pending' AND completed_at IS NOT NULL)",
            name='ck_chat_messages_completion_state',
        ),
        CheckConstraint(
            "role <> 'assistant' "
            "OR status <> 'completed' "
            'OR length(trim(content)) > 0',
            name='ck_chat_messages_completed_content',
        ),
        CheckConstraint(
            "role <> 'assistant' OR is_active = false OR status = 'completed'",
            name='ck_chat_messages_active_state',
        ),
        CheckConstraint(
            'reply_to_message_id IS NULL OR reply_to_message_id <> id',
            name='ck_chat_messages_reply_not_self',
        ),
        CheckConstraint(
            'regenerated_from_id IS NULL OR regenerated_from_id <> id',
            name='ck_chat_messages_regeneration_not_self',
        ),
        Index(
            'ix_chat_messages_conversation_id_id',
            'conversation_id',
            'id',
        ),
        Index(
            'uq_chat_messages_active_reply',
            'reply_to_message_id',
            unique=True,
            postgresql_where=text(
                "role = 'assistant' "
                "AND status = 'completed' "
                'AND is_active = true'
            ),
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey(
            'chat_conversations.id',
            ondelete='CASCADE',
        ),
        nullable=False,
    )

    role: Mapped[ChatMessageRole] = mapped_column(
        SQLAlchemyEnum(
            ChatMessageRole,
            name='chat_message_role',
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[ChatMessageStatus] = mapped_column(
        SQLAlchemyEnum(
            ChatMessageStatus,
            name='chat_message_status',
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=False,
    )

    model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    generation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=True,
    )

    input_tokens: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    output_tokens: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    reply_to_message_id: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,
    )

    regenerated_from_id: Mapped[int | None] = mapped_column(
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    conversation: Mapped['ChatConversation'] = relationship(
        'ChatConversation',
        back_populates='messages',
    )
