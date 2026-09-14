import uuid
import enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Float, Enum, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.project import GUID

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.production_timeline import ProductionTimeline
    from app.models.tts_generation import TTSGeneration
    from app.models.caption import CaptionTrack
    from app.models.audio_mix import AudioTimeline


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RenderJobStatus(str, enum.Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    PREPARING = "preparing"
    RENDERING = "rendering"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RenderJob(Base):
    """
    Video rendering job model tracking composition of visual footage,
    TTS narration, burned-in subtitles, and multi-track audio into final 9:16 Shorts video.
    """
    __tablename__ = "render_jobs"

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
    production_timeline_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("production_timelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    tts_generation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("tts_generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    caption_track_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("caption_tracks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    audio_timeline_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("audio_timelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    status: Mapped[RenderJobStatus] = mapped_column(
        Enum(RenderJobStatus, name="render_job_status", native_enum=False),
        default=RenderJobStatus.PENDING,
        nullable=False,
        index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step: Mapped[str] = mapped_column(String(100), default="Pending", nullable=False)

    # Output artifact properties
    output_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    output_format: Mapped[str] = mapped_column(String(50), default="mp4", nullable=False)
    output_width: Mapped[int] = mapped_column(Integer, default=1080, nullable=False)
    output_height: Mapped[int] = mapped_column(Integer, default=1920, nullable=False)
    output_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Technical codec configuration
    video_codec: Mapped[str] = mapped_column(String(50), default="libx264", nullable=False)
    audio_codec: Mapped[str] = mapped_column(String(50), default="aac", nullable=False)
    fps: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    render_config: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
    project: Mapped["Project"] = relationship("Project", lazy="selectin")
    production_timeline: Mapped["ProductionTimeline"] = relationship("ProductionTimeline", lazy="selectin")
    tts_generation: Mapped["TTSGeneration"] = relationship("TTSGeneration", lazy="selectin")
    caption_track: Mapped["CaptionTrack"] = relationship("CaptionTrack", lazy="selectin")
    audio_timeline: Mapped["AudioTimeline"] = relationship("AudioTimeline", lazy="selectin")
