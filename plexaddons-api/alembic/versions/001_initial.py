"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('discord_id', sa.String(length=20), nullable=False),
        sa.Column('discord_username', sa.String(length=100), nullable=False),
        sa.Column('discord_avatar', sa.String(length=255), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('subscription_tier', sa.String(length=20), nullable=False, server_default='free'),
        sa.Column('storage_used_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('storage_quota_bytes', sa.BigInteger(), nullable=False, server_default='52428800'),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_discord_id', 'users', ['discord_id'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=False)

    # Create subscriptions table
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=20), nullable=False),
        sa.Column('provider_subscription_id', sa.String(length=255), nullable=False),
        sa.Column('provider_customer_id', sa.String(length=255), nullable=True),
        sa.Column('tier', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('canceled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_subscriptions_user_id', 'subscriptions', ['user_id'], unique=False)
    op.create_index('ix_subscriptions_provider_subscription_id', 'subscriptions', ['provider_subscription_id'], unique=True)

    # Create addons table
    op.create_table(
        'addons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('homepage', sa.String(length=500), nullable=True),
        sa.Column('external', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_addons_slug', 'addons', ['slug'], unique=True)
    op.create_index('ix_addons_owner_id', 'addons', ['owner_id'], unique=False)
    op.create_index('ix_addons_name', 'addons', ['name'], unique=False)

    # Create versions table
    op.create_table(
        'versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('addon_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('release_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('download_url', sa.String(length=1000), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('changelog_url', sa.String(length=1000), nullable=True),
        sa.Column('changelog_content', sa.Text(), nullable=True),
        sa.Column('breaking', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('urgent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('storage_size_bytes', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['addon_id'], ['addons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_versions_addon_id', 'versions', ['addon_id'], unique=False)
    op.create_index('ix_versions_addon_version', 'versions', ['addon_id', 'version'], unique=True)

    # Create admin_audit_log table
    op.create_table(
        'admin_audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admin_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('target_type', sa.String(length=50), nullable=True),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_admin_audit_log_admin_id', 'admin_audit_log', ['admin_id'], unique=False)
    op.create_index('ix_admin_audit_log_created_at', 'admin_audit_log', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('admin_audit_log')
    op.drop_table('versions')
    op.drop_table('addons')
    op.drop_table('subscriptions')
    op.drop_table('users')
