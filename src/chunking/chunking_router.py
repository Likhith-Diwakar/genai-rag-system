# src/chunking_router.py

from src.chunking.chunker import chunk_text
from src.utils.logger import logger


def route_chunking(mime_type: str, text: str):
    """
    CSV is NOT chunked anymore.
    Only text documents are embedded.
    """

    logger.info(f"Selecting chunking strategy for {mime_type}")
    return chunk_text(text)
