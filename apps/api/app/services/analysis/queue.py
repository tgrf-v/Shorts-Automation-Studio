import json
import logging
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger("shorts_api.services.queue")


class AnalysisQueue:
    """Redis-backed queue abstraction for asynchronous video analysis jobs."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self.queue_name = settings.ANALYSIS_QUEUE_NAME
        self._client = None

    def _get_client(self):
        if self._client is None:
            import redis
            self._client = redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    def enqueue(self, job_id: str, project_id: str, reanalyze: bool = False) -> bool:
        """Pushes an analysis task payload to the Redis queue."""
        payload = {
            "job_id": str(job_id),
            "project_id": str(project_id),
            "reanalyze": reanalyze
        }
        try:
            client = self._get_client()
            client.rpush(self.queue_name, json.dumps(payload))
            logger.info(f"Enqueued analysis task for job {job_id} on {self.queue_name}")
            return True
        except Exception as exc:
            logger.error(f"Failed to enqueue task to Redis ({self.queue_name}): {exc}")
            raise RuntimeError(f"Could not submit analysis task to queue: {exc}") from exc

    def dequeue(self, timeout: int = 5) -> Optional[Dict[str, Any]]:
        """Blocks for timeout seconds waiting for next task from Redis queue."""
        try:
            client = self._get_client()
            result = client.blpop(self.queue_name, timeout=timeout)
            if result:
                _, data = result
                return json.loads(data)
            return None
        except Exception as exc:
            logger.warning(f"Error while dequeuing from Redis: {exc}")
            return None


analysis_queue = AnalysisQueue()
