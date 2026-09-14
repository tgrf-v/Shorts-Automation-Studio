import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.captions import caption_generation_service
from app.schemas.captions import (
    CaptionGenerateRequest,
    CaptionTrackResponse,
    CaptionTrackSummaryResponse,
    CaptionSegmentSchema,
    CaptionSegmentUpdateRequest,
)

logger = logging.getLogger("shorts_api.api.v1.captions")

captions_router = APIRouter(tags=["Captions & Subtitles (Milestone 8)"])


@captions_router.post(
    "/projects/{project_id}/captions/generate",
    response_model=CaptionTrackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Captions & Subtitles",
    description="Builds a new versioned caption track from active script (M4), active TTS audio segments (M5), and production timeline (M7)."
)
async def generate_captions(
    project_id: uuid.UUID,
    payload: Optional[CaptionGenerateRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    script_id = payload.script_id if payload else None
    tts_generation_id = payload.tts_generation_id if payload else None
    production_timeline_id = payload.production_timeline_id if payload else None
    target_words = payload.target_words_per_segment if payload else 4

    return await caption_generation_service.generate_captions(
        db=db,
        project_id=project_id,
        script_id=script_id,
        tts_generation_id=tts_generation_id,
        production_timeline_id=production_timeline_id,
        target_words_per_segment=target_words,
    )


@captions_router.get(
    "/projects/{project_id}/captions",
    response_model=List[CaptionTrackSummaryResponse],
    summary="List Caption Track Versions",
    description="Returns summaries of all caption track versions for a project."
)
async def list_caption_tracks(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    return await caption_generation_service.get_caption_track_versions(db, project_id)


@captions_router.get(
    "/projects/{project_id}/captions/active",
    response_model=CaptionTrackResponse,
    summary="Get Active Caption Track",
    description="Retrieves current active caption track for a project with segments and stale state detection."
)
async def get_active_caption_track(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    track = await caption_generation_service.get_active_caption_track(db, project_id)
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active caption track found for this project."
        )
    return track


@captions_router.get(
    "/captions/{caption_track_id}",
    response_model=CaptionTrackResponse,
    summary="Get Caption Track Details",
    description="Retrieves specific caption track by ID with its segments and metrics."
)
async def get_caption_track_by_id(
    caption_track_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    track = await caption_generation_service.get_caption_track(db, caption_track_id)
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caption track not found."
        )
    return track


@captions_router.get(
    "/captions/{caption_track_id}/segments",
    response_model=List[CaptionSegmentSchema],
    summary="Get Caption Track Segments",
    description="Retrieves all segments for a given caption track."
)
async def get_caption_segments(
    caption_track_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    track = await caption_generation_service.get_caption_track(db, caption_track_id)
    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caption track not found."
        )
    return track.get("segments", [])


@captions_router.post(
    "/captions/{caption_track_id}/activate",
    response_model=CaptionTrackResponse,
    summary="Activate Caption Track",
    description="Marks this caption track as active and deactivates prior versions."
)
async def activate_caption_track(
    caption_track_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    return await caption_generation_service.activate_caption_track(db, caption_track_id)


@captions_router.patch(
    "/caption-segments/{segment_id}",
    response_model=CaptionTrackResponse,
    summary="Update Caption Segment",
    description="Edits caption segment text, timings (validated within parent audio segment bounds), style, and position."
)
async def update_caption_segment(
    segment_id: uuid.UUID,
    payload: CaptionSegmentUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    return await caption_generation_service.update_caption_segment(
        db=db,
        segment_id=segment_id,
        text=payload.text,
        start_time=payload.start_time,
        end_time=payload.end_time,
        style=payload.style,
        position=payload.position,
    )


@captions_router.get(
    "/captions/{caption_track_id}/srt",
    summary="Export Captions in SRT Format",
    description="Returns standard SubRip (.srt) formatted subtitle text for video renderers."
)
async def export_caption_srt(
    caption_track_id: uuid.UUID,
    download: bool = False,
    db: AsyncSession = Depends(get_db)
):
    srt_content = await caption_generation_service.export_srt(db, caption_track_id)
    headers = {"Content-Type": "text/plain; charset=utf-8"}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="captions_{caption_track_id}.srt"'

    return Response(content=srt_content, media_type="text/plain", headers=headers)
