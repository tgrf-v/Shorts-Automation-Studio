import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.models.media_asset import MediaAssetType


class MediaAssetResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    type: MediaAssetType
    filename: str
    storage_path: str
    source_url: Optional[str] = None
    source_platform: Optional[str] = None
    mime_type: str
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    codec: Optional[str] = None
    size: int
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

