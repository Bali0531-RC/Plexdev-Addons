"""Add A/B experiment tables

Revision ID: 023_add_ab_experiments
Revises: 022_add_canary_channel
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = "023_add_ab_experiments"
down_revision = "022_add_canary_channel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create experimentstatus enum (IF NOT EXISTS to handle create_all preemption)
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE experimentstatus AS ENUM ('draft', 'running', 'paused', 'completed'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$"
    )

    op.create_table(
        "ab_experiments",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("addon_id", sa.Integer, sa.ForeignKey("addons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.Enum("draft", "running", "paused", "completed", name="experimentstatus", create_type=False), nullable=False, server_default="draft"),
        sa.Column("targeting_rules", JSON, nullable=True),
        sa.Column("auto_promote", sa.Boolean, default=False),
        sa.Column("auto_promote_after_hours", sa.Integer, default=24),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ab_experiments_addon", "ab_experiments", ["addon_id"])
    op.create_index("idx_ab_experiments_status", "ab_experiments", ["addon_id", "status"])

    op.create_table(
        "ab_variants",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("experiment_id", sa.Integer, sa.ForeignKey("ab_experiments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_id", sa.Integer, sa.ForeignKey("versions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("percentage", sa.Integer, nullable=False),
        sa.Column("is_control", sa.Boolean, default=False),
        sa.Column("total_checks", sa.Integer, default=0),
        sa.Column("error_reports", sa.Integer, default=0),
        sa.Column("unique_users", sa.Integer, default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ab_variants_experiment", "ab_variants", ["experiment_id"])


def downgrade() -> None:
    op.drop_table("ab_variants")
    op.drop_table("ab_experiments")
    op.execute("DROP TYPE IF EXISTS experimentstatus")
