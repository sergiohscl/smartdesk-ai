
"""create tickets table

Revision ID: fdf63c5b554e
Revises: c15f2efc80b2
Create Date: 2026-10-31 12:13:00.091233
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "fdf63c5b554e"
down_revision: Union[str, Sequence[str], None] = "c15f2efc80b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ticket_status = postgresql.ENUM(
    "open",
    "in_progress",
    "resolved",
    name="ticket_status",
    create_type=False,
)

ticket_priority = postgresql.ENUM(
    "low",
    "medium",
    "high",
    "critical",
    name="ticket_priority",
    create_type=False,
)


def upgrade() -> None:
    """Create tickets table and PostgreSQL enums."""

    bind = op.get_bind()

    ticket_status.create(bind, checkfirst=False)
    ticket_priority.create(bind, checkfirst=False)

    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", ticket_status, nullable=False),
        sa.Column("priority", ticket_priority, nullable=False),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
        ),
    )

    op.create_index(
        "ix_tickets_created_by_id",
        "tickets",
        ["created_by_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove tickets table and PostgreSQL enums."""

    op.drop_index(
        "ix_tickets_created_by_id",
        table_name="tickets",
    )

    op.drop_table("tickets")

    bind = op.get_bind()

    ticket_priority.drop(bind, checkfirst=False)
    ticket_status.drop(bind, checkfirst=False)
