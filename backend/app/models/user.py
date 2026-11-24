from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.chat_conversation import ChatConversation
    from app.models.chat_generation_attempt import ChatGenerationAttempt
    from app.models.chat_usage import ChatUsage
    from app.models.ticket import Ticket


class UserRole(str, Enum):
    USER = 'user'
    SUPPORT = 'support'
    ADMIN = 'admin'


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    role: Mapped[UserRole] = mapped_column(
        SQLAlchemyEnum(
            UserRole,
            name='user_role',
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=UserRole.USER,
        server_default=UserRole.USER.value,
        nullable=False,
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

    tickets: Mapped[list['Ticket']] = relationship(
        'Ticket',
        back_populates='created_by',
    )

    chat_conversations: Mapped[list['ChatConversation']] = relationship(
        'ChatConversation',
        back_populates='user',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )

    chat_usage: Mapped[list['ChatUsage']] = relationship(
        'ChatUsage',
        back_populates='user',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )

    chat_generation_attempts: Mapped[list['ChatGenerationAttempt']] = (
        relationship(
            'ChatGenerationAttempt',
            back_populates='user',
            cascade='all, delete-orphan',
            passive_deletes=True,
        )
    )
