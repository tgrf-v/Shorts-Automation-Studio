import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.project import GUID

if TYPE_CHECKING:
    from app.models.scene import Scene


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Keyframe(Base):
    __tablename__ = "keyframes"

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
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    image_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        nullable=False
    )

    # Relationships
    scene: Mapped["Scene"] = relationship("Scene", back_populates="keyframes")
