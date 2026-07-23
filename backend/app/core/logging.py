"""
Logging configuration using Loguru.

Replaces the default uvicorn/stdlib logging handlers so every log line
(startup, model loading, requests, errors) shares one consistent format
and is routed to both console and a rotating file sink.
"""

import logging
import sys
from pathlib import Path

from loguru import logger

from app.core.config import get_settings


class InterceptHandler(logging.Handler):
    """Redirects standard `logging` records (e.g. from uvicorn) into Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_back and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def configure_logging() -> None:
    """Set up Loguru sinks and intercept stdlib logging (used by uvicorn)."""
    settings = get_settings()
    log_dir: Path = settings.log_dir_resolved

    logger.remove()  # drop default handler to avoid duplicate logs

    logger.add(
        sys.stdout,
        level=settings.LOG_LEVEL,
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    logger.add(
        log_dir / "app.log",
        level=settings.LOG_LEVEL,
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        enqueue=True,  # thread-safe / process-safe writes
        backtrace=False,
        diagnose=False,
    )

    # Route uvicorn/fastapi/stdlib logging through Loguru.
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for noisy_logger in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        logging.getLogger(noisy_logger).handlers = [InterceptHandler()]
        logging.getLogger(noisy_logger).propagate = False

    logger.info("Logging configured | level={} | log_dir={}", settings.LOG_LEVEL, log_dir)
