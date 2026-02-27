import os

from src.providers.parsers.pdf_parser import PDFParser
from src.providers.parsers.docx_parser import DOCXParser
from src.providers.parsers.csv_parser import CSVParser
from src.providers.parsers.google_doc_parser import GoogleDocParser


class ParserRouter:

    def __init__(self):
        self.pdf_parser = PDFParser()
        self.docx_parser = DOCXParser()
        self.csv_parser = CSVParser()
        self.gdoc_parser = GoogleDocParser()

    def route(self, file_name: str):

        ext = os.path.splitext(file_name.lower())[1]

        if ext == ".pdf":
            return self.pdf_parser

        if ext == ".docx":
            return self.docx_parser

        if ext == ".csv":
            return self.csv_parser

        # If no extension but Google Doc ID format used
        return self.gdoc_parser