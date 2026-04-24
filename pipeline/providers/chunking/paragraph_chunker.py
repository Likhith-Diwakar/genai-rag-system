from typing import List
import re
from pipeline.interfaces.base_chunker import BaseChunker
from pipeline.utils.logger import logger


class ParagraphChunker(BaseChunker):

    def __init__(self, max_chars=1200, overlap_chars=200):
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk(self, text: str) -> List[str]:

        logger.info("Using paragraph-based chunking strategy")

        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        chunks = []
        current_chunk = ""

        current_page_marker = ""

        for para in paragraphs:

            # -------------------------------------------
            # Detect page marker
            # -------------------------------------------
            page_match = re.match(r"===== PAGE (\d+) =====", para)

            if page_match:
                current_page_marker = para
                continue

            # -------------------------------------------
            # Attach page marker to first chunk of page
            # -------------------------------------------
            if not current_chunk and current_page_marker:
                current_chunk = current_page_marker + "\n\n"
                current_page_marker = ""

            # -------------------------------------------
            # Handle very large paragraph
            # -------------------------------------------
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

            # -------------------------------------------
            # Normal chunk building
            # -------------------------------------------
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

        # -------------------------------------------
        # Final chunk
        # -------------------------------------------
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks
