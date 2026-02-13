import fitz  # PyMuPDF
from src.logger import logger


def extract_pdf_text(path: str) -> str:
    logger.info(f"Extracting text from PDF: {path}")
    doc = fitz.open(path)

    pages = []
    for page in doc:
        text = page.get_text("text")
        if text.strip():
            pages.append(text)

    return "\n\n".join(pages)
