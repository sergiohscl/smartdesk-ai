from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.chat_message import ChatMessage
    from app.models.user import User


class ChatGenerationStatus(str, Enum):
    IDLE = 'idle'
    GENERATING = 'generating'


class ChatConversation(Base):
    __tablename__ = 'chat_conversations'

    __table_args__ = (
        CheckConstraint(
            'cancel_requested_at IS NULL '
            'OR cancel_requested_at >= generation_started_at',
            name='ck_chat_conversations_cancel_time',
        ),
        CheckConstraint(
            'length(trim(title)) > 0',
            name='ck_chat_conversations_title_not_empty',
        ),
        CheckConstraint(
            "(generation_status = 'idle' "
            'AND generation_id IS NULL '
            'AND generation_started_at IS NULL '
            'AND generation_expires_at IS NULL '
            'AND cancel_requested_at IS NULL) '
            'OR '
            "(generation_status = 'generating' "
            'AND generation_id IS NOT NULL '
            'AND generation_started_at IS NOT NULL '
            'AND generation_expires_at IS NOT NULL '
            'AND generation_expires_at > generation_started_at)',
            name='ck_chat_conversations_generation_state',
        ),
        Index(
            'ix_chat_conversations_user_updated',
            'user_id',
            'updated_at',
            'id',
        ),
        Index(
            'ix_chat_conversations_generation_status',
            'generation_status',
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(150),
        default='Nova conversa',
        server_default='Nova conversa',
        nullable=False,
    )

    generation_status: Mapped[ChatGenerationStatus] = mapped_column(
        SQLAlchemyEnum(
            ChatGenerationStatus,
            name='chat_generation_status',
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=ChatGenerationStatus.IDLE,
        server_default=ChatGenerationStatus.IDLE.value,
        nullable=False,
    )

    generation_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        unique=True,
        nullable=True,
    )

    generation_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    generation_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancel_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped['User'] = relationship(
        'User',
        back_populates='chat_conversations',
    )

    messages: Mapped[list['ChatMessage']] = relationship(
        'ChatMessage',
        back_populates='conversation',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )
