"""Add release channels and deprecation fields to versions

Revision ID: 010
Revises: 009
Create Date: 2026-02-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop leftover enum from any previous failed attempt, then create fresh
    op.execute("DROP TYPE IF EXISTS releasechannel CASCADE")
    op.execute("CREATE TYPE releasechannel AS ENUM ('stable', 'beta', 'alpha')")
    op.execute("ALTER TABLE versions ADD COLUMN channel releasechannel NOT NULL DEFAULT 'stable'::releasechannel")

    # Add deprecation fields
    op.add_column('versions', sa.Column('is_deprecated', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('versions', sa.Column('deprecation_reason', sa.Text(), nullable=True))
    op.add_column('versions', sa.Column('deprecated_at', sa.DateTime(timezone=True), nullable=True))

    # Index for channel-based lookups
    op.create_index('idx_versions_channel', 'versions', ['addon_id', 'channel'])


def downgrade() -> None:
    op.drop_index('idx_versions_channel')
    op.drop_column('versions', 'deprecated_at')
    op.drop_column('versions', 'deprecation_reason')
    op.drop_column('versions', 'is_deprecated')
    op.drop_column('versions', 'channel')

    # Drop enum type
    sa.Enum(name='releasechannel').drop(op.get_bind(), checkfirst=True)
