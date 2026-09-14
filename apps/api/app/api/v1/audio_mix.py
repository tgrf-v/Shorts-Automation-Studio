import os
import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.audio_mix import AudioType
from app.schemas.audio_mix import (
    AudioAssetCreate,
    AudioAssetResponse,
    AudioLayerCreate,
    AudioLayerUpdate,
    AudioLayerResponse,
    AudioTimelineGenerateRequest,
    AudioTimelineSummary,
    AudioTimelineResponse
)
from app.services.audio.asset_service import AudioAssetService
from app.services.audio.audio_timeline_service import AudioTimelineService
from app.services.audio.sfx_suggestion_service import SFXSuggestionService, SceneSFXSuggestionsResponse

logger = logging.getLogger("shorts_api.api.audio_mix")

audio_mix_router = APIRouter(tags=["BGM & SFX Timeline"])
asset_service = AudioAssetService()


# -------------------------------------------------------------
# Audio Asset Endpoints
# -------------------------------------------------------------

@audio_mix_router.post(
    "/projects/{project_id}/audio-assets/upload",
    response_model=AudioAssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an audio asset (BGM or SFX)"
)
async def upload_audio_asset(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    type: AudioType = Form(...),
    name: Optional[str] = Form(None),
    volume: Optional[float] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    try:
        content = await file.read()
        asset = await asset_service.register_uploaded_asset(
            db=db,
            content=content,
            filename=file.filename or "audio_track.mp3",
            asset_type=type,
            project_id=project_id,
            name=name,
            custom_volume=volume
        )
        return asset
    except Exception as e:
        logger.error(f"Error uploading audio asset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@audio_mix_router.post(
    "/projects/{project_id}/audio-assets",
    response_model=AudioAssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a local audio file as an asset"
)
async def register_audio_asset(
    project_id: uuid.UUID,
    payload: AudioAssetCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        asset = await asset_service.register_local_file_asset(
            db=db,
            file_path=payload.file_path,
            asset_type=payload.type,
            project_id=project_id,
            name=payload.name,
            source_url=payload.source_url,
            custom_volume=payload.volume
        )
        return asset
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error registering audio asset: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@audio_mix_router.get(
    "/projects/{project_id}/audio-assets",
    response_model=List[AudioAssetResponse],
    summary="List audio assets for a project"
)
async def list_project_audio_assets(
    project_id: uuid.UUID,
    type: Optional[AudioType] = Query(None, description="Filter by bgm or sfx"),
    db: AsyncSession = Depends(get_db)
):
    assets = await asset_service.list_assets(db, project_id=project_id, asset_type=type)
    return assets


@audio_mix_router.get(
    "/audio-assets/{asset_id}",
    response_model=AudioAssetResponse,
    summary="Get audio asset details"
)
async def get_audio_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    asset = await asset_service.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Audio asset {asset_id} not found.")
    return asset


@audio_mix_router.get(
    "/audio-assets/{asset_id}/stream",
    summary="Stream audio asset for preview"
)
async def stream_audio_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    asset = await asset_service.get_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Audio asset {asset_id} not found.")

    abs_path = asset_service.storage.get_absolute_path(asset.file_path)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="Audio file not found on disk.")

    media_type = "audio/mpeg"
    if asset.format in ["wav", "wave"]:
        media_type = "audio/wav"
    elif asset.format in ["ogg"]:
        media_type = "audio/ogg"

    return FileResponse(abs_path, media_type=media_type)


@audio_mix_router.delete(
    "/audio-assets/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete audio asset"
)
async def delete_audio_asset(
    asset_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    success = await asset_service.delete_asset(db, asset_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Audio asset {asset_id} not found.")
    return None


# -------------------------------------------------------------
# Audio Timeline Endpoints
# -------------------------------------------------------------

@audio_mix_router.post(
    "/projects/{project_id}/audio-timeline/generate",
    response_model=AudioTimelineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate new audio timeline version"
)
async def generate_audio_timeline(
    project_id: uuid.UUID,
    payload: Optional[AudioTimelineGenerateRequest] = None,
    db: AsyncSession = Depends(get_db)
):
    req = payload or AudioTimelineGenerateRequest()
    try:
        timeline = await AudioTimelineService.generate_audio_timeline(
            db=db,
            project_id=project_id,
            bgm_asset_id=req.bgm_asset_id,
            production_timeline_id=req.production_timeline_id,
            ducking_enabled=req.ducking_enabled,
            ducking_level=req.ducking_level
        )
        tl_full = await AudioTimelineService.get_timeline_by_id(db, timeline.id)
        return tl_full
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate audio timeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@audio_mix_router.get(
    "/projects/{project_id}/audio-timeline",
    response_model=AudioTimelineResponse,
    summary="Get active audio timeline with stale diagnostics"
)
async def get_active_audio_timeline(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    timeline, is_stale, stale_reasons = await AudioTimelineService.get_active_timeline(db, project_id)
    if not timeline:
        raise HTTPException(status_code=404, detail=f"No active audio timeline found for project {project_id}.")

    resp = AudioTimelineResponse.model_validate(timeline)
    resp.is_stale = is_stale
    resp.stale_reasons = stale_reasons
    return resp


@audio_mix_router.get(
    "/projects/{project_id}/audio-timeline/versions",
    response_model=List[AudioTimelineSummary],
    summary="List audio timeline versions for project"
)
async def list_audio_timeline_versions(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    versions = await AudioTimelineService.list_versions(db, project_id)
    summaries = []
    for v in versions:
        bgm_count = sum(1 for l in v.layers if l.type == AudioType.BGM)
        sfx_count = sum(1 for l in v.layers if l.type == AudioType.SFX)
        summaries.append(
            AudioTimelineSummary(
                id=v.id,
                project_id=v.project_id,
                production_timeline_id=v.production_timeline_id,
                version=v.version,
                status=v.status.value if hasattr(v.status, 'value') else str(v.status),
                total_duration=v.total_duration,
                is_active=v.is_active,
                ducking_enabled=v.ducking_enabled,
                ducking_level=v.ducking_level,
                total_layers=len(v.layers),
                bgm_layers_count=bgm_count,
                sfx_layers_count=sfx_count,
                created_at=v.created_at
            )
        )
    return summaries


@audio_mix_router.get(
    "/audio-timelines/{timeline_id}",
    response_model=AudioTimelineResponse,
    summary="Get audio timeline by ID"
)
async def get_audio_timeline_by_id(
    timeline_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    timeline = await AudioTimelineService.get_timeline_by_id(db, timeline_id)
    if not timeline:
        raise HTTPException(status_code=404, detail=f"Audio timeline {timeline_id} not found.")
    return timeline


@audio_mix_router.post(
    "/audio-timelines/{timeline_id}/activate",
    response_model=AudioTimelineResponse,
    summary="Activate audio timeline version"
)
async def activate_audio_timeline(
    timeline_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    try:
        timeline = await AudioTimelineService.activate_timeline(db, timeline_id)
        return timeline
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@audio_mix_router.get(
    "/audio-timelines/{timeline_id}/mix-config",
    summary="Get renderer-ready structured audio mix configuration"
)
async def get_audio_mix_config(
    timeline_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    try:
        config = await AudioTimelineService.get_renderer_mix_config(db, timeline_id)
        return config
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# -------------------------------------------------------------
# Audio Layer Endpoints
# -------------------------------------------------------------

@audio_mix_router.post(
    "/projects/{project_id}/audio-layers",
    response_model=AudioLayerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an audio layer (BGM or SFX)"
)
async def add_audio_layer(
    project_id: uuid.UUID,
    payload: AudioLayerCreate,
    timeline_id: Optional[uuid.UUID] = Query(None, description="Audio timeline ID to attach layer to"),
    db: AsyncSession = Depends(get_db)
):
    # If timeline_id not passed, find active audio timeline
    target_tl_id = timeline_id
    if not target_tl_id:
        active_tl, _, _ = await AudioTimelineService.get_active_timeline(db, project_id)
        if not active_tl:
            raise HTTPException(
                status_code=400,
                detail="No active audio timeline found. Please generate an audio timeline first."
            )
        target_tl_id = active_tl.id

    try:
        layer = await AudioTimelineService.add_layer(
            db=db,
            project_id=project_id,
            audio_timeline_id=target_tl_id,
            audio_asset_id=payload.audio_asset_id,
            layer_type=payload.type,
            name=payload.name,
            start_time=payload.start_time,
            end_time=payload.end_time,
            volume=payload.volume,
            fade_in=payload.fade_in,
            fade_out=payload.fade_out,
            loop=payload.loop,
            enabled=payload.enabled,
            ducking_enabled=payload.ducking_enabled,
            ducking_level=payload.ducking_level,
            scene_id=payload.scene_id,
            notes=payload.notes
        )
        return layer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add audio layer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@audio_mix_router.patch(
    "/audio-layers/{layer_id}",
    response_model=AudioLayerResponse,
    summary="Update audio layer properties"
)
async def update_audio_layer(
    layer_id: uuid.UUID,
    payload: AudioLayerUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        layer = await AudioTimelineService.update_layer(
            db=db,
            layer_id=layer_id,
            name=payload.name,
            start_time=payload.start_time,
            end_time=payload.end_time,
            volume=payload.volume,
            fade_in=payload.fade_in,
            fade_out=payload.fade_out,
            loop=payload.loop,
            enabled=payload.enabled,
            ducking_enabled=payload.ducking_enabled,
            ducking_level=payload.ducking_level,
            notes=payload.notes
        )
        return layer
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@audio_mix_router.delete(
    "/audio-layers/{layer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete audio layer"
)
async def delete_audio_layer(
    layer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    success = await AudioTimelineService.delete_layer(db, layer_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Audio layer {layer_id} not found.")
    return None


# -------------------------------------------------------------
# SFX Suggestions Endpoint
# -------------------------------------------------------------

@audio_mix_router.get(
    "/scenes/{scene_id}/sfx-suggestions",
    response_model=SceneSFXSuggestionsResponse,
    summary="Get rule-based SFX placement suggestions for a scene"
)
async def get_scene_sfx_suggestions(
    scene_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
):
    suggestions = await SFXSuggestionService.suggest_sfx_for_scene(db, scene_id)
    return suggestions
