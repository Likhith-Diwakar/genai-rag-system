from typing import List
from src.utils.logger import logger
import re


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
    # STRUCTURALLY SAFE PDF STRATEGY (FIXED)
    # --------------------------------------------------------
    if mime_type == "application/pdf":
        logger.info("Using structurally safe PDF chunking strategy")

        chunks = []

        # 1️⃣ Extract TABLE_ROW blocks using actual markers
        table_pattern = re.compile(
            r"TABLE_ID\s*=\s*.*?\nTABLE_ROW_START.*?TABLE_ROW_END",
            re.DOTALL
        )

        table_blocks = table_pattern.findall(text)

        # Add each table row as atomic chunk
        for block in table_blocks:
            cleaned = block.strip()
            if cleaned:
                chunks.append(cleaned)

        # 2️⃣ Remove table blocks from main text
        text_without_tables = table_pattern.sub("", text)

        # 3️⃣ Chunk remaining narrative text normally
        paragraphs = [
            p.strip()
            for p in text_without_tables.split("\n\n")
            if p.strip()
        ]

        for para in paragraphs:

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

        logger.info(f"Created {len(chunks)} PDF chunks (structurally safe)")
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