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
    from app.services.tts.queue import tts_queue
    from app.services.tts.tts_service import tts_service
    from app.services.footage.queue import footage_queue
    from app.services.footage.footage_service import footage_service

    logger.info(f"AI worker listening on queues '{script_queue.queue_name}', '{tts_queue.queue_name}', and '{footage_queue.queue_name}'...")

    while True:
        try:
            # 1. Check script adaptation queue
            task = script_queue.dequeue(timeout=1)
            if task:
                job_id = task.get("job_id")
                project_id = task.get("project_id")
                logger.info(f"AI Worker received script task: job_id={job_id}, project_id={project_id}")
                try:
                    asyncio.run(script_service.process_job(job_id))
                    logger.info(f"AI Worker completed script job: {job_id}")
                except Exception as exc:
                    logger.error(f"Error in script job {job_id}: {exc}", exc_info=True)
                continue

            # 2. Check TTS generation queue
            tts_task = tts_queue.dequeue(timeout=1)
            if tts_task:
                t_job_id = tts_task.get("job_id")
                t_proj_id = tts_task.get("project_id")
                logger.info(f"AI Worker received TTS task: job_id={t_job_id}, project_id={t_proj_id}")
                try:
                    asyncio.run(tts_service.process_job(t_job_id))
                    logger.info(f"AI Worker completed TTS job: {t_job_id}")
                except Exception as t_exc:
                    logger.error(f"Error in TTS job {t_job_id}: {t_exc}", exc_info=True)
                continue

            # 3. Check visual footage search queue
            f_task = footage_queue.dequeue(timeout=1)
            if f_task:
                f_search_id = f_task.get("search_id")
                f_proj_id = f_task.get("project_id")
                logger.info(f"AI Worker received footage search task: search_id={f_search_id}, project_id={f_proj_id}")
                try:
                    asyncio.run(footage_service.process_search_job(f_search_id))
                    logger.info(f"AI Worker completed footage search: {f_search_id}")
                except Exception as f_exc:
                    logger.error(f"Error in footage search {f_search_id}: {f_exc}", exc_info=True)
                continue

            time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info("AI worker stopped by user.")
            break
        except Exception as exc:
            logger.error(f"Unexpected AI worker error: {exc}", exc_info=True)
            time.sleep(3)


if __name__ == "__main__":
    run_worker()
