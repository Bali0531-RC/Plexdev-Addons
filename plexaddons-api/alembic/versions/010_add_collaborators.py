"""Add addon collaborators table

Revision ID: 010_add_collaborators
Revises: 009_add_screenshots_and_notifications
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010_add_collaborators'
down_revision = '009_add_screenshots_and_notifications'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create CollaboratorRole enum
    collaboratorrole = postgresql.ENUM('admin', 'editor', 'viewer', name='collaboratorrole', create_type=False)
    collaboratorrole.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'addon_collaborators',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('addon_id', sa.Integer(), sa.ForeignKey('addons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', collaboratorrole, nullable=False, server_default='editor'),
        sa.Column('invited_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('accepted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index('idx_addon_collaborators_addon', 'addon_collaborators', ['addon_id'])
    op.create_index('idx_addon_collaborators_user', 'addon_collaborators', ['user_id'])
    op.create_index('idx_addon_collaborators_unique', 'addon_collaborators', ['addon_id', 'user_id'], unique=True)


def downgrade() -> None:
    op.drop_index('idx_addon_collaborators_unique', table_name='addon_collaborators')
    op.drop_index('idx_addon_collaborators_user', table_name='addon_collaborators')
    op.drop_index('idx_addon_collaborators_addon', table_name='addon_collaborators')
    op.drop_table('addon_collaborators')

    collaboratorrole = postgresql.ENUM('admin', 'editor', 'viewer', name='collaboratorrole', create_type=False)
    collaboratorrole.drop(op.get_bind(), checkfirst=True)
