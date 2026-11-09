"""Create AI analyses history table.

Revision ID: 1493c11bb799
Revises: 12607d804554
Create Date: 2026-11-09 08:54:18.168067
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '1493c11bb799'
down_revision: Union[str, Sequence[str], None] = '12607d804554'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ticket_priority_enum = postgresql.ENUM(
    'low',
    'medium',
    'high',
    'critical',
    name='ticket_priority',
    create_type=False,
)


def upgrade() -> None:
    """Create AI analyses history table."""

    op.create_table(
        'ai_analyses',
        sa.Column(
            'id',
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            'ticket_id',
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            'suggested_priority',
            ticket_priority_enum,
            nullable=False,
        ),
        sa.Column(
            'suggested_category',
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            'reason',
            sa.String(length=500),
            nullable=False,
        ),
        sa.Column(
            'priority_at_analysis',
            ticket_priority_enum,
            nullable=False,
        ),
        sa.Column(
            'analyzed_by_id',
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'applied_at',
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            'applied_by_id',
            sa.Integer(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ['analyzed_by_id'],
            ['users.id'],
        ),
        sa.ForeignKeyConstraint(
            ['applied_by_id'],
            ['users.id'],
        ),
        sa.ForeignKeyConstraint(
            ['ticket_id'],
            ['tickets.id'],
            ondelete='CASCADE',
        ),
    )

    op.create_index(
        'ix_ai_analyses_analyzed_by_id',
        'ai_analyses',
        ['analyzed_by_id'],
        unique=False,
    )

    op.create_index(
        'ix_ai_analyses_ticket_id',
        'ai_analyses',
        ['ticket_id'],
        unique=False,
    )


def downgrade() -> None:
    """Remove AI analyses history table."""

    op.drop_index(
        'ix_ai_analyses_ticket_id',
        table_name='ai_analyses',
    )

    op.drop_index(
        'ix_ai_analyses_analyzed_by_id',
        table_name='ai_analyses',
    )

    op.drop_table('ai_analyses')
