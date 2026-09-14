import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.audio_mix import AudioType, AudioTimelineStatus


class AudioAssetBase(BaseModel):
    name: str
    type: AudioType
    source_url: Optional[str] = None
    volume: float = 0.0


class AudioAssetCreate(BaseModel):
    name: Optional[str] = None
    type: AudioType
    file_path: str
    source_url: Optional[str] = None
    volume: float = 0.0


class AudioAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    type: str
    name: str
    file_path: str
    source_url: Optional[str] = None
    duration: float
    format: str
    sample_rate: int
    channels: int
    volume: float
    created_at: datetime
    updated_at: datetime


class AudioLayerCreate(BaseModel):
    audio_asset_id: uuid.UUID
    type: AudioType
    name: Optional[str] = None
    start_time: float = 0.0
    end_time: Optional[float] = None
    volume: Optional[float] = None
    fade_in: float = 0.0
    fade_out: float = 0.0
    loop: Optional[bool] = None
    enabled: bool = True
    ducking_enabled: Optional[bool] = None
    ducking_level: float = -6.0
    scene_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class AudioLayerUpdate(BaseModel):
    name: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    volume: Optional[float] = None
    fade_in: Optional[float] = None
    fade_out: Optional[float] = None
    loop: Optional[bool] = None
    enabled: Optional[bool] = None
    ducking_enabled: Optional[bool] = None
    ducking_level: Optional[float] = None
    notes: Optional[str] = None


class AudioLayerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    audio_timeline_id: uuid.UUID
    audio_asset_id: uuid.UUID
    scene_id: Optional[uuid.UUID] = None
    type: str
    name: str
    start_time: float
    end_time: float
    volume: float
    fade_in: float
    fade_out: float
    loop: bool
    enabled: bool
    ducking_enabled: bool
    ducking_level: float
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    audio_asset: Optional[AudioAssetResponse] = None


class AudioTimelineGenerateRequest(BaseModel):
    bgm_asset_id: Optional[uuid.UUID] = None
    production_timeline_id: Optional[uuid.UUID] = None
    ducking_enabled: bool = True
    ducking_level: float = -6.0


class AudioTimelineSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    production_timeline_id: uuid.UUID
    version: int
    status: str
    total_duration: float
    is_active: bool
    ducking_enabled: bool
    ducking_level: float
    total_layers: int = 0
    bgm_layers_count: int = 0
    sfx_layers_count: int = 0
    created_at: datetime


class AudioTimelineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    production_timeline_id: uuid.UUID
    version: int
    status: str
    total_duration: float
    is_active: bool
    ducking_enabled: bool
    ducking_level: float
    created_at: datetime
    updated_at: datetime
    is_stale: bool = False
    stale_reasons: List[str] = []
    layers: List[AudioLayerResponse] = []
