import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class ProductionTimelineGenerateRequest(BaseModel):
    script_id: Optional[uuid.UUID] = Field(default=None, description="Specific script ID, defaults to project's active script")
    tts_generation_id: Optional[uuid.UUID] = Field(default=None, description="Specific TTS generation ID, defaults to project's active TTS")


class ProductionTimelineItemUpdateRequest(BaseModel):
    footage_candidate_id: Optional[uuid.UUID] = Field(default=None, description="New candidate ID to assign to this scene")
    footage_start_time: Optional[float] = Field(default=None, description="Trim start offset in candidate source video")
    footage_end_time: Optional[float] = Field(default=None, description="Trim end offset in candidate source video")
    transition: Optional[str] = Field(default=None, description="Transition type, e.g. 'cut' or 'fade'")
    notes: Optional[str] = Field(default=None, description="User production notes")


class CandidateBriefSchema(BaseModel):
    id: uuid.UUID
    title: str
    source_platform: str
    source_url: str
    thumbnail_url: Optional[str] = None
    duration: Optional[float] = None
    visual_score: float = 0.0
    context_score: float = 0.0
    final_score: float = 0.0
    match_type: str = "Similar footage"

    model_config = ConfigDict(from_attributes=True)


class SceneBriefSchema(BaseModel):
    id: uuid.UUID
    sequence: int
    start_time: float
    end_time: float
    visual_description: Optional[str] = None
    primary_keyframe_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ProductionTimelineItemSchema(BaseModel):
    id: uuid.UUID
    timeline_id: uuid.UUID
    scene_id: uuid.UUID
    sequence: int
    start_time: float
    end_time: float
    duration: float
    script_text: str
    audio_segment_id: Optional[uuid.UUID] = None
    footage_candidate_id: Optional[uuid.UUID] = None
    footage_source_url: Optional[str] = None
    footage_start_time: float = 0.0
    footage_end_time: float = 0.0
    transition: str = "cut"
    insufficient_footage_duration: bool = False
    duration_unknown: bool = False
    notes: Optional[str] = None
    scene: Optional[SceneBriefSchema] = None
    candidate: Optional[CandidateBriefSchema] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductionTimelineSummaryResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    script_id: uuid.UUID
    tts_generation_id: uuid.UUID
    version: int
    status: str
    duration: float
    total_scenes: int
    scenes_with_footage: int
    scenes_missing_footage: int
    is_active: bool
    is_stale: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductionTimelineResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    script_id: uuid.UUID
    tts_generation_id: uuid.UUID
    version: int
    status: str
    duration: float
    total_scenes: int
    scenes_with_footage: int
    scenes_missing_footage: int
    is_active: bool
    is_stale: bool = False
    stale_reasons: List[str] = []
    average_similarity: Optional[float] = None
    items: List[ProductionTimelineItemSchema] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
