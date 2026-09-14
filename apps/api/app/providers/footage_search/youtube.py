import logging
from typing import List, Optional
import httpx

from app.core.config import settings
from app.providers.footage_search.base import FootageSearchProvider, RawCandidateItem
from app.providers.footage_search.mock import MockFootageSearchProvider

logger = logging.getLogger("shorts_api.footage_search.youtube")


class YouTubeSearchProvider(FootageSearchProvider):
    """
    YouTube Search Provider using YouTube Data API v3 with automatic fallback
    to MockFootageSearchProvider if API credentials are not configured or quota is exceeded.
    """

    SEARCH_ENDPOINT = "https://www.googleapis.com/youtube/v3/search"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.YOUTUBE_API_KEY or settings.GEMINI_API_KEY
        self._mock_fallback = MockFootageSearchProvider()

    async def search(self, query: str, max_results: int = 10) -> List[RawCandidateItem]:
        clean_q = query.strip()
        if not clean_q:
            return []

        if not self.api_key:
            logger.info("YOUTUBE_API_KEY not configured. Falling back to MockFootageSearchProvider.")
            return await self._mock_fallback.search(query, max_results)

        params = {
            "part": "snippet",
            "type": "video",
            "q": clean_q,
            "maxResults": min(max_results, 25),
            "videoDuration": "any",
            "key": self.api_key
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(self.SEARCH_ENDPOINT, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("items", [])
                    results: List[RawCandidateItem] = []

                    for item in items:
                        id_info = item.get("id", {})
                        video_id = id_info.get("videoId")
                        if not video_id:
                            continue

                        snippet = item.get("snippet", {})
                        title = snippet.get("title", "Untitled Video")
                        desc = snippet.get("description", "")
                        channel = snippet.get("channelTitle", "YouTube Creator")
                        published_at = snippet.get("publishedAt")

                        thumbs = snippet.get("thumbnails", {})
                        thumb_url = (
                            thumbs.get("high", {}).get("url") or
                            thumbs.get("medium", {}).get("url") or
                            thumbs.get("default", {}).get("url") or
                            f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
                        )

                        watch_url = f"https://www.youtube.com/watch?v={video_id}"

                        results.append(
                            RawCandidateItem(
                                title=title,
                                url=watch_url,
                                video_url=watch_url,
                                thumbnail_url=thumb_url,
                                platform="youtube",
                                description=desc,
                                creator=channel,
                                duration=None,
                                published_at=published_at,
                                metadata={"video_id": video_id, "channel_id": snippet.get("channelId")}
                            )
                        )

                    logger.info(f"YouTube search returned {len(results)} candidate items for '{clean_q}'")
                    return results

                else:
                    logger.warning(
                        f"YouTube Data API error {resp.status_code}: {resp.text}. Falling back to mock results."
                    )
                    return await self._mock_fallback.search(query, max_results)

        except Exception as exc:
            logger.error(f"YouTube search request error: {exc}. Falling back to mock results.")
            return await self._mock_fallback.search(query, max_results)
