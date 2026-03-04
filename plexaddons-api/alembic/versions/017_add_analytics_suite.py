"""Add premium analytics suite tables (self-hosted config, alerts, cohort entries)

Revision ID: 017_add_analytics_suite
Revises: 016_add_security_suite
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = '017_add_analytics_suite'
down_revision = '016_add_security_suite'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types
    alertnotificationchannel = sa.Enum('webhook', 'email', 'discord', name='alertnotificationchannel')
    alertnotificationchannel.create(op.get_bind(), checkfirst=True)

    alertcomparison = sa.Enum('below', 'above', name='alertcomparison')
    alertcomparison.create(op.get_bind(), checkfirst=True)

    # Self-hosted version checker configs (PREM-15)
    op.execute("""
        CREATE TABLE IF NOT EXISTS self_hosted_configs (
            id SERIAL PRIMARY KEY,
            addon_id INTEGER NOT NULL REFERENCES addons(id) ON DELETE CASCADE UNIQUE,
            custom_domain VARCHAR(255) UNIQUE,
            domain_verified BOOLEAN DEFAULT FALSE,
            verification_token VARCHAR(64),
            private_endpoint_enabled BOOLEAN DEFAULT TRUE,
            api_key_required BOOLEAN DEFAULT TRUE,
            rate_limit_per_minute INTEGER DEFAULT 60,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_self_hosted_configs_addon ON self_hosted_configs(addon_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_self_hosted_configs_domain ON self_hosted_configs(custom_domain)")

    # Analytics alerts (PREM-17)
    op.execute("""
        CREATE TABLE IF NOT EXISTS analytics_alerts (
            id SERIAL PRIMARY KEY,
            addon_id INTEGER NOT NULL REFERENCES addons(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            metric VARCHAR(50) NOT NULL,
            comparison alertcomparison NOT NULL,
            threshold INTEGER NOT NULL,
            notification_channel alertnotificationchannel NOT NULL,
            webhook_url VARCHAR(500),
            email VARCHAR(320),
            discord_webhook_url VARCHAR(500),
            is_active BOOLEAN DEFAULT TRUE,
            last_triggered_at TIMESTAMPTZ,
            trigger_count INTEGER DEFAULT 0,
            cooldown_minutes INTEGER DEFAULT 60,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_analytics_alerts_addon ON analytics_alerts(addon_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_analytics_alerts_active ON analytics_alerts(is_active)")

    # Cohort entries for version upgrade tracking (PREM-18)
    op.execute("""
        CREATE TABLE IF NOT EXISTS cohort_entries (
            id SERIAL PRIMARY KEY,
            addon_id INTEGER NOT NULL REFERENCES addons(id) ON DELETE CASCADE,
            from_version VARCHAR(50) NOT NULL,
            to_version VARCHAR(50) NOT NULL,
            client_ip_hash VARCHAR(64) NOT NULL,
            transitioned_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_cohort_entries_addon ON cohort_entries(addon_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cohort_entries_addon_versions ON cohort_entries(addon_id, from_version, to_version)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cohort_entries_transitioned ON cohort_entries(transitioned_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cohort_entries CASCADE")
    op.execute("DROP TABLE IF EXISTS analytics_alerts CASCADE")
    op.execute("DROP TABLE IF EXISTS self_hosted_configs CASCADE")
    op.execute("DROP TYPE IF EXISTS alertcomparison CASCADE")
    op.execute("DROP TYPE IF EXISTS alertnotificationchannel CASCADE")
