"""Add tags, scheduled releases, rollouts, and organizations

Revision ID: 005_add_tags_schedules_orgs
Revises: 004_add_addon_verified
Create Date: 2025-12-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_add_tags_schedules_orgs'
down_revision = '004_add_addon_verified'
branch_labels = None
depends_on = None


def upgrade():
    # Create organization role enum
    op.execute("CREATE TYPE organizationrole AS ENUM ('owner', 'admin', 'member')")
    
    # Create addon tag enum
    op.execute("""
        CREATE TYPE addontag AS ENUM (
            'utility', 'media', 'automation', 'integration', 
            'security', 'ui', 'library', 'metadata', 
            'sync', 'notification', 'other'
        )
    """)
    
    # Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('avatar_url', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_organizations_id', 'organizations', ['id'])
    op.create_index('ix_organizations_slug', 'organizations', ['slug'], unique=True)
    op.create_index('idx_organizations_owner', 'organizations', ['owner_id'])
    
    # Create organization_members table
    op.create_table(
        'organization_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.Enum('owner', 'admin', 'member', name='organizationrole'), nullable=False, default='member'),
        sa.Column('invited_by_id', sa.Integer(), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invited_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_organization_members_id', 'organization_members', ['id'])
    op.create_index('idx_org_members_org_user', 'organization_members', ['organization_id', 'user_id'], unique=True)
    op.create_index('idx_org_members_user', 'organization_members', ['user_id'])
    
    # Add organization_id and tags to addons table
    op.add_column('addons', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.add_column('addons', sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'))
    op.create_foreign_key('fk_addons_organization', 'addons', 'organizations', ['organization_id'], ['id'], ondelete='SET NULL')
    op.create_index('idx_addons_organization', 'addons', ['organization_id'])
    
    # Add scheduled_release_at, is_published, and rollout_percentage to versions table
    op.add_column('versions', sa.Column('scheduled_release_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('versions', sa.Column('is_published', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('versions', sa.Column('rollout_percentage', sa.Integer(), nullable=False, server_default='100'))
    op.create_index('idx_versions_scheduled_release', 'versions', ['scheduled_release_at'])


def downgrade():
    # Remove version columns
    op.drop_index('idx_versions_scheduled_release', table_name='versions')
    op.drop_column('versions', 'rollout_percentage')
    op.drop_column('versions', 'is_published')
    op.drop_column('versions', 'scheduled_release_at')
    
    # Remove addon columns
    op.drop_index('idx_addons_organization', table_name='addons')
    op.drop_constraint('fk_addons_organization', 'addons', type_='foreignkey')
    op.drop_column('addons', 'tags')
    op.drop_column('addons', 'organization_id')
    
    # Drop organization_members table
    op.drop_index('idx_org_members_user', table_name='organization_members')
    op.drop_index('idx_org_members_org_user', table_name='organization_members')
    op.drop_index('ix_organization_members_id', table_name='organization_members')
    op.drop_table('organization_members')
    
    # Drop organizations table
    op.drop_index('idx_organizations_owner', table_name='organizations')
    op.drop_index('ix_organizations_slug', table_name='organizations')
    op.drop_index('ix_organizations_id', table_name='organizations')
    op.drop_table('organizations')
    
    # Drop enums
    op.execute("DROP TYPE addontag")
    op.execute("DROP TYPE organizationrole")
