from src.interfaces.base_parser import BaseParser
from src.parsers.extract_pdf import extract_pdf_text


class PDFParser(BaseParser):

    def parse(self, file_path: str) -> str:
        return extract_pdf_text(file_path)