"""Initial migration for projects and media assets

Revision ID: 001_initial
Revises: 
Create Date: 2026-09-12 13:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from app.models.project import GUID

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create projects table without foreign key on reference_asset_id initially
    op.create_table(
        'projects',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column(
            'status',
            sa.Enum('draft', 'analyzing', 'ready', 'failed', name='project_status', native_enum=False),
            nullable=False
        ),
        sa.Column('reference_asset_id', GUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)
    op.create_index(op.f('ix_projects_status'), 'projects', ['status'], unique=False)

    # 2. Create media_assets table
    op.create_table(
        'media_assets',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('project_id', GUID(), nullable=False),
        sa.Column(
            'type',
            sa.Enum('reference', 'footage', 'audio', 'caption', 'render', 'other', name='media_asset_type', native_enum=False),
            nullable=False
        ),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('storage_path', sa.String(length=1024), nullable=False),
        sa.Column('source_url', sa.String(length=1024), nullable=True),
        sa.Column('source_platform', sa.String(length=100), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('fps', sa.Float(), nullable=True),
        sa.Column('codec', sa.String(length=50), nullable=True),
        sa.Column('size', sa.BigInteger(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_media_assets_id'), 'media_assets', ['id'], unique=False)
    op.create_index(op.f('ix_media_assets_project_id'), 'media_assets', ['project_id'], unique=False)
    op.create_index(op.f('ix_media_assets_type'), 'media_assets', ['type'], unique=False)

    # 3. Add foreign key from projects.reference_asset_id to media_assets.id
    with op.batch_alter_table('projects') as batch_op:
        batch_op.create_foreign_key(
            'fk_project_reference_asset',
            'media_assets',
            ['reference_asset_id'],
            ['id'],
            ondelete='SET NULL'
        )


def downgrade() -> None:
    with op.batch_alter_table('projects') as batch_op:
        batch_op.drop_constraint('fk_project_reference_asset', type_='foreignkey')
    op.drop_index(op.f('ix_media_assets_type'), table_name='media_assets')
    op.drop_index(op.f('ix_media_assets_project_id'), table_name='media_assets')
    op.drop_index(op.f('ix_media_assets_id'), table_name='media_assets')
    op.drop_table('media_assets')
    op.drop_index(op.f('ix_projects_status'), table_name='projects')
    op.drop_index(op.f('ix_projects_id'), table_name='projects')
    op.drop_table('projects')

