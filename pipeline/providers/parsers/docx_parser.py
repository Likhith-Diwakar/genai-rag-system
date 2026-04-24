from pipeline.interfaces.base_parser import BaseParser
from pipeline.parsers.extract_docx import extract_docx_text


class DOCXParser(BaseParser):

    def parse(self, file_path: str) -> str:
        return extract_docx_text(file_path)
