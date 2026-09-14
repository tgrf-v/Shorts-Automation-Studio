import uuid
import enum
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Enum, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.project import GUID

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.tts_generation import TTSGeneration


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TTSJobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TTSJobStep(str, enum.Enum):
    PREPARING_SCRIPT = "Preparing script"
    GENERATING_SEGMENTS = "Generating audio segments"
    BUILDING_TIMELINE = "Building audio timeline"
    COMBINING_AUDIO = "Combining audio"
    FINALIZING = "Finalizing"
    COMPLETED = "Completed"


class TTSJob(Base):
    __tablename__ = "tts_jobs"

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
    tts_generation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("tts_generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status: Mapped[TTSJobStatus] = mapped_column(
        Enum(TTSJobStatus, name="tts_job_status", native_enum=False),
        default=TTSJobStatus.QUEUED,
        nullable=False,
        index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step: Mapped[str] = mapped_column(String(100), default=TTSJobStep.PREPARING_SCRIPT.value, nullable=False)
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
    project: Mapped["Project"] = relationship("Project", foreign_keys=[project_id])
    generation: Mapped["TTSGeneration"] = relationship("TTSGeneration", back_populates="job")
