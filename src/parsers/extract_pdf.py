import os
import pdfplumber
from PIL import Image
from src.utils.logger import logger


IMAGE_OUTPUT_DIR = "data/tmp/pdf_images"


def _ensure_image_dir():
    os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)


def _format_table(table):
    """
    Convert table (list of rows) into pipe-separated string
    """
    lines = []
    for row in table:
        cleaned = [
            str(cell).strip() if cell is not None else ""
            for cell in row
        ]
        lines.append(" | ".join(cleaned))
    return "\n".join(lines)


def extract_pdf_text(path: str) -> str:
    logger.info(f"Extracting text + tables + images from PDF: {path}")

    _ensure_image_dir()

    combined_output = []

    with pdfplumber.open(path) as pdf:

        for page_number, page in enumerate(pdf.pages, start=1):

            combined_output.append(f"\n\n===== PAGE {page_number} =====\n")

            # -------------------
            # 1️⃣ TEXT
            # -------------------
            text = page.extract_text()
            if text:
                combined_output.append(text)

            # -------------------
            # 2️⃣ TABLES
            # -------------------
            tables = page.extract_tables()
            if tables:
                for idx, table in enumerate(tables, start=1):
                    combined_output.append(f"\n--- TABLE {idx} ---\n")
                    formatted = _format_table(table)
                    combined_output.append(formatted)

            # -------------------
            # 3️⃣ IMAGES
            # -------------------
            for img_index, img in enumerate(page.images, start=1):

                try:
                    x0, top, x1, bottom = (
                        img["x0"],
                        img["top"],
                        img["x1"],
                        img["bottom"],
                    )

                    cropped = page.crop((x0, top, x1, bottom)).to_image(resolution=150)

                    image_filename = (
                        f"page_{page_number}_img_{img_index}.png"
                    )

                    image_path = os.path.join(
                        IMAGE_OUTPUT_DIR,
                        image_filename,
                    )

                    cropped.save(image_path)

                    combined_output.append(
                        f"\n[IMAGE SAVED: {image_path}]"
                    )

                except Exception as e:
                    logger.warning(f"Image extraction failed on page {page_number}")

    return "\n".join(combined_output)
