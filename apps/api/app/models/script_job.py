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
    from app.models.script import Script


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScriptJobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScriptJobStep(str, enum.Enum):
    PREPARING_TRANSCRIPT = "Preparing transcript"
    PREPARING_SCENE_CONTEXT = "Preparing scene context"
    GENERATING_SCRIPT = "Generating script"
    VALIDATING_OUTPUT = "Validating output"
    SAVING_SCRIPT = "Saving script"
    COMPLETED = "Completed"


class ScriptJob(Base):
    __tablename__ = "script_jobs"

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
    status: Mapped[ScriptJobStatus] = mapped_column(
        Enum(ScriptJobStatus, name="script_job_status", native_enum=False),
        default=ScriptJobStatus.QUEUED,
        nullable=False,
        index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step: Mapped[str] = mapped_column(String(100), default=ScriptJobStep.PREPARING_TRANSCRIPT.value, nullable=False)
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
    script: Mapped["Script"] = relationship("Script", foreign_keys=[script_id])
