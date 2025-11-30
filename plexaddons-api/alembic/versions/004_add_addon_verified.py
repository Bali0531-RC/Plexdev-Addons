"""add verified field to addons

Revision ID: 004
Revises: 003
Create Date: 2025-11-30

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add verified field to addons table
    op.add_column('addons', sa.Column('verified', sa.Boolean(), nullable=True, server_default='false'))
    op.create_index('ix_addons_verified', 'addons', ['verified'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_addons_verified', table_name='addons')
    op.drop_column('addons', 'verified')
