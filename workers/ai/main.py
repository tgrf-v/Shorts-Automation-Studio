import os
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [AI-WORKER] - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ai_worker")


def run_worker() -> None:
    logger.info("Starting AI Worker environment...")
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    logger.info(f"Target Redis Queue: {redis_url}")
    logger.info("AI worker initialized and awaiting transcription/TTS tasks.")
    try:
        while True:
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("AI worker stopped by user.")


if __name__ == "__main__":
    run_worker()
