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
    from app.models.production_timeline import ProductionTimeline
    from app.models.scene import Scene


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AudioType(str, enum.Enum):
    BGM = "bgm"
    SFX = "sfx"


class AudioTimelineStatus(str, enum.Enum):
    DRAFT = "draft"
    READY = "ready"


class AudioAsset(Base):
    """
    Audio asset repository model for BGM music tracks and SFX sound effects.
    Supports local filesystem storage with future R2 extensibility.
    """
    __tablename__ = "audio_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    type: Mapped[AudioType] = mapped_column(
        Enum(AudioType, name="audio_asset_type", native_enum=False),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    format: Mapped[str] = mapped_column(String(50), default="mp3", nullable=False)
    sample_rate: Mapped[int] = mapped_column(Integer, default=44100, nullable=False)
    channels: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    volume: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # Native dB gain offset
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
    project: Mapped[Optional["Project"]] = relationship("Project", backref="audio_assets", lazy="selectin")
    layers: Mapped[List["AudioLayer"]] = relationship("AudioLayer", back_populates="audio_asset", cascade="all, delete-orphan", lazy="selectin")


class AudioTimeline(Base):
    """
    Versioned audio timeline container linking production timeline (M7) and TTS (M5)
    with BGM and SFX audio layers.
    """
    __tablename__ = "audio_timelines"

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
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True)
    status: Mapped[AudioTimelineStatus] = mapped_column(
        Enum(AudioTimelineStatus, name="audio_timeline_status", native_enum=False),
        default=AudioTimelineStatus.READY,
        nullable=False,
        index=True
    )
    total_duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    ducking_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ducking_level: Mapped[float] = mapped_column(Float, default=-6.0, nullable=False)  # dB attenuation
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
    layers: Mapped[List["AudioLayer"]] = relationship(
        "AudioLayer",
        back_populates="audio_timeline",
        cascade="all, delete-orphan",
        order_by="AudioLayer.start_time",
        lazy="selectin"
    )


class AudioLayer(Base):
    """
    Individual audio placement layer for BGM bed or SFX cue on the timeline.
    """
    __tablename__ = "audio_layers"

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
    audio_timeline_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("audio_timelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    audio_asset_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("audio_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    scene_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("scenes.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    type: Mapped[AudioType] = mapped_column(
        Enum(AudioType, name="audio_layer_type", native_enum=False),
        nullable=False,
        index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    volume: Mapped[float] = mapped_column(Float, default=-18.0, nullable=False)  # dB gain
    fade_in: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # seconds
    fade_out: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # seconds
    loop: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ducking_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ducking_level: Mapped[float] = mapped_column(Float, default=-6.0, nullable=False)  # dB
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
    audio_timeline: Mapped["AudioTimeline"] = relationship("AudioTimeline", back_populates="layers")
    audio_asset: Mapped["AudioAsset"] = relationship("AudioAsset", back_populates="layers", lazy="selectin")
    scene: Mapped[Optional["Scene"]] = relationship("Scene", lazy="selectin")
