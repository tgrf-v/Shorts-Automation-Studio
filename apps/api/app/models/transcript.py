import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.project import GUID

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.media_asset import MediaAsset


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Transcript(Base):
    __tablename__ = "transcripts"

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
    media_asset_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("media_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    language: Mapped[str] = mapped_column(String(50), default="en", nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="faster_whisper", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    segments: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
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
    media_asset: Mapped["MediaAsset"] = relationship("MediaAsset", foreign_keys=[media_asset_id])
