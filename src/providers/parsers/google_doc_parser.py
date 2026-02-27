from src.interfaces.base_parser import BaseParser
from src.parsers.extract_text import extract_doc_text


class GoogleDocParser(BaseParser):

    def parse(self, doc_id: str) -> str:
        return extract_doc_text(doc_id)