import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.script_job import ScriptJob
from app.schemas.script import (
    ScriptGenerateRequest,
    ScriptGenerateResponse,
    ScriptResponse,
    ScriptSummaryResponse,
    ScriptUpdateRequest,
    ScriptJobResponse,
)
from app.services.script.script_service import script_service

router = APIRouter(tags=["Script Adaptation"])


@router.post(
    "/projects/{project_id}/scripts/generate",
    response_model=ScriptGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate Indonesian script from analyzed reference"
)
async def generate_script(
    project_id: uuid.UUID,
    payload: Optional[ScriptGenerateRequest] = None,
    db: AsyncSession = Depends(get_db)
) -> ScriptGenerateResponse:
    """
    Creates an asynchronous script adaptation job and enqueues task to worker.
    """
    req = payload or ScriptGenerateRequest()
    try:
        job, script = await script_service.create_and_enqueue_job(
            db=db,
            project_id=project_id,
            provider=req.provider,
            model=req.model,
            instructions=req.instructions,
            source_transcript_id=req.source_transcript_id
        )
        return ScriptGenerateResponse(
            job_id=job.id,
            script_id=script.id,
            status=job.status.value
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate script generation: {exc}"
        )


@router.get(
    "/projects/{project_id}/scripts",
    response_model=List[ScriptSummaryResponse],
    summary="List all script versions for a project"
)
async def list_project_scripts(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> List[ScriptSummaryResponse]:
    """Returns all script versions generated for the project ordered by version descending."""
    scripts = await script_service.list_project_scripts(db, project_id)
    return [ScriptSummaryResponse.model_validate(s) for s in scripts]


@router.get(
    "/scripts/{script_id}",
    response_model=ScriptResponse,
    summary="Get script details by ID"
)
async def get_script(
    script_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> ScriptResponse:
    """Retrieves full script detail including scene-aligned segments and duration metrics."""
    try:
        script = await script_service.get_script(db, script_id)
        return ScriptResponse.model_validate(script)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )


@router.patch(
    "/scripts/{script_id}",
    response_model=ScriptResponse,
    summary="Manually update an existing script"
)
async def update_script(
    script_id: uuid.UUID,
    payload: ScriptUpdateRequest,
    db: AsyncSession = Depends(get_db)
) -> ScriptResponse:
    """
    Manually edits title, full script, or scene segments.
    Recalculates duration metrics and flags is_manually_edited=True without calling AI.
    """
    try:
        updated = await script_service.update_script(
            db=db,
            script_id=script_id,
            title=payload.title,
            content=payload.content,
            segments=payload.segments
        )
        return ScriptResponse.model_validate(updated)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update script: {exc}"
        )


@router.post(
    "/scripts/{script_id}/activate",
    response_model=ScriptResponse,
    summary="Activate a specific script version"
)
async def activate_script(
    script_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> ScriptResponse:
    """
    Sets the specified script version as the active script for this project.
    Deactivates all other versions for downstream TTS processing.
    """
    try:
        activated = await script_service.activate_script(db, script_id)
        return ScriptResponse.model_validate(activated)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )


@router.get(
    "/script-jobs/{job_id}",
    response_model=ScriptJobResponse,
    summary="Get script generation job status and progress by ID"
)
async def get_script_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> ScriptJobResponse:
    """Returns real-time progress and status of a script adaptation background job."""
    stmt = select(ScriptJob).where(ScriptJob.id == job_id)
    job = (await db.execute(stmt)).scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Script adaptation job with ID '{job_id}' not found."
        )
    return ScriptJobResponse.model_validate(job)
