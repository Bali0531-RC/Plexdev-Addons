"""Add A/B experiment tables

Revision ID: 023_add_ab_experiments
Revises: 022_add_canary_channel
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "023_add_ab_experiments"
down_revision = "022_add_canary_channel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use pure SQL to avoid SQLAlchemy trying to CREATE TYPE for the enum
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE experimentstatus AS ENUM ('draft', 'running', 'paused', 'completed'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    )

    op.execute("""
        CREATE TABLE IF NOT EXISTS ab_experiments (
            id SERIAL PRIMARY KEY,
            addon_id INTEGER NOT NULL REFERENCES addons(id) ON DELETE CASCADE,
            created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            name VARCHAR(200) NOT NULL,
            description TEXT,
            status experimentstatus NOT NULL DEFAULT 'draft',
            targeting_rules JSONB,
            auto_promote BOOLEAN DEFAULT FALSE,
            auto_promote_after_hours INTEGER DEFAULT 24,
            started_at TIMESTAMPTZ,
            ended_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_ab_experiments_addon ON ab_experiments (addon_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ab_experiments_status ON ab_experiments (addon_id, status)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS ab_variants (
            id SERIAL PRIMARY KEY,
            experiment_id INTEGER NOT NULL REFERENCES ab_experiments(id) ON DELETE CASCADE,
            version_id INTEGER REFERENCES versions(id) ON DELETE SET NULL,
            name VARCHAR(100) NOT NULL,
            percentage INTEGER NOT NULL,
            is_control BOOLEAN DEFAULT FALSE,
            total_checks INTEGER DEFAULT 0,
            error_reports INTEGER DEFAULT 0,
            unique_users INTEGER DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_ab_variants_experiment ON ab_variants (experiment_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ab_variants")
    op.execute("DROP TABLE IF EXISTS ab_experiments")
    op.execute("DROP TYPE IF EXISTS experimentstatus")
