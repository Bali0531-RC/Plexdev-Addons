"""Add readme and icon_url fields to addons

Revision ID: 007
Revises: 006
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006_add_api_keys'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('addons', sa.Column('icon_url', sa.String(500), nullable=True))
    op.add_column('addons', sa.Column('readme', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('addons', 'readme')
    op.drop_column('addons', 'icon_url')
