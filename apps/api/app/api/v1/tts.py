import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.tts_generation import TTSGeneration
from app.models.audio_segment import AudioSegment
from app.models.tts_job import TTSJob
from app.providers.storage.local import storage_provider
from app.providers.tts import get_tts_provider
from app.services.tts.tts_service import tts_service
from app.schemas.tts import (
    TTSGenerateRequest,
    TTSGenerateResponse,
    TTSGenerationSummaryResponse,
    TTSGenerationResponse,
    AudioTimelineSchema,
    TTSJobResponse,
    TTSVoiceSchema,
)

router = APIRouter(tags=["TTS & Audio Timeline"])


# 1. Generate TTS
@router.post(
    "/projects/{project_id}/tts/generate",
    response_model=TTSGenerateResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue a Text-to-Speech narration generation job"
)
async def generate_tts(
    project_id: uuid.UUID,
    payload: TTSGenerateRequest = TTSGenerateRequest(),
    db: AsyncSession = Depends(get_db)
) -> TTSGenerateResponse:
    try:
        job, generation = await tts_service.create_and_enqueue_job(
            db=db,
            project_id=project_id,
            script_id=payload.script_id,
            provider=payload.provider,
            voice=payload.voice,
            model=payload.model
        )
        return TTSGenerateResponse(
            generation_id=generation.id,
            job_id=job.id,
            status=job.status.value
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to queue TTS job: {exc}")


# 2. List TTS Generations for Project
@router.get(
    "/projects/{project_id}/tts",
    response_model=List[TTSGenerationSummaryResponse],
    summary="List all TTS narration generations for a project"
)
async def list_project_tts_generations(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> List[TTSGenerationSummaryResponse]:
    stmt = (
        select(TTSGeneration)
        .where(TTSGeneration.project_id == project_id)
        .order_by(desc(TTSGeneration.created_at))
    )
    result = await db.execute(stmt)
    generations = result.scalars().all()
    return list(generations)


# 3. Get Voices
@router.get(
    "/tts/voices",
    response_model=List[TTSVoiceSchema],
    summary="List available voices for a TTS provider"
)
async def get_voices(
    provider: Optional[str] = Query(default=None, description="TTS provider name ('google', 'elevenlabs', 'mock')")
) -> List[TTSVoiceSchema]:
    prov = get_tts_provider(provider)
    voices = await prov.get_available_voices()
    return [
        TTSVoiceSchema(
            id=v.id,
            name=v.name,
            gender=v.gender,
            language_codes=v.language_codes,
            description=v.description
        )
        for v in voices
    ]


# 4. Get TTS Job
@router.get(
    "/tts/jobs/{job_id}",
    response_model=TTSJobResponse,
    summary="Get status and progress of a TTS generation job"
)
async def get_tts_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> TTSJobResponse:
    stmt = select(TTSJob).where(TTSJob.id == job_id)
    job = (await db.execute(stmt)).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"TTS job '{job_id}' not found.")
    return job


# 5. Get TTS Generation Detail
@router.get(
    "/tts/{generation_id}",
    response_model=TTSGenerationResponse,
    summary="Get detailed TTS generation metadata and segments"
)
async def get_tts_generation(
    generation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> TTSGenerationResponse:
    stmt = (
        select(TTSGeneration)
        .where(TTSGeneration.id == generation_id)
        .options(selectinload(TTSGeneration.segments))
    )
    gen = (await db.execute(stmt)).scalar_one_or_none()
    if not gen:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"TTSGeneration '{generation_id}' not found.")
    return gen


# 6. Get Audio Timeline
@router.get(
    "/tts/{generation_id}/timeline",
    response_model=AudioTimelineSchema,
    summary="Get structured audio timeline and segment timings"
)
async def get_tts_timeline(
    generation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> AudioTimelineSchema:
    try:
        data = await tts_service.get_timeline(db, generation_id)
        return AudioTimelineSchema(**data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# 7. Activate TTS Generation
@router.post(
    "/tts/{generation_id}/activate",
    response_model=TTSGenerationSummaryResponse,
    summary="Mark a TTS generation as the active audio narration for the project"
)
async def activate_tts_generation(
    generation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> TTSGenerationSummaryResponse:
    try:
        gen = await tts_service.activate_generation(db, generation_id)
        return gen
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# 8. Stream Narration Audio
@router.get(
    "/tts/{generation_id}/stream",
    summary="Stream full master narration audio file"
)
async def stream_narration(
    generation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> FileResponse:
    stmt = select(TTSGeneration).where(TTSGeneration.id == generation_id)
    gen = (await db.execute(stmt)).scalar_one_or_none()
    if not gen:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TTS generation not found.")

    if not gen.audio_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Narration audio not generated yet.")

    full_path = storage_provider.get_full_path(gen.audio_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file missing from server storage.")

    media_type = "audio/mpeg" if gen.audio_format == "mp3" else "audio/wav"
    return FileResponse(
        path=full_path,
        media_type=media_type,
        filename=os.path.basename(full_path),
        content_disposition_type="inline"
    )


# 9. Stream Individual Segment Audio
@router.get(
    "/tts/segments/{segment_id}/stream",
    summary="Stream individual segment audio file"
)
async def stream_segment_audio(
    segment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> FileResponse:
    stmt = select(AudioSegment).where(AudioSegment.id == segment_id)
    seg = (await db.execute(stmt)).scalar_one_or_none()
    if not seg or not seg.audio_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio segment not found.")

    full_path = storage_provider.get_full_path(seg.audio_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Segment audio file missing.")

    ext = os.path.splitext(full_path)[1].lower()
    media_type = "audio/mpeg" if ext == ".mp3" else "audio/wav"
    return FileResponse(
        path=full_path,
        media_type=media_type,
        filename=os.path.basename(full_path),
        content_disposition_type="inline"
    )
