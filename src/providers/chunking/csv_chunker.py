from typing import List
from src.interfaces.base_chunker import BaseChunker
from src.utils.logger import logger


class CSVChunker(BaseChunker):

    def chunk(self, text: str) -> List[str]:

        logger.info("Using CSV row-based chunking strategy")

        if not text.strip():
            return []

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