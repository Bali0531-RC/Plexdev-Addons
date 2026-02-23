"""Add security suite tables

Revision ID: 016_add_security_suite
Revises: 015_add_rollouts_flags
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '016_add_security_suite'
down_revision = '015_add_rollouts_flags'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enum types
    op.execute("DROP TYPE IF EXISTS scanstatus CASCADE")
    op.execute("CREATE TYPE scanstatus AS ENUM ('pending', 'scanning', 'completed', 'failed')")
    op.execute("DROP TYPE IF EXISTS vulnerabilityseverity CASCADE")
    op.execute("CREATE TYPE vulnerabilityseverity AS ENUM ('critical', 'high', 'medium', 'low', 'info')")

    # PREM-8: Add ip_allowlist to API keys
    op.execute("ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS ip_allowlist JSON DEFAULT NULL")

    # PREM-5: Addon signing keys
    op.execute("DROP TABLE IF EXISTS addon_signing_keys CASCADE")
    op.create_table(
        'addon_signing_keys',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('addon_id', sa.Integer(), sa.ForeignKey('addons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('public_key', sa.Text(), nullable=False),
        sa.Column('key_fingerprint', sa.String(64), nullable=False),
        sa.Column('algorithm', sa.String(20), nullable=False, server_default='ed25519'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_signing_keys_addon ON addon_signing_keys (addon_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_signing_keys_fingerprint ON addon_signing_keys (key_fingerprint)")

    # PREM-5: Version signatures
    op.execute("DROP TABLE IF EXISTS version_signatures CASCADE")
    op.create_table(
        'version_signatures',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('version_id', sa.Integer(), sa.ForeignKey('versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('signing_key_id', sa.Integer(), sa.ForeignKey('addon_signing_keys.id', ondelete='SET NULL'), nullable=True),
        sa.Column('signature', sa.Text(), nullable=False),
        sa.Column('signed_hash', sa.String(128), nullable=False),
        sa.Column('verified', sa.Boolean(), server_default='false'),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_version_signatures_version ON version_signatures (version_id)")

    # PREM-6: Vulnerability scans
    op.execute("DROP TABLE IF EXISTS vulnerability_scans CASCADE")
    op.create_table(
        'vulnerability_scans',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('version_id', sa.Integer(), sa.ForeignKey('versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('initiated_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.Enum('pending', 'scanning', 'completed', 'failed',
                                    name='scanstatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('vulnerabilities', sa.JSON(), nullable=True),
        sa.Column('total_vulnerabilities', sa.Integer(), server_default='0'),
        sa.Column('critical_count', sa.Integer(), server_default='0'),
        sa.Column('high_count', sa.Integer(), server_default='0'),
        sa.Column('medium_count', sa.Integer(), server_default='0'),
        sa.Column('low_count', sa.Integer(), server_default='0'),
        sa.Column('scan_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scan_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_vuln_scans_version ON vulnerability_scans (version_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_vuln_scans_status ON vulnerability_scans (status)")

    # PREM-7: SBOM
    op.execute("DROP TABLE IF EXISTS version_sboms CASCADE")
    op.create_table(
        'version_sboms',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('version_id', sa.Integer(), sa.ForeignKey('versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('uploaded_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('format', sa.String(50), nullable=False, server_default='npm'),
        sa.Column('raw_content', sa.Text(), nullable=True),
        sa.Column('dependencies', sa.JSON(), nullable=True),
        sa.Column('total_dependencies', sa.Integer(), server_default='0'),
        sa.Column('direct_dependencies', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_sboms_version ON version_sboms (version_id)")

    # PREM-9: 2FA challenges
    op.execute("DROP TABLE IF EXISTS two_factor_challenges CASCADE")
    op.create_table(
        'two_factor_challenges',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('challenge_code_hash', sa.String(128), nullable=False),
        sa.Column('is_verified', sa.Boolean(), server_default='false'),
        sa.Column('is_used', sa.Boolean(), server_default='false'),
        sa.Column('attempts', sa.Integer(), server_default='0'),
        sa.Column('max_attempts', sa.Integer(), server_default='5'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_2fa_challenges_user ON two_factor_challenges (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_2fa_challenges_expires ON two_factor_challenges (expires_at)")


def downgrade() -> None:
    op.drop_table('two_factor_challenges')
    op.drop_table('version_sboms')
    op.drop_table('vulnerability_scans')
    op.drop_table('version_signatures')
    op.drop_table('addon_signing_keys')
    op.execute("ALTER TABLE api_keys DROP COLUMN IF EXISTS ip_allowlist")
    op.execute("DROP TYPE IF EXISTS scanstatus CASCADE")
    op.execute("DROP TYPE IF EXISTS vulnerabilityseverity CASCADE")
