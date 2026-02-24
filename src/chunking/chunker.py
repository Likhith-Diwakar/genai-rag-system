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
    # PDF TABLE-AWARE STRATEGY
    # --------------------------------------------------------
    if mime_type == "application/pdf" and "--- TABLE" in text:
        logger.info("Using PDF table-aware chunking strategy")

        chunks = []

        sections = text.split("\n--- TABLE")
        normal_text = sections[0].strip()

        # First chunk normal paragraph text
        if normal_text:
            chunks.extend(_paragraph_chunk(normal_text, max_chars, overlap_chars))

        # Process each table separately
        for table_section in sections[1:]:
            table_section = "--- TABLE" + table_section
            lines = [l.strip() for l in table_section.split("\n") if l.strip()]

            if len(lines) < 2:
                continue

            header = lines[1]  # header row
            header_cols = [h.strip() for h in header.split("|")]

            for row in lines[2:]:
                row_cols = [c.strip() for c in row.split("|")]

                if len(row_cols) != len(header_cols):
                    continue

                structured_row = []
                for h, c in zip(header_cols, row_cols):
                    structured_row.append(f"{h}: {c}")

                chunks.append("\n".join(structured_row))

        logger.info(f"Created {len(chunks)} PDF table-aware chunks")
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