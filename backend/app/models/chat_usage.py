from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class ChatUsage(Base):
    __tablename__ = 'chat_usage'

    __table_args__ = (
        UniqueConstraint(
            'user_id',
            'usage_date',
            name='uq_chat_usage_user_date',
        ),
        CheckConstraint(
            'request_count >= 0',
            name='ck_chat_usage_request_count',
        ),
        CheckConstraint(
            'input_tokens >= 0',
            name='ck_chat_usage_input_tokens',
        ),
        CheckConstraint(
            'output_tokens >= 0',
            name='ck_chat_usage_output_tokens',
        ),
    )

    id: Mapped[int] = mapped_column(
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

    request_count: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        server_default='0',
        nullable=False,
    )

    input_tokens: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        server_default='0',
        nullable=False,
    )

    output_tokens: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        server_default='0',
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

    user: Mapped['User'] = relationship(
        'User',
        back_populates='chat_usage',
    )
