"""Add addon theme customization and verified developer badge

Revision ID: 010
Revises: 009
Create Date: 2026-02-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PRO-10: Addon page theme customization
    op.execute("ALTER TABLE addons ADD COLUMN IF NOT EXISTS theme_accent_color VARCHAR(7)")
    op.execute("ALTER TABLE addons ADD COLUMN IF NOT EXISTS theme_header_url VARCHAR(500)")

    # PRO-11: Verified developer badge
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified_developer BOOLEAN NOT NULL DEFAULT false")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_verified_developer ON users (is_verified_developer)")


def downgrade() -> None:
    op.drop_index('idx_users_verified_developer', table_name='users')
    op.drop_column('users', 'is_verified_developer')
    op.drop_column('addons', 'theme_header_url')
    op.drop_column('addons', 'theme_accent_color')
