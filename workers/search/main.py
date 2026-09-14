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


async def main_search_worker_loop() -> None:
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
            task = await asyncio.to_thread(footage_queue.dequeue, 2)
            if task:
                search_id = task.get("search_id")
                scene_id = task.get("scene_id")
                project_id = task.get("project_id")
                logger.info(f"Search Worker received task: search_id={search_id}, scene_id={scene_id}, project_id={project_id}")

                try:
                    await footage_service.process_search_job(search_id)
                    logger.info(f"Search Worker completed search job: {search_id}")
                except Exception as proc_exc:
                    logger.error(f"Error processing footage search {search_id}: {proc_exc}", exc_info=True)
            else:
                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.info("Search worker task cancelled.")
            break
        except Exception as exc:
            logger.error(f"Unexpected search worker error: {exc}", exc_info=True)
            await asyncio.sleep(3)


def run_worker() -> None:
    asyncio.run(main_search_worker_loop())


if __name__ == "__main__":
    run_worker()
