"""Add canary release channel to ReleaseChannel enum

Revision ID: 022_add_canary_channel
Revises: 021_add_trgm_indexes
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "022_add_canary_channel"
down_revision = "021_add_trgm_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'canary' value to the releasechannel enum type
    op.execute("ALTER TYPE releasechannel ADD VALUE IF NOT EXISTS 'canary'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values directly.
    # To fully revert, would need to recreate the enum type.
    pass
