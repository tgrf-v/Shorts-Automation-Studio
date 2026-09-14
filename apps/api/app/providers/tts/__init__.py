import logging
from typing import Optional
from app.core.config import settings
from app.providers.tts.base import TTSProvider, TTSAudioResult, TTSVoiceOption
from app.providers.tts.google import GoogleTTSProvider
from app.providers.tts.elevenlabs import ElevenLabsProvider
from app.providers.tts.mock import MockTTSProvider

logger = logging.getLogger("shorts_api.tts.factory")


def get_tts_provider(provider_name: Optional[str] = None) -> TTSProvider:
    """
    Factory resolving TTSProvider implementation based on request or configuration.
    Defaults to 'google' or 'mock' depending on configuration.
    """
    name = (provider_name or settings.TTS_PROVIDER or "google").strip().lower()

    if name == "mock":
        return MockTTSProvider()

    if name in ("google", "google_tts", "gcloud"):
        return GoogleTTSProvider()

    if name in ("elevenlabs", "11labs"):
        return ElevenLabsProvider()

    logger.warning(f"Unknown TTS provider '{provider_name}'. Falling back to MockTTSProvider.")
    return MockTTSProvider()


__all__ = [
    "TTSProvider",
    "TTSAudioResult",
    "TTSVoiceOption",
    "GoogleTTSProvider",
    "ElevenLabsProvider",
    "MockTTSProvider",
    "get_tts_provider",
]
