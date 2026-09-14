import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, TYPE_CHECKING
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.project import GUID

if TYPE_CHECKING:
    from app.models.footage_search import FootageSearch
    from app.models.scene import Scene


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FootageCandidate(Base):
    __tablename__ = "footage_candidates"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    footage_search_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("footage_searches.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    scene_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("scenes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    source_platform: Mapped[str] = mapped_column(String(50), default="youtube", nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    video_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    creator: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    published_at: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    search_query: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Multi-signal scores
    context_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    visual_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    final_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    match_type: Mapped[str] = mapped_column(String(50), default="relevant", nullable=False)

    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

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
    search: Mapped["FootageSearch"] = relationship("FootageSearch", back_populates="candidates")
    scene: Mapped["Scene"] = relationship("Scene", foreign_keys=[scene_id])
