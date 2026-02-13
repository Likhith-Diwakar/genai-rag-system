from loguru import logger
import sys

logger.remove()

logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan> | {message}",
)

__all__ = ["logger"]