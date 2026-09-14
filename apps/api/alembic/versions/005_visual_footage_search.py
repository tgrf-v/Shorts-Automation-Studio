"""Migration for visual footage search tables (footage_searches, footage_candidates, scene_footage_selections)

Revision ID: 005_visual_footage_search
Revises: 004_tts_and_audio_timeline
Create Date: 2026-09-14 15:00:00.000000

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
revision: str = '005_visual_footage_search'
down_revision: Union[str, None] = '004_tts_and_audio_timeline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create footage_searches table
    op.create_table(
        'footage_searches',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('project_id', GUID(), nullable=False),
        sa.Column('scene_id', GUID(), nullable=False),
        sa.Column('query', sa.String(length=500), nullable=False),
        sa.Column('search_provider', sa.String(length=50), nullable=False, server_default='youtube'),
        sa.Column(
            'status',
            sa.Enum('queued', 'searching', 'ranking', 'completed', 'failed', name='footage_search_status', native_enum=False),
            nullable=False,
            server_default='queued'
        ),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('current_step', sa.String(length=100), nullable=False, server_default='Queued'),
        sa.Column('total_results', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_footage_searches_id'), 'footage_searches', ['id'], unique=False)
    op.create_index(op.f('ix_footage_searches_project_id'), 'footage_searches', ['project_id'], unique=False)
    op.create_index(op.f('ix_footage_searches_scene_id'), 'footage_searches', ['scene_id'], unique=False)
    op.create_index(op.f('ix_footage_searches_status'), 'footage_searches', ['status'], unique=False)

    # 2. Create footage_candidates table
    op.create_table(
        'footage_candidates',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('footage_search_id', GUID(), nullable=False),
        sa.Column('scene_id', GUID(), nullable=False),
        sa.Column('source_platform', sa.String(length=50), nullable=False, server_default='youtube'),
        sa.Column('source_url', sa.String(length=1024), nullable=False),
        sa.Column('video_url', sa.String(length=1024), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=1024), nullable=True),
        sa.Column('creator', sa.String(length=255), nullable=True),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('published_at', sa.String(length=100), nullable=True),
        sa.Column('search_query', sa.String(length=255), nullable=True),
        sa.Column('context_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('visual_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('similarity_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('final_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('match_type', sa.String(length=50), nullable=False, server_default='relevant'),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['footage_search_id'], ['footage_searches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_footage_candidates_id'), 'footage_candidates', ['id'], unique=False)
    op.create_index(op.f('ix_footage_candidates_footage_search_id'), 'footage_candidates', ['footage_search_id'], unique=False)
    op.create_index(op.f('ix_footage_candidates_scene_id'), 'footage_candidates', ['scene_id'], unique=False)
    op.create_index(op.f('ix_footage_candidates_source_platform'), 'footage_candidates', ['source_platform'], unique=False)
    op.create_index(op.f('ix_footage_candidates_final_score'), 'footage_candidates', ['final_score'], unique=False)

    # 3. Create scene_footage_selections table
    op.create_table(
        'scene_footage_selections',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('scene_id', GUID(), nullable=False),
        sa.Column('candidate_id', GUID(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='selected'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['footage_candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('scene_id', name='uq_scene_footage_selection_scene_id')
    )
    op.create_index(op.f('ix_scene_footage_selections_id'), 'scene_footage_selections', ['id'], unique=False)
    op.create_index(op.f('ix_scene_footage_selections_scene_id'), 'scene_footage_selections', ['scene_id'], unique=False)
    op.create_index(op.f('ix_scene_footage_selections_candidate_id'), 'scene_footage_selections', ['candidate_id'], unique=False)


def downgrade() -> None:
    op.drop_table('scene_footage_selections')
    op.drop_table('footage_candidates')
    op.drop_table('footage_searches')
