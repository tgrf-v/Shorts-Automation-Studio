"""Migration for production timeline tables (production_timelines, production_timeline_items)

Revision ID: 006_production_timeline
Revises: 005_visual_footage_search
Create Date: 2026-09-14 16:00:00.000000

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
revision: str = '006_production_timeline'
down_revision: Union[str, None] = '005_visual_footage_search'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create production_timelines table
    op.create_table(
        'production_timelines',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('project_id', GUID(), nullable=False),
        sa.Column('script_id', GUID(), nullable=False),
        sa.Column('tts_generation_id', GUID(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column(
            'status',
            sa.Enum('draft', 'ready', name='timeline_status', native_enum=False),
            nullable=False,
            server_default='ready'
        ),
        sa.Column('duration', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('total_scenes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('scenes_with_footage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('scenes_missing_footage', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['script_id'], ['scripts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tts_generation_id'], ['tts_generations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_production_timelines_id'), 'production_timelines', ['id'], unique=False)
    op.create_index(op.f('ix_production_timelines_project_id'), 'production_timelines', ['project_id'], unique=False)
    op.create_index(op.f('ix_production_timelines_script_id'), 'production_timelines', ['script_id'], unique=False)
    op.create_index(op.f('ix_production_timelines_tts_generation_id'), 'production_timelines', ['tts_generation_id'], unique=False)
    op.create_index(op.f('ix_production_timelines_version'), 'production_timelines', ['version'], unique=False)
    op.create_index(op.f('ix_production_timelines_is_active'), 'production_timelines', ['is_active'], unique=False)

    # 2. Create production_timeline_items table
    op.create_table(
        'production_timeline_items',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('timeline_id', GUID(), nullable=False),
        sa.Column('scene_id', GUID(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('start_time', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('end_time', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('duration', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('script_text', sa.Text(), nullable=False, server_default=''),
        sa.Column('audio_segment_id', GUID(), nullable=True),
        sa.Column('footage_candidate_id', GUID(), nullable=True),
        sa.Column('footage_source_url', sa.String(length=1000), nullable=True),
        sa.Column('footage_start_time', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('footage_end_time', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('transition', sa.String(length=50), nullable=False, server_default='cut'),
        sa.Column('insufficient_footage_duration', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('duration_unknown', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['timeline_id'], ['production_timelines.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['scene_id'], ['scenes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['audio_segment_id'], ['audio_segments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['footage_candidate_id'], ['footage_candidates.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_production_timeline_items_id'), 'production_timeline_items', ['id'], unique=False)
    op.create_index(op.f('ix_production_timeline_items_timeline_id'), 'production_timeline_items', ['timeline_id'], unique=False)
    op.create_index(op.f('ix_production_timeline_items_scene_id'), 'production_timeline_items', ['scene_id'], unique=False)
    op.create_index(op.f('ix_production_timeline_items_sequence'), 'production_timeline_items', ['sequence'], unique=False)


def downgrade() -> None:
    op.drop_table('production_timeline_items')
    op.drop_table('production_timelines')
