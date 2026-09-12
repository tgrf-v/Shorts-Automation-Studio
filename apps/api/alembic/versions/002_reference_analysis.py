"""Migration for reference analysis tables (transcripts, scenes, keyframes, analysis_jobs)

Revision ID: 002_reference_analysis
Revises: 001_initial
Create Date: 2026-09-12 16:00:00.000000

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
revision: str = '002_reference_analysis'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create transcripts table
    op.create_table(
        'transcripts',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('project_id', GUID(), nullable=False),
        sa.Column('media_asset_id', GUID(), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=False, server_default='en'),
        sa.Column('provider', sa.String(length=50), nullable=False, server_default='faster_whisper'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('segments', sa.JSON(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['media_asset_id'], ['media_assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_transcripts_id'), 'transcripts', ['id'], unique=False)
    op.create_index(op.f('ix_transcripts_project_id'), 'transcripts', ['project_id'], unique=False)
    op.create_index(op.f('ix_transcripts_media_asset_id'), 'transcripts', ['media_asset_id'], unique=False)

    # 2. Create scenes table
    op.create_table(
        'scenes',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('project_id', GUID(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=False),
        sa.Column('end_time', sa.Float(), nullable=False),
        sa.Column('duration', sa.Float(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('transcript_segment', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'sequence', name='uq_project_scene_sequence')
    )
    op.create_index(op.f('ix_scenes_id'), 'scenes', ['id'], unique=False)
    op.create_index(op.f('ix_scenes_project_id'), 'scenes', ['project_id'], unique=False)

    # 3. Create keyframes table
    op.create_table(
        'keyframes',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('scene_id', GUID(), nullable=False),
        sa.Column('timestamp', sa.Float(), nullable=False),
        sa.Column('image_path', sa.String(length=1024), nullable=False),
        sa.Column('quality_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_keyframes_id'), 'keyframes', ['id'], unique=False)
    op.create_index(op.f('ix_keyframes_scene_id'), 'keyframes', ['scene_id'], unique=False)

    # 4. Create analysis_jobs table
    op.create_table(
        'analysis_jobs',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('project_id', GUID(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('queued', 'processing', 'completed', 'failed', 'cancelled', name='analysis_job_status', native_enum=False),
            nullable=False
        ),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_step', sa.String(length=50), nullable=False, server_default='initializing'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analysis_jobs_id'), 'analysis_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_analysis_jobs_project_id'), 'analysis_jobs', ['project_id'], unique=False)
    op.create_index(op.f('ix_analysis_jobs_status'), 'analysis_jobs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_analysis_jobs_status'), table_name='analysis_jobs')
    op.drop_index(op.f('ix_analysis_jobs_project_id'), table_name='analysis_jobs')
    op.drop_index(op.f('ix_analysis_jobs_id'), table_name='analysis_jobs')
    op.drop_table('analysis_jobs')

    op.drop_index(op.f('ix_keyframes_scene_id'), table_name='keyframes')
    op.drop_index(op.f('ix_keyframes_id'), table_name='keyframes')
    op.drop_table('keyframes')

    op.drop_index(op.f('ix_scenes_project_id'), table_name='scenes')
    op.drop_index(op.f('ix_scenes_id'), table_name='scenes')
    op.drop_table('scenes')

    op.drop_index(op.f('ix_transcripts_media_asset_id'), table_name='transcripts')
    op.drop_index(op.f('ix_transcripts_project_id'), table_name='transcripts')
    op.drop_index(op.f('ix_transcripts_id'), table_name='transcripts')
    op.drop_table('transcripts')
