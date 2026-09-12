import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.project import ProjectStatus
from app.schemas.media_asset import MediaAssetResponse


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Project name", json_schema_extra={"example": "Viral Science Shorts #1"})


class ProjectResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: ProjectStatus
    reference_asset_id: Optional[uuid.UUID] = None
    reference_asset: Optional[MediaAssetResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}



class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int
