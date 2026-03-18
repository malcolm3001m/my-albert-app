import logging
from logging.config import dictConfig


def configure_logging(level: str = "INFO") -> None:
    resolved_level = level.upper()

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "standard": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "standard",
                    "level": resolved_level,
                }
            },
            "root": {"handlers": ["default"], "level": resolved_level},
        }
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
