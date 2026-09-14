import os
import sys
import time
import asyncio
import logging
import subprocess

# Ensure app package is importable
sys.path.insert(0, "/app")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api")))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [VIDEO-WORKER] - %(levelname)s - %(message)s"
)
logger = logging.getLogger("video_worker")


def verify_ffmpeg() -> bool:
    """Verifies that ffmpeg and ffprobe binaries are available."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        subprocess.run(
            ["ffprobe", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        logger.info("FFmpeg and FFprobe verified successfully.")
        return True
    except Exception as exc:
        logger.error(f"FFmpeg verification failed: {exc}")
        return False


def run_worker() -> None:
    logger.info("Starting Video Processing Worker environment for Shorts Automation Studio...")
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    logger.info(f"Connected to Redis Queue: {redis_url}")

    ffmpeg_ready = verify_ffmpeg()
    if not ffmpeg_ready:
        logger.warning("FFmpeg binary not detected in PATH. Ensure container environment includes FFmpeg.")

    from app.services.analysis.queue import analysis_queue
    from app.services.analysis.media_analysis import reference_analysis_service
    from app.services.script.queue import script_queue
    from app.services.script.script_service import script_service

    logger.info(f"Worker actively listening on queues '{analysis_queue.queue_name}' and '{script_queue.queue_name}'...")

    while True:
        try:
            # 1. Check video analysis queue
            task = analysis_queue.dequeue(timeout=1)
            if task:
                job_id = task.get("job_id")
                project_id = task.get("project_id")
                logger.info(f"Received analysis task: job_id={job_id}, project_id={project_id}")

                try:
                    asyncio.run(reference_analysis_service.process_job(job_id))
                    logger.info(f"Successfully processed analysis job: {job_id}")
                except Exception as proc_exc:
                    logger.error(f"Error executing analysis job {job_id}: {proc_exc}", exc_info=True)
                continue

            # 2. Check script adaptation queue
            script_task = script_queue.dequeue(timeout=1)
            if script_task:
                s_job_id = script_task.get("job_id")
                s_proj_id = script_task.get("project_id")
                logger.info(f"Received script task: job_id={s_job_id}, project_id={s_proj_id}")

                try:
                    asyncio.run(script_service.process_job(s_job_id))
                    logger.info(f"Successfully processed script job: {s_job_id}")
                except Exception as s_exc:
                    logger.error(f"Error executing script job {s_job_id}: {s_exc}", exc_info=True)
                continue

            # Idle heartbeat
            time.sleep(0.5)

        except KeyboardInterrupt:
            logger.info("Video worker stopped by user.")
            break
        except Exception as exc:
            logger.error(f"Unexpected worker loop exception: {exc}", exc_info=True)
            time.sleep(3)


if __name__ == "__main__":
    run_worker()
