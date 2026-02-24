# src/chunker.py

from typing import List
from src.utils.logger import logger


def chunk_text(
    text: str,
    mime_type: str = None,
    max_chars: int = 1200,
    overlap_chars: int = 200
) -> List[str]:

    if not text or not text.strip():
        logger.warning("Empty text received for chunking")
        return []

    text = text.replace("\r\n", "\n").strip()

    # --------------------------------------------------------
    # CSV STRATEGY (ROW-BASED)
    # --------------------------------------------------------
    if mime_type == "text/csv":
        logger.info("Using CSV row-based chunking strategy")

        sections = text.split("\n\n")
        if not sections:
            return []

        schema = sections[0]
        rows = sections[1:]

        max_rows_per_chunk = 10
        chunks = []

        for i in range(0, len(rows), max_rows_per_chunk):
            chunk_rows = rows[i:i + max_rows_per_chunk]
            chunk = schema + "\n\n" + "\n\n".join(chunk_rows)
            chunks.append(chunk)

        logger.info(f"Created {len(chunks)} CSV chunks")
        return chunks

    # --------------------------------------------------------
    # PDF SMART TABLE GROUPING (Balanced)
    # --------------------------------------------------------
    if mime_type == "application/pdf":
        logger.info("Using balanced PDF chunking strategy")

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []

        for para in paragraphs:

            lines = para.split("\n")

            numeric_line_count = 0
            for line in lines:
                numeric_tokens = [
                    token for token in line.split()
                    if token.replace(".", "", 1).isdigit()
                ]
                if len(numeric_tokens) >= 3:
                    numeric_line_count += 1

            # If paragraph looks like a table block → keep entire block
            if numeric_line_count >= 2:
                chunks.append(para)
                continue

            # Otherwise use paragraph chunking logic
            if len(para) > max_chars:
                start = 0
                while start < len(para):
                    end = start + max_chars
                    chunk = para[start:end].strip()
                    if chunk:
                        chunks.append(chunk)
                    start = end - overlap_chars if overlap_chars > 0 else end
            else:
                chunks.append(para)

        logger.info(f"Created {len(chunks)} PDF chunks (balanced)")
        return chunks

    # --------------------------------------------------------
    # DEFAULT PARAGRAPH STRATEGY
    # --------------------------------------------------------

    logger.info("Using paragraph-based chunking strategy")
    return _paragraph_chunk(text, max_chars, overlap_chars)


def _paragraph_chunk(text: str, max_chars: int, overlap_chars: int) -> List[str]:

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = ""

    for para in paragraphs:

        if len(para) > max_chars:
            start = 0
            while start < len(para):
                end = start + max_chars
                chunk = para[start:end].strip()
                if chunk:
                    chunks.append(chunk)
                start = end - overlap_chars if overlap_chars > 0 else end
            current_chunk = ""
            continue

        if len(current_chunk) + len(para) + 2 > max_chars:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())

            overlap_text = (
                current_chunk[-overlap_chars:]
                if overlap_chars > 0 and current_chunk
                else ""
            )

            current_chunk = overlap_text + "\n\n" + para if overlap_text else para

        else:
            current_chunk = current_chunk + "\n\n" + para if current_chunk else para

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks