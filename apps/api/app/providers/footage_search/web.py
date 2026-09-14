import logging
from typing import List
from app.providers.footage_search.base import FootageSearchProvider, RawCandidateItem
from app.providers.footage_search.mock import MockFootageSearchProvider

logger = logging.getLogger("shorts_api.footage_search.web")


class WebSearchProvider(FootageSearchProvider):
    """
    Web Video Search Provider for discovering candidate video pages across general web sources.
    Defaults to MockFootageSearchProvider for fast, deterministic local development.
    """

    def __init__(self):
        self._mock_fallback = MockFootageSearchProvider()

    async def search(self, query: str, max_results: int = 10) -> List[RawCandidateItem]:
        logger.info(f"WebSearchProvider searching for: '{query}'")
        # For development / initial implementation, use mock candidates tagged with 'web' platform
        candidates = await self._mock_fallback.search(query, max_results)
        for c in candidates:
            c.platform = "web"
        return candidates
