import uuid
import enum
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Float, Boolean, Enum, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.project import GUID

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.script import Script
    from app.models.tts_generation import TTSGeneration
    from app.models.scene import Scene
    from app.models.audio_segment import AudioSegment
    from app.models.footage_candidate import FootageCandidate


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TimelineStatus(str, enum.Enum):
    DRAFT = "draft"
    READY = "ready"


class ProductionTimeline(Base):
    """
    Unified production timeline / shot plan connecting reference scenes,
    Indonesian script segments, TTS audio segments, and selected footage.
    """
    __tablename__ = "production_timelines"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    script_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("scripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    tts_generation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("tts_generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True)
    status: Mapped[TimelineStatus] = mapped_column(
        Enum(TimelineStatus, name="timeline_status", native_enum=False),
        default=TimelineStatus.READY,
        nullable=False,
        index=True
    )
    duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_scenes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scenes_with_footage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scenes_missing_footage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project")
    script: Mapped["Script"] = relationship("Script")
    tts_generation: Mapped["TTSGeneration"] = relationship("TTSGeneration")
    items: Mapped[List["ProductionTimelineItem"]] = relationship(
        "ProductionTimelineItem",
        back_populates="timeline",
        cascade="all, delete-orphan",
        order_by="ProductionTimelineItem.sequence"
    )


class ProductionTimelineItem(Base):
    """
    Individual shot / scene block on the production timeline specifying visual cut,
    exact narration audio timing, selected footage, trim offsets, and transition.
    """
    __tablename__ = "production_timeline_items"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    timeline_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("production_timelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    scene_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True)
    start_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    script_text: Mapped[str] = mapped_column(Text, default="", nullable=False)

    audio_segment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("audio_segments.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    footage_candidate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("footage_candidates.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    footage_source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    footage_start_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    footage_end_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    transition: Mapped[str] = mapped_column(String(50), default="cut", nullable=False)

    insufficient_footage_duration: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    duration_unknown: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False
    )

    # Relationships
    timeline: Mapped["ProductionTimeline"] = relationship("ProductionTimeline", back_populates="items")
    scene: Mapped["Scene"] = relationship("Scene")
    audio_segment: Mapped[Optional["AudioSegment"]] = relationship("AudioSegment")
    footage_candidate: Mapped[Optional["FootageCandidate"]] = relationship("FootageCandidate")
