"""Add staged rollouts and feature flags

Revision ID: 013_add_rollouts_flags
Revises: 012
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '013_add_rollouts_flags'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enum types
    op.execute("DROP TYPE IF EXISTS rolloutstage CASCADE")
    op.execute("CREATE TYPE rolloutstage AS ENUM ('canary', 'early', 'partial', 'majority', 'full', 'paused')")
    op.execute("DROP TYPE IF EXISTS rolloutstatus CASCADE")
    op.execute("CREATE TYPE rolloutstatus AS ENUM ('draft', 'active', 'paused', 'completed', 'cancelled')")

    # Staged rollouts table
    op.execute("DROP TABLE IF EXISTS staged_rollouts CASCADE")
    op.create_table(
        'staged_rollouts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('addon_id', sa.Integer(), sa.ForeignKey('addons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_id', sa.Integer(), sa.ForeignKey('versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('stage', sa.Enum('canary', 'early', 'partial', 'majority', 'full', 'paused',
                                   name='rolloutstage', create_type=False), nullable=False, server_default='canary'),
        sa.Column('percentage', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('status', sa.Enum('draft', 'active', 'paused', 'completed', 'cancelled',
                                    name='rolloutstatus', create_type=False), nullable=False, server_default='draft'),
        sa.Column('targeting_rules', sa.JSON(), nullable=True),
        sa.Column('auto_promote', sa.Boolean(), server_default='false'),
        sa.Column('auto_promote_after_hours', sa.Integer(), server_default='24'),
        sa.Column('total_checks', sa.Integer(), server_default='0'),
        sa.Column('error_reports', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('promoted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_staged_rollouts_addon ON staged_rollouts (addon_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_staged_rollouts_version ON staged_rollouts (version_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_staged_rollouts_addon_status ON staged_rollouts (addon_id, status)")

    # Rollout events table
    op.execute("DROP TABLE IF EXISTS rollout_events CASCADE")
    op.create_table(
        'rollout_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('rollout_id', sa.Integer(), sa.ForeignKey('staged_rollouts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('from_stage', sa.String(20), nullable=True),
        sa.Column('to_stage', sa.String(20), nullable=False),
        sa.Column('from_percentage', sa.Integer(), nullable=True),
        sa.Column('to_percentage', sa.Integer(), nullable=False),
        sa.Column('triggered_by', sa.String(20), nullable=False, server_default='manual'),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_rollout_events_rollout ON rollout_events (rollout_id)")

    # Feature flags table
    op.execute("DROP TABLE IF EXISTS feature_flags CASCADE")
    op.create_table(
        'feature_flags',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('addon_id', sa.Integer(), sa.ForeignKey('addons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('enabled', sa.Boolean(), server_default='false'),
        sa.Column('percentage', sa.Integer(), server_default='100'),
        sa.Column('targeting', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_feature_flags_addon ON feature_flags (addon_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_feature_flags_addon_key ON feature_flags (addon_id, key)")


def downgrade() -> None:
    op.drop_table('feature_flags')
    op.drop_table('rollout_events')
    op.drop_table('staged_rollouts')
    op.execute("DROP TYPE IF EXISTS rolloutstatus CASCADE")
    op.execute("DROP TYPE IF EXISTS rolloutstage CASCADE")
