import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.models.analysis_job import AnalysisJobStatus


class TranscriptSegmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    start: float = Field(..., description="Start time in seconds")
    end: float = Field(..., description="End time in seconds")
    text: str = Field(..., description="Spoken text in segment")


class TranscriptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    media_asset_id: uuid.UUID
    language: str
    provider: str
    content: str
    segments: List[TranscriptSegmentResponse]
    version: int
    created_at: datetime
    updated_at: datetime


class KeyframeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    scene_id: uuid.UUID
    timestamp: float
    image_path: str
    quality_score: float
    created_at: datetime


class SceneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    sequence: int
    start_time: float
    end_time: float
    duration: float
    description: Optional[str] = None
    transcript_segment: List[Dict[str, Any]] = Field(default_factory=list)
    keyframes: List[KeyframeResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AnalysisJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    status: AnalysisJobStatus
    progress: int
    current_step: str
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ProjectAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: uuid.UUID
    status: str
    job: Optional[AnalysisJobResponse] = None
    transcript: Optional[TranscriptResponse] = None
    scenes: List[SceneResponse] = Field(default_factory=list)
