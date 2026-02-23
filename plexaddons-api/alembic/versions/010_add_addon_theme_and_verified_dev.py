"""Add addon theme customization and verified developer badge

Revision ID: 010
Revises: 009
Create Date: 2026-02-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PRO-10: Addon page theme customization
    op.add_column('addons', sa.Column('theme_accent_color', sa.String(7), nullable=True))
    op.add_column('addons', sa.Column('theme_header_url', sa.String(500), nullable=True))

    # PRO-11: Verified developer badge
    op.add_column('users', sa.Column('is_verified_developer', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.create_index('idx_users_verified_developer', 'users', ['is_verified_developer'])


def downgrade() -> None:
    op.drop_index('idx_users_verified_developer', table_name='users')
    op.drop_column('users', 'is_verified_developer')
    op.drop_column('addons', 'theme_header_url')
    op.drop_column('addons', 'theme_accent_color')
