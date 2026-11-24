from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class ChatGenerationAttemptStatus(str, Enum):
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    TRUNCATED = 'truncated'
    EXPIRED = 'expired'


class ChatGenerationAttempt(Base):
    __tablename__ = 'chat_generation_attempts'

    __table_args__ = (
        CheckConstraint(
            'expires_at > reserved_at',
            name='ck_chat_attempts_expiration',
        ),
        CheckConstraint(
            "(status = 'running' AND finished_at IS NULL) "
            'OR '
            "(status <> 'running' AND finished_at IS NOT NULL)",
            name='ck_chat_attempts_completion_state',
        ),
        CheckConstraint(
            'finished_at IS NULL OR finished_at >= reserved_at',
            name='ck_chat_attempts_finished_at',
        ),
        CheckConstraint(
            'input_tokens IS NULL OR input_tokens >= 0',
            name='ck_chat_attempts_input_tokens',
        ),
        CheckConstraint(
            'output_tokens IS NULL OR output_tokens >= 0',
            name='ck_chat_attempts_output_tokens',
        ),
        CheckConstraint(
            'length(trim(model)) > 0',
            name='ck_chat_attempts_model_not_empty',
        ),
        CheckConstraint(
            "(status IN ('failed', 'expired') "
            'AND error_code IS NOT NULL) '
            'OR '
            "(status NOT IN ('failed', 'expired') "
            'AND error_code IS NULL)',
            name='ck_chat_attempts_error_state',
        ),
        Index(
            'ix_chat_attempts_user_reserved',
            'user_id',
            'reserved_at',
        ),
        Index(
            'ix_chat_attempts_running_expiration',
            'expires_at',
            postgresql_where=text("status = 'running'"),
        ),
        Index(
            'ix_chat_attempts_running_user',
            'user_id',
            postgresql_where=text("status = 'running'"),
        ),
    )

    generation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )

    usage_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    status: Mapped[ChatGenerationAttemptStatus] = mapped_column(
        SQLAlchemyEnum(
            ChatGenerationAttemptStatus,
            name='chat_generation_attempt_status',
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=ChatGenerationAttemptStatus.RUNNING,
        server_default=ChatGenerationAttemptStatus.RUNNING.value,
        nullable=False,
    )

    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    reserved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    input_tokens: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    output_tokens: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    error_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    user: Mapped['User'] = relationship(
        'User',
        back_populates='chat_generation_attempts',
    )
