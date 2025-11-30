"""Add temporary tier fields to users table

Revision ID: 002_add_temp_tier_fields
Revises: 001_initial
Create Date: 2024-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_temp_tier_fields'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add temporary tier fields to users table
    op.add_column(
        'users',
        sa.Column('temp_tier', sa.String(length=20), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('temp_tier_expires_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('temp_tier_granted_by', sa.Integer(), nullable=True)
    )
    op.add_column(
        'users',
        sa.Column('temp_tier_granted_at', sa.DateTime(timezone=True), nullable=True)
    )
    
    # Add foreign key constraint for temp_tier_granted_by
    op.create_foreign_key(
        'fk_users_temp_tier_granted_by',
        'users', 'users',
        ['temp_tier_granted_by'], ['id'],
        ondelete='SET NULL'
    )
    
    # Add index for finding expired temp tiers efficiently
    op.create_index(
        'ix_users_temp_tier_expires_at',
        'users',
        ['temp_tier_expires_at'],
        unique=False,
        postgresql_where=sa.text('temp_tier_expires_at IS NOT NULL')
    )


def downgrade() -> None:
    # Remove index
    op.drop_index('ix_users_temp_tier_expires_at', table_name='users')
    
    # Remove foreign key
    op.drop_constraint('fk_users_temp_tier_granted_by', 'users', type_='foreignkey')
    
    # Remove columns
    op.drop_column('users', 'temp_tier_granted_at')
    op.drop_column('users', 'temp_tier_granted_by')
    op.drop_column('users', 'temp_tier_expires_at')
    op.drop_column('users', 'temp_tier')
