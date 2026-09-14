import os
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [AI-WORKER] - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ai_worker")


import sys
import asyncio

# Ensure app package is importable
sys.path.insert(0, "/app")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api")))

def run_worker() -> None:
    logger.info("Starting AI Worker environment...")
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    logger.info(f"Target Redis Queue: {redis_url}")

    from app.services.script.queue import script_queue
    from app.services.script.script_service import script_service

    logger.info(f"AI worker listening on queue '{script_queue.queue_name}'...")

    while True:
        try:
            task = script_queue.dequeue(timeout=3)
            if task:
                job_id = task.get("job_id")
                project_id = task.get("project_id")
                logger.info(f"AI Worker received script task: job_id={job_id}, project_id={project_id}")
                try:
                    asyncio.run(script_service.process_job(job_id))
                    logger.info(f"AI Worker completed script job: {job_id}")
                except Exception as exc:
                    logger.error(f"Error in script job {job_id}: {exc}", exc_info=True)
            else:
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("AI worker stopped by user.")
            break
        except Exception as exc:
            logger.error(f"Unexpected AI worker error: {exc}", exc_info=True)
            time.sleep(3)


if __name__ == "__main__":
    run_worker()
