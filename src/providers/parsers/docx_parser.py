from src.interfaces.base_parser import BaseParser
from src.parsers.extract_docx import extract_docx_text


class DOCXParser(BaseParser):

    def parse(self, file_path: str) -> str:
        return extract_docx_text(file_path)