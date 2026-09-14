import uuid
import enum
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Float, Boolean, Enum, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.project import GUID

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.transcript import Transcript


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScriptStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class Script(Base):
    __tablename__ = "scripts"

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
    source_transcript_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("transcripts.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(50), default="id", nullable=False)
    status: Mapped[ScriptStatus] = mapped_column(
        Enum(ScriptStatus, name="script_status", native_enum=False),
        default=ScriptStatus.GENERATING,
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="Untitled Shorts Script", nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    segments: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    generation_provider: Mapped[str] = mapped_column(String(50), default="gemini", nullable=False)
    generation_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_manually_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    source_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duration_ratio: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
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
    source_transcript: Mapped[Optional["Transcript"]] = relationship("Transcript", foreign_keys=[source_transcript_id])
