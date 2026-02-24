import os
import pdfplumber
import hashlib
import pytesseract
import pandas as pd
from pdf2image import convert_from_path
from PIL import Image
from src.utils.logger import logger


# ================= CONFIG ================= #

IMAGE_OUTPUT_DIR = "data/tmp/pdf_images"

MIN_IMAGE_WIDTH = 80
MIN_IMAGE_HEIGHT = 80
DIGITAL_TEXT_THRESHOLD = 50

# ⚠️ SET THIS TO YOUR TESSERACT INSTALL PATH
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ================= HELPERS ================= #

def _ensure_image_dir():
    os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)


def _format_table(table):
    """
    Convert extracted table (list of lists) into:
    1) Markdown table (LLM friendly)
    2) Row-level semantic lines (header: value pairs)
    """
    if not table or len(table) < 2:
        return ""

    try:
        # First row as header
        header = [str(cell).strip() if cell else "" for cell in table[0]]
        rows = [
            [str(cell).strip() if cell else "" for cell in row]
            for row in table[1:]
        ]

        df = pd.DataFrame(rows, columns=header)

        output_blocks = []

        # 1️⃣ Markdown table (preserves structure)
        markdown_table = df.to_markdown(index=False)
        output_blocks.append(markdown_table)

        # 2️⃣ Row-level semantic serialization
        for _, row in df.iterrows():
            parts = []
            for col in df.columns:
                value = row[col]
                if value:
                    parts.append(f"{col}: {value}")
            if parts:
                output_blocks.append(", ".join(parts))

        return "\n".join(output_blocks)

    except Exception:
        # Safe fallback (original behavior)
        lines = []
        for row in table:
            cleaned = [
                str(cell).strip() if cell is not None else ""
                for cell in row
            ]
            lines.append(" | ".join(cleaned))
        return "\n".join(lines)


def _is_valid_bbox(x0, top, x1, bottom):
    if x1 <= x0 or bottom <= top:
        return False
    if (x1 - x0) < MIN_IMAGE_WIDTH:
        return False
    if (bottom - top) < MIN_IMAGE_HEIGHT:
        return False
    return True


def _run_ocr_on_pil(pil_image: Image.Image) -> str:
    try:
        text = pytesseract.image_to_string(pil_image)
        return text.strip()
    except Exception:
        return ""


def _extract_tables_with_fallback(page):
    output_blocks = []
    found_tables = page.find_tables()

    for idx, table in enumerate(found_tables, start=1):
        extracted = table.extract()
        if extracted:
            formatted = _format_table(extracted)
            if formatted:
                output_blocks.append(f"\n--- TABLE {idx} ---\n{formatted}\n")

    return output_blocks


# ================= MAIN ================= #

def extract_pdf_text(path: str) -> str:
    logger.info(f"Extracting text + tables + OCR images from PDF: {path}")

    _ensure_image_dir()
    combined_output = []
    seen_hashes = set()

    with pdfplumber.open(path) as pdf:

        for page_number, page in enumerate(pdf.pages, start=1):

            combined_output.append(f"\n\n===== PAGE {page_number} =====\n")

            # 1️⃣ DIGITAL TEXT
            text = page.extract_text()
            if text:
                combined_output.append(text)

            # 2️⃣ STRUCTURED TABLE EXTRACTION
            table_blocks = _extract_tables_with_fallback(page)
            combined_output.extend(table_blocks)

            # 3️⃣ IMAGE REGION OCR
            for img_index, img in enumerate(page.images, start=1):

                try:
                    x0 = img.get("x0")
                    top = img.get("top")
                    x1 = img.get("x1")
                    bottom = img.get("bottom")

                    if not all([x0, top, x1, bottom]):
                        continue

                    if not _is_valid_bbox(x0, top, x1, bottom):
                        continue

                    cropped = (
                        page.crop((x0, top, x1, bottom))
                        .to_image(resolution=300)
                        .original
                    )

                    img_bytes = cropped.tobytes()
                    img_hash = hashlib.md5(img_bytes).hexdigest()

                    if img_hash in seen_hashes:
                        continue

                    seen_hashes.add(img_hash)

                    ocr_text = _run_ocr_on_pil(cropped)

                    if ocr_text:
                        combined_output.append(
                            f"\n[IMAGE OCR DATA {img_index}]\n{ocr_text}\n"
                        )

                except Exception:
                    continue

            # 4️⃣ FULL PAGE OCR (only if page is scanned)
            if not text or len(text) < DIGITAL_TEXT_THRESHOLD:
                try:
                    logger.info(f"Running full-page OCR on page {page_number}")

                    images = convert_from_path(
                        path,
                        dpi=300,
                        first_page=page_number,
                        last_page=page_number
                    )

                    if images:
                        full_page_img = images[0]

                        img_bytes = full_page_img.tobytes()
                        img_hash = hashlib.md5(img_bytes).hexdigest()

                        if img_hash not in seen_hashes:
                            seen_hashes.add(img_hash)

                            ocr_text = _run_ocr_on_pil(full_page_img)

                            if ocr_text:
                                combined_output.append(
                                    f"\n[FULL PAGE OCR]\n{ocr_text}\n"
                                )

                except Exception:
                    continue

    return "\n".join(combined_output)