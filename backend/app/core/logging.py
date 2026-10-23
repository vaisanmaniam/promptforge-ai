import logging
import sys
from typing import Any, Dict
from app.core.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """Configure structured console logging for the application."""
    log_format = (
        "%(asctime)s [%(levelname)s] [%(name)s] "
        "[%(filename)s:%(lineno)d] - %(message)s"
    )

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Silence overly verbose external loggers if in DEBUG
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


logger = logging.getLogger("promptforge")
