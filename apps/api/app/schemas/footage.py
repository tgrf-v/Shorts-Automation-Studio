import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class FootageSearchRequest(BaseModel):
    query: Optional[str] = Field(default=None, description="Custom search query string (defaults to auto-generated)")
    queries: Optional[List[str]] = Field(default=None, description="Optional explicit query list")
    provider: Optional[str] = Field(default=None, description="Provider identifier: 'youtube', 'web', 'mock'")
    max_results: int = Field(default=20, description="Max total candidate results to collect")


class FootageSearchResponse(BaseModel):
    search_id: uuid.UUID
    scene_id: uuid.UUID
    project_id: uuid.UUID
    query: str
    search_provider: str
    status: str
    progress: int
    current_step: str
    total_results: int
    error: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FootageCandidateSchema(BaseModel):
    id: uuid.UUID
    footage_search_id: uuid.UUID
    scene_id: uuid.UUID
    source_platform: str
    source_url: str
    video_url: Optional[str] = None
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    creator: Optional[str] = None
    duration: Optional[float] = None
    published_at: Optional[str] = None
    search_query: Optional[str] = None
    context_score: float
    visual_score: float
    similarity_score: float
    final_score: float
    match_type: str
    is_selected: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SelectCandidateRequest(BaseModel):
    notes: Optional[str] = Field(default=None, description="Optional user notes or timestamps for this footage")


class SceneFootageSelectionSchema(BaseModel):
    id: uuid.UUID
    scene_id: uuid.UUID
    candidate_id: uuid.UUID
    status: str
    notes: Optional[str] = None
    candidate: Optional[FootageCandidateSchema] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SceneFootageSummaryItem(BaseModel):
    scene_id: uuid.UUID
    sequence: int
    start_time: float
    end_time: float
    duration: float
    description: Optional[str] = None
    total_candidates: int
    has_selection: bool
    selected_candidate: Optional[FootageCandidateSchema] = None
