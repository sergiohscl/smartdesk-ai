from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.ticket import TicketPriority

if TYPE_CHECKING:
    from app.models.ticket import Ticket
    from app.models.user import User


class AIAnalysis(Base):
    __tablename__ = 'ai_analyses'

    id: Mapped[int] = mapped_column(primary_key=True)

    ticket_id: Mapped[int] = mapped_column(
        ForeignKey('tickets.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    suggested_priority: Mapped[TicketPriority] = mapped_column(
        SQLAlchemyEnum(
            TicketPriority,
            name='ticket_priority',
            values_callable=lambda enum: [item.value for item in enum],
            create_type=False,
        ),
        nullable=False,
    )

    suggested_category: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    priority_at_analysis: Mapped[TicketPriority] = mapped_column(
        SQLAlchemyEnum(
            TicketPriority,
            name='ticket_priority',
            values_callable=lambda enum: [item.value for item in enum],
            create_type=False,
        ),
        nullable=False,
    )

    analyzed_by_id: Mapped[int] = mapped_column(
        ForeignKey('users.id'),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    applied_by_id: Mapped[int | None] = mapped_column(
        ForeignKey('users.id'),
        nullable=True,
    )

    ticket: Mapped['Ticket'] = relationship(
        'Ticket',
        back_populates='ai_analyses',
    )

    analyzed_by: Mapped['User'] = relationship(
        'User',
        foreign_keys=[analyzed_by_id],
    )

    applied_by: Mapped['User | None'] = relationship(
        'User',
        foreign_keys=[applied_by_id],
    )
