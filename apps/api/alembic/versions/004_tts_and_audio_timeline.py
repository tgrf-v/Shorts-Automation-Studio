"""Migration for TTS and audio timeline tables (tts_generations, audio_segments, tts_jobs)

Revision ID: 004_tts_and_audio_timeline
Revises: 003_script_adaptation
Create Date: 2026-09-14 14:00:00.000000

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
revision: str = '004_tts_and_audio_timeline'
down_revision: Union[str, None] = '003_script_adaptation'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create tts_generations table
    op.create_table(
        'tts_generations',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('project_id', GUID(), nullable=False),
        sa.Column('script_id', GUID(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False, server_default='google'),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('voice', sa.String(length=100), nullable=True),
        sa.Column(
            'status',
            sa.Enum('queued', 'processing', 'completed', 'failed', name='tts_status', native_enum=False),
            nullable=False,
            server_default='queued'
        ),
        sa.Column('audio_path', sa.String(length=500), nullable=True),
        sa.Column('audio_format', sa.String(length=20), nullable=False, server_default='mp3'),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('sample_rate', sa.Integer(), nullable=True),
        sa.Column('channels', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['script_id'], ['scripts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tts_generations_id'), 'tts_generations', ['id'], unique=False)
    op.create_index(op.f('ix_tts_generations_project_id'), 'tts_generations', ['project_id'], unique=False)
    op.create_index(op.f('ix_tts_generations_script_id'), 'tts_generations', ['script_id'], unique=False)
    op.create_index(op.f('ix_tts_generations_status'), 'tts_generations', ['status'], unique=False)
    op.create_index(op.f('ix_tts_generations_is_active'), 'tts_generations', ['is_active'], unique=False)

    # 2. Create audio_segments table
    op.create_table(
        'audio_segments',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('tts_generation_id', GUID(), nullable=False),
        sa.Column('scene_id', sa.String(length=50), nullable=True),
        sa.Column('sequence', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('end_time', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('duration', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('audio_path', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tts_generation_id'], ['tts_generations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audio_segments_id'), 'audio_segments', ['id'], unique=False)
    op.create_index(op.f('ix_audio_segments_tts_generation_id'), 'audio_segments', ['tts_generation_id'], unique=False)
    op.create_index(op.f('ix_audio_segments_scene_id'), 'audio_segments', ['scene_id'], unique=False)
    op.create_index(op.f('ix_audio_segments_sequence'), 'audio_segments', ['sequence'], unique=False)

    # 3. Create tts_jobs table
    op.create_table(
        'tts_jobs',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('project_id', GUID(), nullable=False),
        sa.Column('tts_generation_id', GUID(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('queued', 'processing', 'completed', 'failed', 'cancelled', name='tts_job_status', native_enum=False),
            nullable=False,
            server_default='queued'
        ),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_step', sa.String(length=100), nullable=False, server_default='Preparing script'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tts_generation_id'], ['tts_generations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tts_jobs_id'), 'tts_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_tts_jobs_project_id'), 'tts_jobs', ['project_id'], unique=False)
    op.create_index(op.f('ix_tts_jobs_tts_generation_id'), 'tts_jobs', ['tts_generation_id'], unique=False)
    op.create_index(op.f('ix_tts_jobs_status'), 'tts_jobs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('tts_jobs')
    op.drop_table('audio_segments')
    op.drop_table('tts_generations')
