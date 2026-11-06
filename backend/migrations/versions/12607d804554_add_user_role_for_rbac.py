"""Add user role for RBAC.

Revision ID: 12607d804554
Revises: fdf63c5b554e
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '12607d804554'
down_revision: Union[str, Sequence[str], None] = 'fdf63c5b554e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_role_enum = postgresql.ENUM(
    'user',
    'support',
    'admin',
    name='user_role',
    create_type=False,
)


def upgrade() -> None:
    # Criar explicitamente o enum no PostgreSQL.
    user_role_enum.create(op.get_bind(), checkfirst=False)

    # Adicionar a coluna com valor padrão para usuários existentes.
    op.add_column(
        'users',
        sa.Column(
            'role',
            user_role_enum,
            server_default='user',
            nullable=False,
        ),
    )


def downgrade() -> None:
    # Remover primeiro a coluna que utiliza o enum.
    op.drop_column('users', 'role')

    # Remover o tipo enum após a coluna.
    user_role_enum.drop(op.get_bind(), checkfirst=False)
