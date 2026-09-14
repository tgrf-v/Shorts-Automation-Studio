import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class TTSGenerateRequest(BaseModel):
    script_id: Optional[uuid.UUID] = Field(default=None, description="Target Script ID (defaults to active script)")
    provider: Optional[str] = Field(default=None, description="TTS provider: 'google', 'elevenlabs', 'mock'")
    voice: Optional[str] = Field(default=None, description="Voice identifier (e.g. 'id-ID-Standard-A')")
    model: Optional[str] = Field(default=None, description="Optional model identifier")


class TTSGenerateResponse(BaseModel):
    generation_id: uuid.UUID = Field(..., description="Newly created TTSGeneration ID")
    job_id: uuid.UUID = Field(..., description="Background TTSJob ID")
    status: str = Field(default="queued", description="Job status")


class AudioSegmentSchema(BaseModel):
    id: uuid.UUID
    scene_id: Optional[str] = None
    sequence: int
    text: str
    start_time: float
    end_time: float
    duration: float
    audio_path: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AudioTimelineSchema(BaseModel):
    generation_id: uuid.UUID
    project_id: uuid.UUID
    script_id: uuid.UUID
    duration: float
    segments_count: int
    segments: List[AudioSegmentSchema]


class TTSGenerationSummaryResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    script_id: uuid.UUID
    provider: str
    model: Optional[str] = None
    voice: Optional[str] = None
    status: str
    duration: Optional[float] = None
    audio_format: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TTSGenerationResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    script_id: uuid.UUID
    provider: str
    model: Optional[str] = None
    voice: Optional[str] = None
    status: str
    audio_path: Optional[str] = None
    audio_format: str
    duration: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    is_active: bool
    error: Optional[str] = None
    segments: List[AudioSegmentSchema] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TTSJobResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    tts_generation_id: uuid.UUID
    status: str
    progress: int
    current_step: str
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TTSVoiceSchema(BaseModel):
    id: str
    name: str
    gender: Optional[str] = None
    language_codes: List[str] = []
    description: Optional[str] = None
