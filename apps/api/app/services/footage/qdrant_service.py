import logging
from typing import List, Dict, Any, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger("shorts_api.footage.qdrant")


class QdrantFootageService:
    """
    Qdrant vector database integration for indexing and comparing scene visual embeddings.
    Communicates directly via Qdrant HTTP REST endpoints with defensive local fallback.
    """

    def __init__(self, qdrant_url: Optional[str] = None):
        self.qdrant_url = (qdrant_url or settings.QDRANT_URL or "http://qdrant:6333").rstrip("/")
        self.collection_name = getattr(settings, "QDRANT_COLLECTION_FOOTAGE", "scene_visual_embeddings")
        self._collection_initialized = False

    async def ensure_collection(self, vector_size: int = 64) -> bool:
        """Ensures the visual embeddings collection exists in Qdrant."""
        if self._collection_initialized:
            return True

        url = f"{self.qdrant_url}/collections/{self.collection_name}"
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    self._collection_initialized = True
                    return True

                # Create collection if 404
                payload = {
                    "vectors": {
                        "size": vector_size,
                        "distance": "Cosine"
                    }
                }
                put_resp = await client.put(url, json=payload)
                if put_resp.status_code in (200, 201):
                    logger.info(f"Created Qdrant collection '{self.collection_name}' (dim={vector_size})")
                    self._collection_initialized = True
                    return True
                else:
                    logger.warning(f"Could not create Qdrant collection: {put_resp.text}")
                    return False
        except Exception as exc:
            logger.warning(f"Qdrant connection unavailable ({exc}). Using in-memory vector comparison fallback.")
            return False

    async def search_similar(
        self,
        query_vector: List[float],
        filter_scene_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Queries Qdrant for closest vectors using cosine similarity."""
        ready = await self.ensure_collection(vector_size=len(query_vector))
        if not ready:
            return []

        url = f"{self.qdrant_url}/collections/{self.collection_name}/points/search"
        payload: Dict[str, Any] = {
            "vector": query_vector,
            "limit": limit,
            "with_payload": True
        }

        if filter_scene_id:
            payload["filter"] = {
                "must": [
                    {"key": "scene_id", "match": {"value": filter_scene_id}}
                ]
            }

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("result", [])
                return []
        except Exception as exc:
            logger.warning(f"Qdrant search error ({exc}), continuing with local scoring.")
            return []


qdrant_service = QdrantFootageService()
