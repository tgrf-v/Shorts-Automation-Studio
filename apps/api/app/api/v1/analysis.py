import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.project import Project
from app.models.analysis_job import AnalysisJob
from app.models.transcript import Transcript
from app.models.scene import Scene
from app.schemas.analysis import (
    AnalysisJobResponse,
    ProjectAnalysisResponse,
    TranscriptResponse,
    SceneResponse
)
from app.services.analysis.media_analysis import reference_analysis_service

router = APIRouter(tags=["Reference Analysis"])


@router.post(
    "/projects/{project_id}/analyze",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger reference video analysis"
)
async def analyze_project(
    project_id: uuid.UUID,
    reanalyze: bool = Query(default=False, description="Force re-analysis even if already completed"),
    db: AsyncSession = Depends(get_db)
) -> AnalysisJobResponse:
    try:
        job = await reference_analysis_service.create_and_enqueue_job(
            db=db,
            project_id=project_id,
            reanalyze=reanalyze
        )
        return job
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger analysis: {exc}"
        )


@router.get(
    "/projects/{project_id}/analysis",
    response_model=ProjectAnalysisResponse,
    summary="Get reference analysis results for a project"
)
async def get_project_analysis(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> ProjectAnalysisResponse:
    project_stmt = select(Project).where(Project.id == project_id)
    project = (await db.execute(project_stmt)).scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found."
        )

    # Get latest analysis job
    job_stmt = (
        select(AnalysisJob)
        .where(AnalysisJob.project_id == project_id)
        .order_by(AnalysisJob.created_at.desc())
    )
    job = (await db.execute(job_stmt)).scalars().first()

    # Get transcript
    transcript_stmt = (
        select(Transcript)
        .where(Transcript.project_id == project_id)
        .order_by(Transcript.version.desc())
    )
    transcript = (await db.execute(transcript_stmt)).scalars().first()

    # Get scenes with keyframes
    scenes_stmt = (
        select(Scene)
        .where(Scene.project_id == project_id)
        .options(selectinload(Scene.keyframes))
        .order_by(Scene.sequence.asc())
    )
    scenes = (await db.execute(scenes_stmt)).scalars().all()

    return ProjectAnalysisResponse(
        project_id=project.id,
        status=project.status.value,
        job=AnalysisJobResponse.model_validate(job) if job else None,
        transcript=TranscriptResponse.model_validate(transcript) if transcript else None,
        scenes=[SceneResponse.model_validate(s) for s in scenes]
    )


@router.get(
    "/analysis-jobs/{job_id}",
    response_model=AnalysisJobResponse,
    summary="Get analysis job status and progress by ID"
)
async def get_analysis_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> AnalysisJobResponse:
    stmt = select(AnalysisJob).where(AnalysisJob.id == job_id)
    job = (await db.execute(stmt)).scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Analysis job with ID '{job_id}' not found."
        )
    return job


@router.get(
    "/keyframes/{keyframe_id}/image",
    summary="Serve keyframe image safely by keyframe ID"
)
async def get_keyframe_image(
    keyframe_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    import os
    from fastapi.responses import FileResponse
    from app.models.keyframe import Keyframe
    from app.providers.storage.local import storage_provider

    stmt = select(Keyframe).where(Keyframe.id == keyframe_id)
    kf = (await db.execute(stmt)).scalar_one_or_none()
    if not kf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Keyframe with ID '{keyframe_id}' not found."
        )

    full_path = storage_provider.get_full_path(kf.image_path)
    if not os.path.exists(full_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Keyframe image file missing from server storage."
        )

    return FileResponse(
        path=full_path,
        media_type="image/jpeg",
        filename=f"keyframe_{keyframe_id}.jpg",
        content_disposition_type="inline"
    )

