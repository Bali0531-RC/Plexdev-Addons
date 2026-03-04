"""Add screenshots, banner_url to addons and notifications table

Revision ID: 009
Revises: 008
Create Date: 2026-02-23 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add media fields to addons
    op.add_column('addons', sa.Column('banner_url', sa.String(500), nullable=True))
    op.add_column('addons', sa.Column('screenshots', sa.JSON(), server_default='[]', nullable=True))

    # Notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('link', sa.String(500), nullable=True),
        sa.Column('is_read', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_notifications_user_read', 'notifications', ['user_id', 'is_read'])
    op.create_index('idx_notifications_user_created', 'notifications', ['user_id', 'created_at'])


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_column('addons', 'screenshots')
    op.drop_column('addons', 'banner_url')
