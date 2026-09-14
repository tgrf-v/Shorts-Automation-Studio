"""Migration for caption and subtitle tables (caption_tracks, caption_segments)

Revision ID: 007_captions_and_subtitles
Revises: 006_production_timeline
Create Date: 2026-09-14 17:00:00.000000

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
revision: str = '007_captions_and_subtitles'
down_revision: Union[str, None] = '006_production_timeline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create caption_tracks table
    op.create_table(
        'caption_tracks',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('project_id', GUID(), nullable=False),
        sa.Column('script_id', GUID(), nullable=False),
        sa.Column('tts_generation_id', GUID(), nullable=False),
        sa.Column('production_timeline_id', GUID(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('language', sa.String(length=50), nullable=False, server_default='id'),
        sa.Column(
            'status',
            sa.Enum('draft', 'ready', name='caption_track_status', native_enum=False),
            nullable=False,
            server_default='ready'
        ),
        sa.Column('total_duration', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_segments', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['script_id'], ['scripts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tts_generation_id'], ['tts_generations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['production_timeline_id'], ['production_timelines.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_caption_tracks_id'), 'caption_tracks', ['id'], unique=False)
    op.create_index(op.f('ix_caption_tracks_project_id'), 'caption_tracks', ['project_id'], unique=False)
    op.create_index(op.f('ix_caption_tracks_script_id'), 'caption_tracks', ['script_id'], unique=False)
    op.create_index(op.f('ix_caption_tracks_tts_generation_id'), 'caption_tracks', ['tts_generation_id'], unique=False)
    op.create_index(op.f('ix_caption_tracks_production_timeline_id'), 'caption_tracks', ['production_timeline_id'], unique=False)
    op.create_index(op.f('ix_caption_tracks_version'), 'caption_tracks', ['version'], unique=False)
    op.create_index(op.f('ix_caption_tracks_is_active'), 'caption_tracks', ['is_active'], unique=False)

    # 2. Create caption_segments table
    op.create_table(
        'caption_segments',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('caption_track_id', GUID(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('start_time', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('end_time', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('duration', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('source_audio_segment_id', GUID(), nullable=True),
        sa.Column('scene_id', GUID(), nullable=True),
        sa.Column('style', sa.String(length=50), nullable=False, server_default='default'),
        sa.Column('position', sa.String(length=50), nullable=False, server_default='bottom'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['caption_track_id'], ['caption_tracks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_audio_segment_id'], ['audio_segments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_caption_segments_id'), 'caption_segments', ['id'], unique=False)
    op.create_index(op.f('ix_caption_segments_caption_track_id'), 'caption_segments', ['caption_track_id'], unique=False)
    op.create_index(op.f('ix_caption_segments_sequence'), 'caption_segments', ['sequence'], unique=False)
    op.create_index(op.f('ix_caption_segments_start_time'), 'caption_segments', ['start_time'], unique=False)
    op.create_index(op.f('ix_caption_segments_source_audio_segment_id'), 'caption_segments', ['source_audio_segment_id'], unique=False)
    op.create_index(op.f('ix_caption_segments_scene_id'), 'caption_segments', ['scene_id'], unique=False)


def downgrade() -> None:
    op.drop_table('caption_segments')
    op.drop_table('caption_tracks')
