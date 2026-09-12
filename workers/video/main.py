import os
import sys
import time
import logging
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [VIDEO-WORKER] - %(levelname)s - %(message)s"
)
logger = logging.getLogger("video_worker")


def verify_ffmpeg() -> bool:
    """Verifies that ffmpeg and ffprobe binaries are available."""
    try:
        ffmpeg_res = subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        ffprobe_res = subprocess.run(
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
    logger.info("Starting Video Processing Worker environment...")
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    logger.info(f"Target Redis Queue: {redis_url}")

    ffmpeg_ready = verify_ffmpeg()
    if not ffmpeg_ready:
        logger.warning("FFmpeg binary not detected in PATH. Ensure container environment includes FFmpeg.")

    logger.info("Video worker initialized and awaiting tasks.")
    # Skeleton heartbeat loop
    try:
        while True:
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Video worker stopped by user.")


if __name__ == "__main__":
    run_worker()
