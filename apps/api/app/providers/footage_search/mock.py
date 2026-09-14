import hashlib
import logging
from typing import List
from app.providers.footage_search.base import FootageSearchProvider, RawCandidateItem

logger = logging.getLogger("shorts_api.footage_search.mock")


class MockFootageSearchProvider(FootageSearchProvider):
    """
    Deterministic Mock search provider for development, CI, and testing.
    Generates realistic video candidates with diverse platforms, titles, and thumbnails
    without requiring external network requests or search engine quotas.
    """

    SAMPLE_TEMPLATES = [
        {
            "title_suffix": "Massive Machinery in Action (4K Documentary)",
            "platform": "youtube",
            "domain": "https://www.youtube.com/watch?v=mock_",
            "creator": "MegaMachines HD",
            "duration": 45.0,
            "thumb": "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=640&q=80"
        },
        {
            "title_suffix": "Close Up Heavy Equipment Operation",
            "platform": "pexels",
            "domain": "https://www.pexels.com/video/mock-",
            "creator": "Construction Stock",
            "duration": 28.5,
            "thumb": "https://images.unsplash.com/photo-1541888946425-d0fbb186c5f7?w=640&q=80"
        },
        {
            "title_suffix": "Engineering Marvel - Lifting Giant Structure",
            "platform": "youtube",
            "domain": "https://www.youtube.com/watch?v=eng_",
            "creator": "Modern Engineering",
            "duration": 58.0,
            "thumb": "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=640&q=80"
        },
        {
            "title_suffix": "High Angle View of Site Construction",
            "platform": "web",
            "domain": "https://archive.org/details/mock_",
            "creator": "Public Footage Lab",
            "duration": 34.0,
            "thumb": "https://images.unsplash.com/photo-1581094794329-c8112a89af12?w=640&q=80"
        },
        {
            "title_suffix": "Shorts Viral Clip - You Won't Believe This Scale",
            "platform": "youtube",
            "domain": "https://www.youtube.com/shorts/mock_",
            "creator": "TechFacts Shorts",
            "duration": 18.0,
            "thumb": "https://images.unsplash.com/photo-1517524008697-84bbe3c3fd98?w=640&q=80"
        },
    ]

    async def search(self, query: str, max_results: int = 10) -> List[RawCandidateItem]:
        logger.info(f"MockFootageSearchProvider executing query: '{query}' (limit={max_results})")
        clean_q = query.strip()
        candidates: List[RawCandidateItem] = []

        # Generate deterministic results based on hash of query
        q_hash = int(hashlib.md5(clean_q.encode("utf-8")).hexdigest()[:8], 16)

        count = min(max(max_results, 3), len(self.SAMPLE_TEMPLATES))
        for i in range(count):
            tpl = self.SAMPLE_TEMPLATES[i]
            seed_id = (q_hash + i * 101) % 999999

            title = f"{clean_q.capitalize()} - {tpl['title_suffix']}"
            url = f"{tpl['domain']}{seed_id}"
            thumb = tpl["thumb"]

            candidates.append(
                RawCandidateItem(
                    title=title,
                    url=url,
                    video_url=url,
                    thumbnail_url=thumb,
                    platform=tpl["platform"],
                    description=f"High definition visual footage of {clean_q}. Captured in cinematic 4K resolution.",
                    creator=tpl["creator"],
                    duration=tpl["duration"],
                    published_at="2025-06-15",
                    metadata={"mock_seed": seed_id, "query": clean_q}
                )
            )

        return candidates
