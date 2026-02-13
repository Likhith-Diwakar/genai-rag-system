from src.chunker import chunk_text
from src.logger import logger


def chunk_by_file_type(text: str, mime_type: str):
    """
    Route chunking strategy based on file type.
    """

    logger.info(f"Selecting chunking strategy for {mime_type}")

    # Docs, DOCX, PDF → paragraph-based
    return chunk_text(text)
