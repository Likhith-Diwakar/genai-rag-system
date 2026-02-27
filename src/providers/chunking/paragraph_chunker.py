from typing import List
from src.interfaces.base_chunker import BaseChunker
from src.utils.logger import logger


class ParagraphChunker(BaseChunker):

    def __init__(self, max_chars=1200, overlap_chars=200):
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk(self, text: str) -> List[str]:

        logger.info("Using paragraph-based chunking strategy")

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks = []
        current_chunk = ""

        for para in paragraphs:

            if len(para) > self.max_chars:
                start = 0
                while start < len(para):
                    end = start + self.max_chars
                    chunk = para[start:end].strip()
                    if chunk:
                        chunks.append(chunk)
                    start = end - self.overlap_chars if self.overlap_chars > 0 else end
                current_chunk = ""
                continue

            if len(current_chunk) + len(para) + 2 > self.max_chars:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())

                overlap_text = (
                    current_chunk[-self.overlap_chars:]
                    if self.overlap_chars > 0 and current_chunk
                    else ""
                )

                current_chunk = overlap_text + "\n\n" + para if overlap_text else para
            else:
                current_chunk = current_chunk + "\n\n" + para if current_chunk else para

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks