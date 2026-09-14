from fastapi import APIRouter
from app.schemas.health import HealthResponse
from app.core.config import settings
from app.api.v1.projects import router as projects_router
from app.api.v1.assets import router as assets_router
from app.api.v1.analysis import router as analysis_router
from app.api.v1.scripts import router as scripts_router
from app.api.v1.tts import router as tts_router
from app.api.v1.footage import router as footage_router
from app.api.v1.timeline import timeline_router
from app.api.v1.captions import captions_router
from app.api.v1.audio_mix import audio_mix_router
from app.api.v1.render import render_router

api_v1_router = APIRouter()

# System ping endpoint
@api_v1_router.get("/ping", response_model=HealthResponse, tags=["System"])
async def ping() -> HealthResponse:
    """Ping endpoint under v1 namespace."""
    return HealthResponse(
        status="ok",
        app_env=settings.APP_ENV,
        version="0.1.0"
    )

# Include projects, assets, reference analysis, script adaptation, TTS, footage, timeline, captions, audio mix, and render routes
api_v1_router.include_router(projects_router)
api_v1_router.include_router(assets_router)
api_v1_router.include_router(analysis_router)
api_v1_router.include_router(scripts_router)
api_v1_router.include_router(tts_router)
api_v1_router.include_router(footage_router)
api_v1_router.include_router(timeline_router)
api_v1_router.include_router(captions_router)
api_v1_router.include_router(audio_mix_router)
api_v1_router.include_router(render_router)
