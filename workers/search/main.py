import os
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [SEARCH-WORKER] - %(levelname)s - %(message)s"
)
logger = logging.getLogger("search_worker")


def run_worker() -> None:
    logger.info("Starting Visual Search Worker environment...")
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    qdrant_url = os.getenv("QDRANT_URL", "http://qdrant:6333")
    logger.info(f"Target Redis Queue: {redis_url}")
    logger.info(f"Target Qdrant Instance: {qdrant_url}")
    logger.info("Search worker initialized and awaiting visual search tasks.")
    try:
        while True:
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Search worker stopped by user.")


if __name__ == "__main__":
    run_worker()
