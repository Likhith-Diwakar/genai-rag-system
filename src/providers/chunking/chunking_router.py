from src.providers.chunking.csv_chunker import CSVChunker
from src.providers.chunking.pdf_chunker import PDFChunker
from src.providers.chunking.paragraph_chunker import ParagraphChunker


class ChunkingRouter:

    def __init__(self):
        self.csv_chunker = CSVChunker()
        self.pdf_chunker = PDFChunker()
        self.default_chunker = ParagraphChunker()

    def route(self, mime_type: str):

        if mime_type == "text/csv":
            return self.csv_chunker

        if mime_type == "application/pdf":
            return self.pdf_chunker

        return self.default_chunker