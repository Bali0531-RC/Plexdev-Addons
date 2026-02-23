"""Add missing database indexes for query optimization

Revision ID: 019_add_db_indexes
Revises: 018_add_marketplace
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "019_add_db_indexes"
down_revision = "018_add_marketplace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Addon indexes for common query patterns
    op.execute("CREATE INDEX IF NOT EXISTS idx_addons_public_active ON addons (is_public, is_active)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_addons_updated_at ON addons (updated_at)")
    
    # Version indexes for sorting within addon
    op.execute("CREATE INDEX IF NOT EXISTS idx_versions_addon_created_at ON versions (addon_id, created_at)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_versions_addon_created_at")
    op.execute("DROP INDEX IF EXISTS idx_addons_updated_at")
    op.execute("DROP INDEX IF EXISTS idx_addons_public_active")
