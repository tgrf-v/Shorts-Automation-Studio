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


async def main_worker_loop() -> None:
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
    from app.services.tts.queue import tts_queue
    from app.services.tts.tts_service import tts_service
    from app.services.footage.queue import footage_queue
    from app.services.footage.footage_service import footage_service

    logger.info(f"Worker actively listening on queues '{analysis_queue.queue_name}', '{script_queue.queue_name}', '{tts_queue.queue_name}', and '{footage_queue.queue_name}'...")

    while True:
        try:
            # 1. Check video analysis queue
            task = await asyncio.to_thread(analysis_queue.dequeue, 1)
            if task:
                job_id = task.get("job_id")
                project_id = task.get("project_id")
                logger.info(f"Received analysis task: job_id={job_id}, project_id={project_id}")

                try:
                    await reference_analysis_service.process_job(job_id)
                    logger.info(f"Successfully processed analysis job: {job_id}")
                except Exception as proc_exc:
                    logger.error(f"Error executing analysis job {job_id}: {proc_exc}", exc_info=True)
                continue

            # 2. Check script adaptation queue
            script_task = await asyncio.to_thread(script_queue.dequeue, 1)
            if script_task:
                s_job_id = script_task.get("job_id")
                s_proj_id = script_task.get("project_id")
                logger.info(f"Received script task: job_id={s_job_id}, project_id={s_proj_id}")

                try:
                    await script_service.process_job(s_job_id)
                    logger.info(f"Successfully processed script job: {s_job_id}")
                except Exception as s_exc:
                    logger.error(f"Error executing script job {s_job_id}: {s_exc}", exc_info=True)
                continue

            # 3. Check TTS generation queue
            tts_task = await asyncio.to_thread(tts_queue.dequeue, 1)
            if tts_task:
                t_job_id = tts_task.get("job_id")
                t_proj_id = tts_task.get("project_id")
                logger.info(f"Received TTS task: job_id={t_job_id}, project_id={t_proj_id}")

                try:
                    await tts_service.process_job(t_job_id)
                    logger.info(f"Successfully processed TTS job: {t_job_id}")
                except Exception as t_exc:
                    logger.error(f"Error executing TTS job {t_job_id}: {t_exc}", exc_info=True)
                continue

            # 4. Check visual footage search queue
            f_task = await asyncio.to_thread(footage_queue.dequeue, 1)
            if f_task:
                f_search_id = f_task.get("search_id")
                f_proj_id = f_task.get("project_id")
                logger.info(f"Received footage search task: search_id={f_search_id}, project_id={f_proj_id}")

                try:
                    await footage_service.process_search_job(f_search_id)
                    logger.info(f"Successfully processed footage search job: {f_search_id}")
                except Exception as f_exc:
                    logger.error(f"Error executing footage search {f_search_id}: {f_exc}", exc_info=True)
                continue

            # Idle heartbeat
            await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.info("Video worker task cancelled.")
            break
        except Exception as exc:
            logger.error(f"Unexpected worker loop exception: {exc}", exc_info=True)
            await asyncio.sleep(3)


def run_worker() -> None:
    asyncio.run(main_worker_loop())


if __name__ == "__main__":
    run_worker()
