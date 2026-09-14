import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.project import GUID

if TYPE_CHECKING:
    from app.models.scene import Scene
    from app.models.footage_candidate import FootageCandidate


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SceneFootageSelection(Base):
    __tablename__ = "scene_footage_selections"
    __table_args__ = (
        UniqueConstraint("scene_id", name="uq_scene_footage_selection_scene_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    scene_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("footage_candidates.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="selected", nullable=False)
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
    scene: Mapped["Scene"] = relationship("Scene", foreign_keys=[scene_id])
    candidate: Mapped["FootageCandidate"] = relationship("FootageCandidate", foreign_keys=[candidate_id])
