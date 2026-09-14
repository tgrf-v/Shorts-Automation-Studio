import logging
from typing import Optional
from app.core.config import settings
from app.providers.script.base import ScriptGenerationProvider
from app.providers.script.mock import MockScriptProvider
from app.providers.script.gemini import GeminiScriptProvider
from app.providers.script.openai import OpenAIScriptProvider

logger = logging.getLogger("shorts_api.providers.script")


def get_script_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None
) -> ScriptGenerationProvider:
    """
    Factory function returning the configured script adaptation provider.
    Defaults to GeminiScriptProvider unless 'mock' or 'openai' is specified.
    """
    chosen = (provider_name or settings.SCRIPT_PROVIDER or "gemini").lower().strip()

    if chosen == "gemini":
        return GeminiScriptProvider(api_key=settings.GEMINI_API_KEY, model=model)

    elif chosen == "openai":
        return OpenAIScriptProvider(api_key=settings.OPENAI_API_KEY, model=model)

    elif chosen == "mock":
        return MockScriptProvider()

    else:
        logger.warning(f"Unknown SCRIPT_PROVIDER '{chosen}'. Defaulting to MockScriptProvider.")
        return MockScriptProvider()


__all__ = [
    "ScriptGenerationProvider",
    "MockScriptProvider",
    "GeminiScriptProvider",
    "OpenAIScriptProvider",
    "get_script_provider",
]
