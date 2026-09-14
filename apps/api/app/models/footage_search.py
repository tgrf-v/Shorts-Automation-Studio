import uuid
import enum
from datetime import datetime, timezone
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Enum, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.project import GUID

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.scene import Scene
    from app.models.footage_candidate import FootageCandidate


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FootageSearchStatus(str, enum.Enum):
    QUEUED = "queued"
    SEARCHING = "searching"
    RANKING = "ranking"
    COMPLETED = "completed"
    FAILED = "failed"


class FootageSearch(Base):
    __tablename__ = "footage_searches"

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
    scene_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    query: Mapped[str] = mapped_column(String(500), nullable=False)
    search_provider: Mapped[str] = mapped_column(String(50), default="youtube", nullable=False)
    status: Mapped[FootageSearchStatus] = mapped_column(
        Enum(FootageSearchStatus, name="footage_search_status", native_enum=False),
        default=FootageSearchStatus.QUEUED,
        nullable=False,
        index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_step: Mapped[str] = mapped_column(String(100), default="Queued", nullable=False)
    total_results: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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
    scene: Mapped["Scene"] = relationship("Scene", foreign_keys=[scene_id])
    candidates: Mapped[List["FootageCandidate"]] = relationship(
        "FootageCandidate",
        back_populates="search",
        cascade="all, delete-orphan",
        order_by="desc(FootageCandidate.final_score)"
    )
