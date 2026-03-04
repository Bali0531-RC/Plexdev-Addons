"""Add org enhancements: banner, permissions, audit log, org API keys.

Revision ID: 014_add_org_enhancements
Revises: 013
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '014_add_org_enhancements'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add banner_url to organizations
    op.execute("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS banner_url VARCHAR(500)")

    # Add permissions JSON to organization_members
    op.execute("ALTER TABLE organization_members ADD COLUMN IF NOT EXISTS permissions JSON")

    # Create org_audit_logs table
    op.execute("DROP TABLE IF EXISTS org_audit_logs CASCADE")
    op.create_table(
        'org_audit_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_org_audit_logs_org ON org_audit_logs (organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_org_audit_logs_created ON org_audit_logs (organization_id, created_at)")

    # Create org_api_keys table
    op.execute("DROP TABLE IF EXISTS org_api_keys CASCADE")
    op.create_table(
        'org_api_keys',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('key_hash', sa.String(128), nullable=False, unique=True),
        sa.Column('key_prefix', sa.String(12), nullable=False),
        sa.Column('scopes', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_org_api_keys_org ON org_api_keys (organization_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_org_api_keys_hash ON org_api_keys (key_hash)")


def downgrade() -> None:
    op.drop_table('org_api_keys')
    op.drop_table('org_audit_logs')
    op.execute("ALTER TABLE organization_members DROP COLUMN IF EXISTS permissions")
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS banner_url")
