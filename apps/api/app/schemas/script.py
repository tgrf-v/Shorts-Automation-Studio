import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ScriptGenerateRequest(BaseModel):
    source_transcript_id: Optional[uuid.UUID] = Field(default=None, description="Optional specific transcript ID")
    provider: Optional[str] = Field(default=None, description="AI provider to use: 'gemini', 'openai', 'mock'")
    model: Optional[str] = Field(default=None, description="Optional custom model identifier")
    instructions: Optional[str] = Field(default=None, description="Optional custom tone, focus, or style instructions")


class ScriptGenerateResponse(BaseModel):
    job_id: uuid.UUID = Field(..., description="Asynchronous ScriptJob ID")
    script_id: uuid.UUID = Field(..., description="Newly created Script record ID")
    status: str = Field(default="generating", description="Current status of the generation job")


class ScriptSegmentSchema(BaseModel):
    scene_id: str = Field(..., description="Scene UUID identifier")
    sequence: int = Field(default=1, description="1-based scene sequence number")
    start_time: float = Field(..., description="Scene start timestamp in seconds")
    end_time: float = Field(..., description="Scene end timestamp in seconds")
    duration: float = Field(..., description="Scene duration in seconds")
    visual_description: Optional[str] = Field(default=None, description="Visual description of scene elements")
    source_text: Optional[str] = Field(default=None, description="Source dialogue in original reference")
    adapted_text: str = Field(..., description="Indonesian adapted narration for this scene")
    word_count: Optional[int] = Field(default=0, description="Word count in this segment")
    estimated_duration: Optional[float] = Field(default=0.0, description="Estimated speaking duration in seconds")


class ScriptUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, description="Updated script title")
    content: Optional[str] = Field(default=None, description="Updated full script text")
    segments: Optional[List[Dict[str, Any]]] = Field(default=None, description="Updated scene-aligned segments")


class ScriptSummaryResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    source_transcript_id: Optional[uuid.UUID] = None
    version: int
    is_active: bool
    language: str
    status: str
    title: str
    generation_provider: str
    generation_model: Optional[str] = None
    is_manually_edited: bool
    word_count: int
    estimated_duration: float
    source_duration: Optional[float] = None
    duration_ratio: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScriptResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    source_transcript_id: Optional[uuid.UUID] = None
    version: int
    is_active: bool
    language: str
    status: str
    title: str
    content: str
    segments: List[Dict[str, Any]]
    generation_provider: str
    generation_model: Optional[str] = None
    instructions: Optional[str] = None
    is_manually_edited: bool
    word_count: int
    estimated_duration: float
    source_duration: Optional[float] = None
    duration_ratio: Optional[float] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScriptJobResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    script_id: uuid.UUID
    status: str
    progress: int
    current_step: str
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
