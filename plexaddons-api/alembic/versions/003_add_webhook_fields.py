"""add webhook fields to users

Revision ID: 003_add_webhook_fields
Revises: 002_add_temp_tier_fields
Create Date: 2025-11-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_webhook_fields'
down_revision: Union[str, None] = '002_add_temp_tier_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add webhook fields to users table
    op.add_column('users', sa.Column('webhook_url', sa.String(500), nullable=True))
    op.add_column('users', sa.Column('webhook_secret', sa.String(64), nullable=True))
    op.add_column('users', sa.Column('webhook_enabled', sa.Boolean(), nullable=True, server_default='false'))


def downgrade() -> None:
    op.drop_column('users', 'webhook_enabled')
    op.drop_column('users', 'webhook_secret')
    op.drop_column('users', 'webhook_url')
