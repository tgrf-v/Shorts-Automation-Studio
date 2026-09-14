import uuid
import enum
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Float, Boolean, Enum, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.project import GUID

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.script import Script
    from app.models.audio_segment import AudioSegment
    from app.models.tts_job import TTSJob


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TTSStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TTSGeneration(Base):
    __tablename__ = "tts_generations"

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
    provider: Mapped[str] = mapped_column(String(50), default="google", nullable=False)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    voice: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[TTSStatus] = mapped_column(
        Enum(TTSStatus, name="tts_status", native_enum=False),
        default=TTSStatus.QUEUED,
        nullable=False,
        index=True
    )
    audio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    audio_format: Mapped[str] = mapped_column(String(20), default="mp3", nullable=False)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sample_rate: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    channels: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    project: Mapped["Project"] = relationship("Project", foreign_keys=[project_id])
    script: Mapped["Script"] = relationship("Script", foreign_keys=[script_id])
    segments: Mapped[List["AudioSegment"]] = relationship(
        "AudioSegment",
        back_populates="generation",
        cascade="all, delete-orphan",
        order_by="AudioSegment.sequence"
    )
    job: Mapped[Optional["TTSJob"]] = relationship(
        "TTSJob",
        uselist=False,
        back_populates="generation",
        cascade="all, delete-orphan"
    )
