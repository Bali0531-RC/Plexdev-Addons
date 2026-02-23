"""Add marketplace and sponsorship (addon licenses, paid addon fields, stripe connect)

Revision ID: 013_add_marketplace
Revises: 012_add_collaborators
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '013_add_marketplace'
down_revision = '012_add_collaborators'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create license status enum
    licensestatus = sa.Enum('active', 'expired', 'revoked', 'suspended', name='licensestatus')
    licensestatus.create(op.get_bind(), checkfirst=True)

    # Add marketplace columns to addons table
    op.execute("ALTER TABLE addons ADD COLUMN IF NOT EXISTS is_paid BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE addons ADD COLUMN IF NOT EXISTS price_cents INTEGER")
    op.execute("ALTER TABLE addons ADD COLUMN IF NOT EXISTS revenue_split_percent INTEGER DEFAULT 90")
    op.execute("ALTER TABLE addons ADD COLUMN IF NOT EXISTS sponsor_url VARCHAR(500)")

    # Add Stripe Connect account ID to users table
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_connect_account_id VARCHAR(255) UNIQUE")

    # Create addon_licenses table
    op.execute("""
        CREATE TABLE IF NOT EXISTS addon_licenses (
            id SERIAL PRIMARY KEY,
            addon_id INTEGER NOT NULL REFERENCES addons(id) ON DELETE CASCADE,
            buyer_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            license_key VARCHAR(64) NOT NULL UNIQUE,
            stripe_payment_intent_id VARCHAR(255),
            amount_cents INTEGER NOT NULL,
            developer_amount_cents INTEGER NOT NULL,
            platform_amount_cents INTEGER NOT NULL,
            status licensestatus NOT NULL DEFAULT 'active',
            server_id VARCHAR(100),
            expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            revoked_at TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_addon_licenses_addon ON addon_licenses(addon_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_addon_licenses_buyer ON addon_licenses(buyer_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_addon_licenses_key ON addon_licenses(license_key)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_addon_licenses_status ON addon_licenses(status)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS addon_licenses CASCADE")
    op.execute("ALTER TABLE addons DROP COLUMN IF EXISTS is_paid")
    op.execute("ALTER TABLE addons DROP COLUMN IF EXISTS price_cents")
    op.execute("ALTER TABLE addons DROP COLUMN IF EXISTS revenue_split_percent")
    op.execute("ALTER TABLE addons DROP COLUMN IF EXISTS sponsor_url")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS stripe_connect_account_id")
    op.execute("DROP TYPE IF EXISTS licensestatus CASCADE")
