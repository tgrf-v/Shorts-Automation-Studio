"""Migration for Video Rendering and Composition table (render_jobs)

Revision ID: 009_video_rendering_and_composition
Revises: 008_bgm_and_sfx_timeline
Create Date: 2026-09-14 19:00:00.000000

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
revision: str = '009_video_rendering_and_composition'
down_revision: Union[str, None] = '008_bgm_and_sfx_timeline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'render_jobs',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('project_id', GUID(), nullable=False),
        sa.Column('production_timeline_id', GUID(), nullable=False),
        sa.Column('tts_generation_id', GUID(), nullable=False),
        sa.Column('caption_track_id', GUID(), nullable=False),
        sa.Column('audio_timeline_id', GUID(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('pending', 'validating', 'preparing', 'rendering', 'completed', 'failed', 'cancelled', name='render_job_status', native_enum=False),
            nullable=False,
            server_default='pending'
        ),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_step', sa.String(length=100), nullable=False, server_default='Pending'),
        sa.Column('output_path', sa.String(length=1024), nullable=True),
        sa.Column('output_format', sa.String(length=50), nullable=False, server_default='mp4'),
        sa.Column('output_width', sa.Integer(), nullable=False, server_default='1080'),
        sa.Column('output_height', sa.Integer(), nullable=False, server_default='1920'),
        sa.Column('output_duration', sa.Float(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('video_codec', sa.String(length=50), nullable=False, server_default='libx264'),
        sa.Column('audio_codec', sa.String(length=50), nullable=False, server_default='aac'),
        sa.Column('fps', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('render_config', sa.JSON(), nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['production_timeline_id'], ['production_timelines.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tts_generation_id'], ['tts_generations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['caption_track_id'], ['caption_tracks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['audio_timeline_id'], ['audio_timelines.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_render_jobs_id'), 'render_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_render_jobs_project_id'), 'render_jobs', ['project_id'], unique=False)
    op.create_index(op.f('ix_render_jobs_status'), 'render_jobs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('render_jobs')
