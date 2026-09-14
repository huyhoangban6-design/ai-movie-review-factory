"""Worker starter (Phase 1 scaffold).

Phase 8 sẽ gắn vào Redis queue (REDIS_URL) + retry/backoff/observability.
Hiện tại chỉ in log để minh hoạ vòng lặp worker.
"""
import logging
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("worker")


def main() -> None:
    logger.info("Worker started (Phase 1 scaffold). No queue wired yet; exiting after one tick.")
    time.sleep(0.5)


if __name__ == "__main__":
    main()