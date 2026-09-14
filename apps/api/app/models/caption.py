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
    from app.models.production_timeline import ProductionTimeline
    from app.models.audio_segment import AudioSegment
    from app.models.scene import Scene


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CaptionTrackStatus(str, enum.Enum):
    DRAFT = "draft"
    READY = "ready"


class CaptionTrack(Base):
    """
    Versioned subtitle/caption track container linked to active Indonesian script,
    TTS narration audio timeline, and production timeline.
    """
    __tablename__ = "caption_tracks"

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
    production_timeline_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("production_timelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(50), default="id", nullable=False)
    status: Mapped[CaptionTrackStatus] = mapped_column(
        Enum(CaptionTrackStatus, name="caption_track_status", native_enum=False),
        default=CaptionTrackStatus.READY,
        nullable=False,
        index=True
    )
    total_duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_segments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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
    production_timeline: Mapped["ProductionTimeline"] = relationship("ProductionTimeline")
    segments: Mapped[List["CaptionSegment"]] = relationship(
        "CaptionSegment",
        back_populates="track",
        cascade="all, delete-orphan",
        order_by="CaptionSegment.sequence"
    )


class CaptionSegment(Base):
    """
    Individual timestamped subtitle segment with styling metadata,
    aligned to TTS narration audio and reference scene.
    """
    __tablename__ = "caption_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    caption_track_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("caption_tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True)
    start_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    end_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    source_audio_segment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("audio_segments.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    scene_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    style: Mapped[str] = mapped_column(String(50), default="default", nullable=False)
    position: Mapped[str] = mapped_column(String(50), default="bottom", nullable=False)

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
    track: Mapped["CaptionTrack"] = relationship("CaptionTrack", back_populates="segments")
    audio_segment: Mapped[Optional["AudioSegment"]] = relationship("AudioSegment")
    scene: Mapped[Optional["Scene"]] = relationship("Scene")
