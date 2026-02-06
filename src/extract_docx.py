# src/extract_docx.py

from docx import Document
from src.logger import logger


def extract_docx_text(file_path: str) -> str:
    logger.info(f"Extracting text from DOCX: {file_path}")

    doc = Document(file_path)
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]

    text = "\n\n".join(paragraphs)

    logger.info(f"Extracted {len(paragraphs)} paragraphs from DOCX")
    return text
