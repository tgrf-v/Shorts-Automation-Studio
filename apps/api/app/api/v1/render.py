import os
import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.render import (
    RenderJobCreateRequest,
    RenderChecklistResponse,
    RenderJobSummary,
    RenderJobResponse
)
from app.services.renderer.config import RenderConfig
from app.services.renderer.render_service import RenderService

logger = logging.getLogger("shorts_api.api.render")

render_router = APIRouter(tags=["Video Rendering & Composition"])
render_service = RenderService()


@render_router.get(
    "/projects/{project_id}/render-checklist",
    response_model=RenderChecklistResponse,
    summary="Check pre-flight dependencies before video rendering"
)
async def get_render_checklist(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    checklist = await render_service.validate_dependencies(db, project_id)
    return checklist


@render_router.post(
    "/projects/{project_id}/renders",
    response_model=RenderJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start video rendering job"
)
async def start_render_job(
    project_id: uuid.UUID,
    payload: Optional[RenderJobCreateRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    cfg = None
    if payload and payload.config:
        cfg = RenderConfig(**payload.config.model_dump())

    try:
        job = await render_service.create_render_job(db, project_id, config=cfg)
        return job
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to initiate render job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@render_router.get(
    "/projects/{project_id}/renders",
    response_model=List[RenderJobSummary],
    summary="List render jobs for a project"
)
async def list_project_render_jobs(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    jobs = await render_service.list_render_jobs(db, project_id)
    summaries = []
    for j in jobs:
        summaries.append(
            RenderJobSummary(
                id=j.id,
                project_id=j.project_id,
                status=j.status.value if hasattr(j.status, 'value') else str(j.status),
                progress=j.progress,
                current_step=j.current_step,
                output_format=j.output_format,
                output_duration=j.output_duration,
                file_size=j.file_size,
                started_at=j.started_at,
                completed_at=j.completed_at,
                created_at=j.created_at
            )
        )
    return summaries


@render_router.get(
    "/render-jobs/{job_id}",
    response_model=RenderJobResponse,
    summary="Get render job details and live progress"
)
async def get_render_job_details(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    job = await render_service.get_render_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Render job {job_id} not found.")
    return job


@render_router.post(
    "/render-jobs/{job_id}/cancel",
    response_model=RenderJobResponse,
    summary="Cancel a render job"
)
async def cancel_render_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    success = await render_service.cancel_render_job(db, job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel render job.")
    job = await render_service.get_render_job(db, job_id)
    return job


@render_router.get(
    "/render-jobs/{job_id}/stream",
    summary="Stream rendered video for browser playback"
)
async def stream_rendered_video(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    job = await render_service.get_render_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Render job {job_id} not found.")

    if not job.output_path or not os.path.exists(job.output_path):
        raise HTTPException(status_code=404, detail="Rendered video file is not ready or not found on disk.")

    return FileResponse(job.output_path, media_type="video/mp4")


@render_router.get(
    "/render-jobs/{job_id}/download",
    summary="Download rendered video MP4"
)
async def download_rendered_video(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    job = await render_service.get_render_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Render job {job_id} not found.")

    if not job.output_path or not os.path.exists(job.output_path):
        raise HTTPException(status_code=404, detail="Rendered video file is not ready or not found on disk.")

    filename = f"shorts_{job.project_id}_{job.id}.mp4"
    return FileResponse(
        job.output_path,
        media_type="video/mp4",
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
