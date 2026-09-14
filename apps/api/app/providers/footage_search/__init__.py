import logging
from typing import Optional
from app.core.config import settings
from app.providers.footage_search.base import FootageSearchProvider, RawCandidateItem
from app.providers.footage_search.youtube import YouTubeSearchProvider
from app.providers.footage_search.web import WebSearchProvider
from app.providers.footage_search.mock import MockFootageSearchProvider

logger = logging.getLogger("shorts_api.footage_search.factory")


def get_footage_search_provider(name: Optional[str] = None) -> FootageSearchProvider:
    """
    Factory resolving FootageSearchProvider implementation based on request or config.
    """
    prov_name = (name or getattr(settings, "FOOTAGE_SEARCH_PROVIDER", "youtube")).strip().lower()

    if prov_name in ("mock", "offline"):
        return MockFootageSearchProvider()

    if prov_name in ("youtube", "yt"):
        return YouTubeSearchProvider()

    if prov_name in ("web", "bing", "google_video"):
        return WebSearchProvider()

    logger.warning(f"Unknown footage search provider '{name}', defaulting to MockFootageSearchProvider.")
    return MockFootageSearchProvider()


__all__ = [
    "FootageSearchProvider",
    "RawCandidateItem",
    "YouTubeSearchProvider",
    "WebSearchProvider",
    "MockFootageSearchProvider",
    "get_footage_search_provider",
]
