"""Add addon stars and reviews tables

Revision ID: 008
Revises: 006
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Stars/Favorites table
    op.create_table(
        'addon_stars',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('addon_id', sa.Integer(), sa.ForeignKey('addons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_addon_stars_user_addon', 'addon_stars', ['user_id', 'addon_id'], unique=True)
    op.create_index('idx_addon_stars_addon', 'addon_stars', ['addon_id'])

    # Reviews/Ratings table
    op.create_table(
        'addon_reviews',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('addon_id', sa.Integer(), sa.ForeignKey('addons.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('is_visible', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_addon_reviews_user_addon', 'addon_reviews', ['user_id', 'addon_id'], unique=True)
    op.create_index('idx_addon_reviews_addon', 'addon_reviews', ['addon_id'])


def downgrade() -> None:
    op.drop_table('addon_reviews')
    op.drop_table('addon_stars')
