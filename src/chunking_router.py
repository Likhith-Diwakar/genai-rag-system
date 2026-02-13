# src/chunking_router.py

from src.chunker import chunk_text
from src.chunk_csv import chunk_csv_text
from src.logger import logger


def route_chunking(mime_type: str, text: str):
    """
    Selects chunking strategy based on file type.
    """

    logger.info(f"Selecting chunking strategy for {mime_type}")

    # CSV → row-based chunking
    if mime_type == "text/csv":
        return chunk_csv_text(text)

    # PDFs, Docs, DOCX → paragraph chunking
    return chunk_text(text)
