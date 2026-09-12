import logging
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.schemas.health import HealthResponse
from app.api.v1.router import api_v1_router

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("shorts_api")

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"]
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint to verify service readiness and liveness.
    Returns ok status along with current environment info.
    """
    try:
        return HealthResponse(
            status="ok",
            app_env=settings.APP_ENV,
            version="0.1.0"
        )
    except Exception as exc:
        logger.error(f"Health check failed with error: {exc}")
        return HealthResponse(
            status="error",
            app_env=settings.APP_ENV,
            version="0.1.0"
        )


@app.on_event("startup")
async def startup_event() -> None:
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    logger.info(f"Shutting down {settings.APP_NAME}")
