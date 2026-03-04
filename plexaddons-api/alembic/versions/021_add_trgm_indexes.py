"""Add GIN trigram indexes for full-text search

pg_trgm extension is already enabled in init-db.sql.
These indexes speed up ILIKE queries on addon name and description.

Revision ID: 021_add_trgm_indexes
Revises: 020_drop_legacy_api_key
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "021_add_trgm_indexes"
down_revision = "020_drop_legacy_api_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # GIN trigram indexes for fast ILIKE pattern matching
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_addons_name_trgm "
        "ON addons USING gin (name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_addons_description_trgm "
        "ON addons USING gin (description gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_addons_slug_trgm "
        "ON addons USING gin (slug gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_addons_slug_trgm")
    op.execute("DROP INDEX IF EXISTS idx_addons_description_trgm")
    op.execute("DROP INDEX IF EXISTS idx_addons_name_trgm")
