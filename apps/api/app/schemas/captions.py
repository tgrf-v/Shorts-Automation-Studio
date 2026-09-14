import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class CaptionGenerateRequest(BaseModel):
    script_id: Optional[uuid.UUID] = Field(default=None, description="Optional script ID (defaults to active Indonesian script)")
    tts_generation_id: Optional[uuid.UUID] = Field(default=None, description="Optional TTS generation ID (defaults to active completed TTS)")
    production_timeline_id: Optional[uuid.UUID] = Field(default=None, description="Optional production timeline ID (defaults to active timeline)")
    target_words_per_segment: int = Field(default=4, ge=2, le=10, description="Ideal target word count per subtitle line")


class CaptionSegmentUpdateRequest(BaseModel):
    text: Optional[str] = Field(default=None, description="Updated caption text")
    start_time: Optional[float] = Field(default=None, description="Updated start time in seconds")
    end_time: Optional[float] = Field(default=None, description="Updated end time in seconds")
    style: Optional[str] = Field(default=None, description="Style metadata: 'default', 'bold', 'highlight'")
    position: Optional[str] = Field(default=None, description="Position metadata: 'top', 'center', 'bottom'")


class CaptionSegmentSchema(BaseModel):
    id: uuid.UUID
    caption_track_id: uuid.UUID
    sequence: int
    start_time: float
    end_time: float
    duration: float
    text: str
    source_audio_segment_id: Optional[uuid.UUID] = None
    scene_id: Optional[uuid.UUID] = None
    scene_sequence: Optional[int] = None
    style: str = "default"
    position: str = "bottom"
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CaptionTrackSummaryResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    script_id: uuid.UUID
    tts_generation_id: uuid.UUID
    production_timeline_id: uuid.UUID
    version: int
    language: str
    status: str
    total_duration: float
    total_segments: int
    is_active: bool
    is_stale: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CaptionTrackResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    script_id: uuid.UUID
    tts_generation_id: uuid.UUID
    production_timeline_id: uuid.UUID
    version: int
    language: str
    status: str
    total_duration: float
    total_segments: int
    is_active: bool
    is_stale: bool = False
    stale_reasons: List[str] = []
    average_caption_duration: Optional[float] = None
    scenes_covered: int = 0
    segments: List[CaptionSegmentSchema] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
