"""Migration for BGM & SFX audio timeline tables (audio_assets, audio_timelines, audio_layers)

Revision ID: 008_bgm_and_sfx_timeline
Revises: 007_captions_and_subtitles
Create Date: 2026-09-14 18:00:00.000000

"""
import os
import sys
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# Ensure app module is in python path
_curr = os.path.dirname(os.path.abspath(__file__))
_root = os.path.abspath(os.path.join(_curr, "..", ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from app.models.project import GUID

# revision identifiers, used by Alembic.
revision: str = '008_bgm_and_sfx_timeline'
down_revision: Union[str, None] = '007_captions_and_subtitles'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create audio_assets table
    op.create_table(
        'audio_assets',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('project_id', GUID(), nullable=True),
        sa.Column(
            'type',
            sa.Enum('bgm', 'sfx', name='audio_asset_type', native_enum=False),
            nullable=False
        ),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=1024), nullable=False),
        sa.Column('source_url', sa.String(length=1024), nullable=True),
        sa.Column('duration', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('format', sa.String(length=50), nullable=False, server_default='mp3'),
        sa.Column('sample_rate', sa.Integer(), nullable=False, server_default='44100'),
        sa.Column('channels', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('volume', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audio_assets_id'), 'audio_assets', ['id'], unique=False)
    op.create_index(op.f('ix_audio_assets_project_id'), 'audio_assets', ['project_id'], unique=False)
    op.create_index(op.f('ix_audio_assets_type'), 'audio_assets', ['type'], unique=False)

    # 2. Create audio_timelines table
    op.create_table(
        'audio_timelines',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('project_id', GUID(), nullable=False),
        sa.Column('production_timeline_id', GUID(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column(
            'status',
            sa.Enum('draft', 'ready', name='audio_timeline_status', native_enum=False),
            nullable=False,
            server_default='ready'
        ),
        sa.Column('total_duration', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('ducking_enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('ducking_level', sa.Float(), nullable=False, server_default='-6.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['production_timeline_id'], ['production_timelines.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audio_timelines_id'), 'audio_timelines', ['id'], unique=False)
    op.create_index(op.f('ix_audio_timelines_project_id'), 'audio_timelines', ['project_id'], unique=False)
    op.create_index(op.f('ix_audio_timelines_production_timeline_id'), 'audio_timelines', ['production_timeline_id'], unique=False)
    op.create_index(op.f('ix_audio_timelines_version'), 'audio_timelines', ['version'], unique=False)
    op.create_index(op.f('ix_audio_timelines_status'), 'audio_timelines', ['status'], unique=False)
    op.create_index(op.f('ix_audio_timelines_is_active'), 'audio_timelines', ['is_active'], unique=False)

    # 3. Create audio_layers table
    op.create_table(
        'audio_layers',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('project_id', GUID(), nullable=False),
        sa.Column('audio_timeline_id', GUID(), nullable=False),
        sa.Column('audio_asset_id', GUID(), nullable=False),
        sa.Column('scene_id', GUID(), nullable=True),
        sa.Column(
            'type',
            sa.Enum('bgm', 'sfx', name='audio_layer_type', native_enum=False),
            nullable=False
        ),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('end_time', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('volume', sa.Float(), nullable=False, server_default='-18.0'),
        sa.Column('fade_in', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('fade_out', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('loop', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('ducking_enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('ducking_level', sa.Float(), nullable=False, server_default='-6.0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['audio_timeline_id'], ['audio_timelines.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['audio_asset_id'], ['audio_assets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audio_layers_id'), 'audio_layers', ['id'], unique=False)
    op.create_index(op.f('ix_audio_layers_project_id'), 'audio_layers', ['project_id'], unique=False)
    op.create_index(op.f('ix_audio_layers_audio_timeline_id'), 'audio_layers', ['audio_timeline_id'], unique=False)
    op.create_index(op.f('ix_audio_layers_audio_asset_id'), 'audio_layers', ['audio_asset_id'], unique=False)
    op.create_index(op.f('ix_audio_layers_scene_id'), 'audio_layers', ['scene_id'], unique=False)
    op.create_index(op.f('ix_audio_layers_type'), 'audio_layers', ['type'], unique=False)


def downgrade() -> None:
    op.drop_table('audio_layers')
    op.drop_table('audio_timelines')
    op.drop_table('audio_assets')
