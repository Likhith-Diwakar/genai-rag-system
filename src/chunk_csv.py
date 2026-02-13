# src/chunk_csv.py

from src.logger import logger


def chunk_csv_text(text: str, max_rows_per_chunk: int = 10):
    """
    Splits structured CSV text into row-based chunks.

    Each chunk contains:
    - Schema header
    - N rows
    """

    logger.info("Chunking CSV using row-based strategy")

    if not text.strip():
        return []

    sections = text.split("\n\n")

    if not sections:
        return []

    schema = sections[0]
    rows = sections[1:]

    chunks = []
    for i in range(0, len(rows), max_rows_per_chunk):
        chunk_rows = rows[i:i + max_rows_per_chunk]
        chunk = schema + "\n\n" + "\n\n".join(chunk_rows)
        chunks.append(chunk)

    logger.info(f"Created {len(chunks)} CSV chunks")

    return chunks
