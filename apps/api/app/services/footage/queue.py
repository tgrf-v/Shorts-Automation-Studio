import json
import logging
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger("shorts_api.services.footage.queue")


class FootageQueue:
    """Redis-backed queue for asynchronous footage search and visual analysis jobs."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self.queue_name = getattr(settings, "FOOTAGE_SEARCH_QUEUE_NAME", "shorts:queue:footage_search")
        self._client = None

    def _get_client(self):
        if self._client is None:
            import redis
            self._client = redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    def enqueue(self, search_id: str, scene_id: str, project_id: str) -> bool:
        """Pushes a footage search task payload to Redis."""
        payload = {
            "search_id": str(search_id),
            "scene_id": str(scene_id),
            "project_id": str(project_id)
        }
        try:
            client = self._get_client()
            client.rpush(self.queue_name, json.dumps(payload))
            logger.info(f"Enqueued footage search task {search_id} on {self.queue_name}")
            return True
        except Exception as exc:
            logger.error(f"Failed to enqueue task to Redis ({self.queue_name}): {exc}")
            raise RuntimeError(f"Could not submit footage search task to queue: {exc}") from exc

    def dequeue(self, timeout: int = 3) -> Optional[Dict[str, Any]]:
        """Blocks for timeout seconds waiting for next footage search task from Redis queue."""
        try:
            client = self._get_client()
            result = client.blpop(self.queue_name, timeout=timeout)
            if result:
                _, data = result
                return json.loads(data)
            return None
        except Exception as exc:
            logger.warning(f"Error while dequeuing from Redis ({self.queue_name}): {exc}")
            return None


footage_queue = FootageQueue()
