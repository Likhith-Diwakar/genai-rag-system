from src.interfaces.base_parser import BaseParser
from src.parsers.extract_csv import extract_csv_text


class CSVParser(BaseParser):

    def parse(self, file_id: str, file_name: str):
        return extract_csv_text(file_id, file_name)