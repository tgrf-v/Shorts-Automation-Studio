import os
import sys
import time
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [SEARCH-WORKER] - %(levelname)s - %(message)s"
)
logger = logging.getLogger("search_worker")

# Ensure app package is importable
sys.path.insert(0, "/app")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api")))


def run_worker() -> None:
    logger.info("Starting Visual Search Worker environment...")
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
    logger.info(f"Target Redis Queue: {redis_url}")
    logger.info(f"Target Qdrant Instance: {qdrant_url}")

    from app.services.footage.queue import footage_queue
    from app.services.footage.footage_service import footage_service

    logger.info(f"Search worker listening on queue '{footage_queue.queue_name}'...")

    while True:
        try:
            task = footage_queue.dequeue(timeout=2)
            if task:
                search_id = task.get("search_id")
                scene_id = task.get("scene_id")
                project_id = task.get("project_id")
                logger.info(f"Search Worker received task: search_id={search_id}, scene_id={scene_id}, project_id={project_id}")

                try:
                    asyncio.run(footage_service.process_search_job(search_id))
                    logger.info(f"Search Worker completed search job: {search_id}")
                except Exception as proc_exc:
                    logger.error(f"Error processing footage search {search_id}: {proc_exc}", exc_info=True)
            else:
                time.sleep(0.5)

        except KeyboardInterrupt:
            logger.info("Search worker stopped by user.")
            break
        except Exception as exc:
            logger.error(f"Unexpected search worker error: {exc}", exc_info=True)
            time.sleep(3)


if __name__ == "__main__":
    run_worker()
