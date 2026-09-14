import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.timeline import production_timeline_service
from app.schemas.timeline import (
    ProductionTimelineGenerateRequest,
    ProductionTimelineResponse,
    ProductionTimelineSummaryResponse,
    ProductionTimelineItemUpdateRequest,
)

logger = logging.getLogger("shorts_api.api.v1.timeline")

timeline_router = APIRouter(tags=["Production Timeline (Milestone 7)"])


@timeline_router.post(
    "/projects/{project_id}/production-timeline/generate",
    response_model=ProductionTimelineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Production Timeline",
    description="Combines Reference Scenes (M3), Indonesian Script (M4), TTS Narration Audio (M5), and Selected Footage (M6) into a new timeline version."
)
async def generate_production_timeline(
    project_id: uuid.UUID,
    payload: Optional[ProductionTimelineGenerateRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    script_id = payload.script_id if payload else None
    tts_generation_id = payload.tts_generation_id if payload else None

    return await production_timeline_service.generate_timeline(
        db=db,
        project_id=project_id,
        script_id=script_id,
        tts_generation_id=tts_generation_id,
    )


@timeline_router.get(
    "/projects/{project_id}/production-timeline",
    response_model=Optional[ProductionTimelineResponse],
    summary="Get Active Production Timeline",
    description="Retrieves current active production timeline for a project, including stale state detection."
)
async def get_active_production_timeline(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    tl = await production_timeline_service.get_active_timeline(db, project_id)
    if not tl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active production timeline found for this project."
        )
    return tl


@timeline_router.get(
    "/projects/{project_id}/production-timeline/versions",
    response_model=List[ProductionTimelineSummaryResponse],
    summary="List Production Timeline Versions",
    description="Retrieves all production timeline versions for a project."
)
async def get_production_timeline_versions(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    return await production_timeline_service.get_timeline_versions(db, project_id)


@timeline_router.get(
    "/production-timelines/{timeline_id}",
    response_model=ProductionTimelineResponse,
    summary="Get Production Timeline Details",
    description="Retrieves a specific production timeline by ID with items, keyframes, and candidate metadata."
)
async def get_production_timeline_by_id(
    timeline_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    tl = await production_timeline_service.get_timeline(db, timeline_id)
    if not tl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Production timeline not found."
        )
    return tl


@timeline_router.post(
    "/production-timelines/{timeline_id}/activate",
    response_model=ProductionTimelineResponse,
    summary="Activate Production Timeline",
    description="Marks this timeline as the active production version for the project."
)
async def activate_production_timeline(
    timeline_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    return await production_timeline_service.activate_timeline(db, timeline_id)


@timeline_router.patch(
    "/production-timeline-items/{item_id}",
    response_model=ProductionTimelineResponse,
    summary="Update Production Timeline Item",
    description="Allows editing footage selection, manual trim timings (start/end), transition, and notes. Narration timing is immutable."
)
async def update_production_timeline_item(
    item_id: uuid.UUID,
    payload: ProductionTimelineItemUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    return await production_timeline_service.update_timeline_item(
        db=db,
        item_id=item_id,
        footage_candidate_id=payload.footage_candidate_id,
        footage_start_time=payload.footage_start_time,
        footage_end_time=payload.footage_end_time,
        transition=payload.transition,
        notes=payload.notes,
    )
