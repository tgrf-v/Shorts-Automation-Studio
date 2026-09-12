import uuid
from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectListResponse
from app.schemas.media_asset import MediaAssetResponse
from app.services.project_service import project_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project"
)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db)
) -> ProjectResponse:
    project = await project_service.create_project(db, payload.name)
    return project


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List all projects"
)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
) -> ProjectListResponse:
    projects, total = await project_service.list_projects(db, skip=skip, limit=limit)
    return ProjectListResponse(projects=projects, total=total)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project by ID"
)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> ProjectResponse:
    return await project_service.get_project(db, project_id)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project and all associated media"
)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    await project_service.delete_project(db, project_id)


@router.post(
    "/{project_id}/reference",
    response_model=MediaAssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload reference video for a project"
)
async def upload_reference(
    project_id: uuid.UUID,
    file: UploadFile = File(..., description="Reference video file (.mp4, .mov, .webm)"),
    db: AsyncSession = Depends(get_db)
) -> MediaAssetResponse:
    return await project_service.upload_reference(db, project_id, file)


@router.get(
    "/{project_id}/assets",
    response_model=List[MediaAssetResponse],
    summary="List all media assets for a project"
)
async def list_project_assets(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> List[MediaAssetResponse]:
    return await project_service.list_project_assets(db, project_id)
