import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.project import GUID

if TYPE_CHECKING:
    from app.models.tts_generation import TTSGeneration


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AudioSegment(Base):
    __tablename__ = "audio_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    tts_generation_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("tts_generations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    scene_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    sequence: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duration: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    audio_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

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
    generation: Mapped["TTSGeneration"] = relationship(
        "TTSGeneration",
        back_populates="segments"
    )
