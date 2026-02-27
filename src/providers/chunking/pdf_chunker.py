import re
from typing import List
from src.interfaces.base_chunker import BaseChunker
from src.utils.logger import logger


class PDFChunker(BaseChunker):

    def __init__(self, max_chars=1200, overlap_chars=200):
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk(self, text: str) -> List[str]:

        logger.info("Using structurally safe PDF chunking strategy")

        chunks = []

        table_pattern = re.compile(
            r"TABLE_ID\s*=\s*.*?\nTABLE_ROW_START.*?TABLE_ROW_END",
            re.DOTALL
        )

        table_blocks = table_pattern.findall(text)

        for block in table_blocks:
            cleaned = block.strip()
            if cleaned:
                chunks.append(cleaned)

        text_without_tables = table_pattern.sub("", text)

        paragraphs = [
            p.strip()
            for p in text_without_tables.split("\n\n")
            if p.strip()
        ]

        for para in paragraphs:

            if len(para) > self.max_chars:
                start = 0
                while start < len(para):
                    end = start + self.max_chars
                    chunk = para[start:end].strip()
                    if chunk:
                        chunks.append(chunk)
                    start = end - self.overlap_chars if self.overlap_chars > 0 else end
            else:
                chunks.append(para)

        logger.info(f"Created {len(chunks)} PDF chunks")

        return chunks