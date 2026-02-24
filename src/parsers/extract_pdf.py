import os
import pdfplumber
import hashlib
import pytesseract
import pandas as pd
from pdf2image import convert_from_path
from PIL import Image
from src.utils.logger import logger
from src.parsers.vision_extractor import run_vision_extraction


IMAGE_OUTPUT_DIR = "data/tmp/pdf_images"

MIN_IMAGE_WIDTH = 80
MIN_IMAGE_HEIGHT = 80
DIGITAL_TEXT_THRESHOLD = 50

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def _ensure_image_dir():
    os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)


def _format_table(table):
    if not table or len(table) < 2:
        return ""

    try:
        header = [str(cell).strip() if cell else "" for cell in table[0]]
        rows = [
            [str(cell).strip() if cell else "" for cell in row]
            for row in table[1:]
        ]

        df = pd.DataFrame(rows, columns=header)

        output_blocks = []

        markdown_table = df.to_markdown(index=False)
        output_blocks.append(markdown_table)

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


def extract_pdf_text(path: str) -> str:
    logger.info(f"Extracting text + tables + OCR images from PDF: {path}")

    _ensure_image_dir()
    combined_output = []
    seen_hashes = set()

    with pdfplumber.open(path) as pdf:

        for page_number, page in enumerate(pdf.pages, start=1):

            # DEBUG: Count raster images
            logger.info(f"Page {page_number} contains {len(page.images)} raster images")

            combined_output.append(f"\n\n===== PAGE {page_number} =====\n")

            text = page.extract_text()
            if text:
                combined_output.append(text)

            table_blocks = _extract_tables_with_fallback(page)
            combined_output.extend(table_blocks)

            for img_index, img in enumerate(page.images, start=1):

                try:
                    logger.info(f"Processing image {img_index} on page {page_number}")

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

                    vision_text = run_vision_extraction(cropped)

                    if vision_text:
                        combined_output.append(
                            f"\n[IMAGE VISION DATA {img_index}]\n{vision_text}\n"
                        )
                    else:
                        ocr_text = _run_ocr_on_pil(cropped)
                        if ocr_text:
                            combined_output.append(
                                f"\n[IMAGE OCR DATA {img_index}]\n{ocr_text}\n"
                            )

                except Exception:
                    continue

            if not text or len(text) < DIGITAL_TEXT_THRESHOLD:
                try:
                    logger.info(f"Running full-page vision extraction on page {page_number}")

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

                            vision_text = run_vision_extraction(full_page_img)

                            if vision_text:
                                combined_output.append(
                                    f"\n[FULL PAGE VISION DATA]\n{vision_text}\n"
                                )
                            else:
                                ocr_text = _run_ocr_on_pil(full_page_img)
                                if ocr_text:
                                    combined_output.append(
                                        f"\n[FULL PAGE OCR]\n{ocr_text}\n"
                                    )

                except Exception:
                    continue

    return "\n".join(combined_output)