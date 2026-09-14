from typing import List

# Ensure FFmpeg and FFprobe binaries are in PATH if static-ffmpeg is installed
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception:
    pass

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    from pydantic import BaseModel as BaseSettings
    SettingsConfigDict = None
    HAS_PYDANTIC_SETTINGS = False


class Settings(BaseSettings):
    APP_NAME: str = "Shorts Automation Studio API"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres_password_dev@postgres:5432/shorts_automation"
    REDIS_URL: str = "redis://redis:6379/0"
    QDRANT_URL: str = "http://qdrant:6333"

    # Media Storage & Upload
    MEDIA_STORAGE_PATH: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 500
    ALLOWED_VIDEO_EXTENSIONS: List[str] = [".mp4", ".mov", ".webm"]
    ALLOWED_VIDEO_MIME_TYPES: List[str] = [
        "video/mp4",
        "video/quicktime",
        "video/webm",
        "application/octet-stream"  # Fallback for some browsers on webm/mov
    ]

    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GOOGLE_TTS_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = ""

    # Reference Analysis Settings
    STT_PROVIDER: str = "faster_whisper"
    WHISPER_MODEL: str = "tiny"
    KEYFRAMES_PER_SCENE: int = 3
    ANALYSIS_MAX_DURATION_SECONDS: int = 180
    ANALYSIS_QUEUE_NAME: str = "shorts:queue:analysis"

    # Milestone 4: Script Adaptation Settings
    SCRIPT_PROVIDER: str = "gemini"
    SCRIPT_MODEL: str = "gemini-2.5-flash"
    SCRIPT_TARGET_WPM: int = 150
    SCRIPT_MAX_DURATION_RATIO: float = 1.15
    SCRIPT_MIN_DURATION_RATIO: float = 0.85
    SCRIPT_QUEUE_NAME: str = "shorts:queue:script"

    # Milestone 5: TTS & Audio Timeline Settings
    TTS_PROVIDER: str = "google"
    TTS_MODEL: str = ""
    TTS_VOICE: str = "id-ID-Standard-A"
    TTS_QUEUE_NAME: str = "shorts:queue:tts"

    # Milestone 6: Visual Footage Search Settings
    FOOTAGE_SEARCH_PROVIDER: str = "youtube"
    FOOTAGE_SEARCH_QUEUE_NAME: str = "shorts:queue:footage_search"
    FOOTAGE_MAX_QUERIES_PER_SCENE: int = 4
    FOOTAGE_MAX_RESULTS_PER_QUERY: int = 10
    FOOTAGE_MAX_TOTAL_CANDIDATES: int = 30
    FOOTAGE_VISUAL_WEIGHT: float = 0.60
    FOOTAGE_CONTEXT_WEIGHT: float = 0.25
    FOOTAGE_METADATA_WEIGHT: float = 0.15
    YOUTUBE_API_KEY: str = ""
    QDRANT_COLLECTION_FOOTAGE: str = "scene_visual_embeddings"

    if HAS_PYDANTIC_SETTINGS and SettingsConfigDict is not None:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=True,
            extra="ignore"
        )



settings = Settings()
