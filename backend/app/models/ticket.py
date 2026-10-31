from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy import (
    Enum as SQLAlchemyEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class TicketStatus(str, Enum):
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'


class TicketPriority(str, Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class Ticket(Base):
    __tablename__ = 'tickets'

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[TicketStatus] = mapped_column(
        SQLAlchemyEnum(
            TicketStatus,
            name='ticket_status',
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=TicketStatus.OPEN,
        nullable=False,
    )

    priority: Mapped[TicketPriority] = mapped_column(
        SQLAlchemyEnum(
            TicketPriority,
            name='ticket_priority',
            values_callable=lambda enum: [item.value for item in enum],
        ),
        default=TicketPriority.MEDIUM,
        nullable=False,
    )

    created_by_id: Mapped[int] = mapped_column(
        ForeignKey('users.id'),
        nullable=False,
        index=True,
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

    created_by: Mapped['User'] = relationship(
        'User',
        back_populates='tickets',
    )
