"""add auth_tokens table

Revision ID: a1b2c3d4e5f6
Revises: c50bc1dd7e55
Create Date: 2026-05-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c50bc1dd7e55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'auth_tokens',
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('telegram_id', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['telegram_id'], ['users.telegram_id']),
        sa.PrimaryKeyConstraint('token'),
    )


def downgrade() -> None:
    op.drop_table('auth_tokens')
