import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

from app.models.render_job import RenderJobStatus


class RenderConfigSchema(BaseModel):
    width: int = Field(default=1080, description="Width in pixels")
    height: int = Field(default=1920, description="Height in pixels")
    fps: int = Field(default=30, description="Frame rate")
    crf: int = Field(default=23, description="CRF quality factor (18-28)")
    preset: str = Field(default="medium", description="x264 encoding preset")
    video_codec: str = Field(default="libx264")
    audio_codec: str = Field(default="aac")
    audio_bitrate: str = Field(default="192k")


class RenderJobCreateRequest(BaseModel):
    config: Optional[RenderConfigSchema] = None


class RenderChecklistResponse(BaseModel):
    ready: bool
    errors: List[str] = []
    warnings: List[str] = []
    details: Dict[str, Any] = {}


class RenderJobSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    status: str
    progress: int
    current_step: str
    output_format: str
    output_duration: Optional[float] = None
    file_size: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class RenderJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    production_timeline_id: uuid.UUID
    tts_generation_id: uuid.UUID
    caption_track_id: uuid.UUID
    audio_timeline_id: uuid.UUID
    status: str
    progress: int
    current_step: str
    output_path: Optional[str] = None
    output_format: str
    output_width: int
    output_height: int
    output_duration: Optional[float] = None
    file_size: Optional[int] = None
    video_codec: str
    audio_codec: str
    fps: int
    render_config: Dict[str, Any] = {}
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
