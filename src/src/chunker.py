
# src/chunker.py
from typing import List
from src.logger import logger


def chunk_text(
    text: str,
    max_chars: int = 1200,
    overlap_chars: int = 200
) -> List[str]:

    if not text or not text.strip():
        logger.warning("Empty text received for chunking")
        return []

    text = text.replace("\r\n", "\n").strip()
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    logger.info(f"Chunking text | paragraphs={len(paragraphs)}")

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(para) > max_chars:
            logger.debug("Large paragraph detected, hard-splitting")
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

    logger.info(f"Created {len(chunks)} chunks")
    return chunks
