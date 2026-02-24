"""Drop legacy User.api_key and api_key_created_at columns

Replaced by the multi-key ApiKey table (see 006_add_api_keys).

Revision ID: 020_drop_legacy_api_key
Revises: 019_add_db_indexes
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "020_drop_legacy_api_key"
down_revision = "019_add_db_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_users_api_key", table_name="users", if_exists=True)
    op.drop_column("users", "api_key")
    op.drop_column("users", "api_key_created_at")


def downgrade() -> None:
    op.add_column("users", sa.Column("api_key_created_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("api_key", sa.String(67), nullable=True))
    op.create_index("ix_users_api_key", "users", ["api_key"], unique=True)
