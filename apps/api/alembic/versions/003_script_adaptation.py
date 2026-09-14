"""Migration for script adaptation tables (scripts, script_jobs)

Revision ID: 003_script_adaptation
Revises: 002_reference_analysis
Create Date: 2026-09-14 11:00:00.000000

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
revision: str = '003_script_adaptation'
down_revision: Union[str, None] = '002_reference_analysis'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create scripts table
    op.create_table(
        'scripts',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('project_id', GUID(), nullable=False),
        sa.Column('source_transcript_id', GUID(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('language', sa.String(length=50), nullable=False, server_default='id'),
        sa.Column(
            'status',
            sa.Enum('draft', 'generating', 'ready', 'failed', name='script_status', native_enum=False),
            nullable=False,
            server_default='generating'
        ),
        sa.Column('title', sa.String(length=255), nullable=False, server_default='Untitled Shorts Script'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('segments', sa.JSON(), nullable=False),
        sa.Column('generation_provider', sa.String(length=50), nullable=False, server_default='gemini'),
        sa.Column('generation_model', sa.String(length=100), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('is_manually_edited', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('word_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('estimated_duration', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('source_duration', sa.Float(), nullable=True),
        sa.Column('duration_ratio', sa.Float(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_transcript_id'], ['transcripts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_scripts_id'), 'scripts', ['id'], unique=False)
    op.create_index(op.f('ix_scripts_project_id'), 'scripts', ['project_id'], unique=False)
    op.create_index(op.f('ix_scripts_source_transcript_id'), 'scripts', ['source_transcript_id'], unique=False)
    op.create_index(op.f('ix_scripts_is_active'), 'scripts', ['is_active'], unique=False)
    op.create_index(op.f('ix_scripts_status'), 'scripts', ['status'], unique=False)

    # 2. Create script_jobs table
    op.create_table(
        'script_jobs',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('project_id', GUID(), nullable=False),
        sa.Column('script_id', GUID(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('queued', 'processing', 'completed', 'failed', 'cancelled', name='script_job_status', native_enum=False),
            nullable=False,
            server_default='queued'
        ),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_step', sa.String(length=100), nullable=False, server_default='Preparing transcript'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['script_id'], ['scripts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_script_jobs_id'), 'script_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_script_jobs_project_id'), 'script_jobs', ['project_id'], unique=False)
    op.create_index(op.f('ix_script_jobs_script_id'), 'script_jobs', ['script_id'], unique=False)
    op.create_index(op.f('ix_script_jobs_status'), 'script_jobs', ['status'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_script_jobs_status'), table_name='script_jobs')
    op.drop_index(op.f('ix_script_jobs_script_id'), table_name='script_jobs')
    op.drop_index(op.f('ix_script_jobs_project_id'), table_name='script_jobs')
    op.drop_index(op.f('ix_script_jobs_id'), table_name='script_jobs')
    op.drop_table('script_jobs')

    op.drop_index(op.f('ix_scripts_status'), table_name='scripts')
    op.drop_index(op.f('ix_scripts_is_active'), table_name='scripts')
    op.drop_index(op.f('ix_scripts_source_transcript_id'), table_name='scripts')
    op.drop_index(op.f('ix_scripts_project_id'), table_name='scripts')
    op.drop_index(op.f('ix_scripts_id'), table_name='scripts')
    op.drop_table('scripts')
