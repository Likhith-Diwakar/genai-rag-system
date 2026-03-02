import os
import re
import pdfplumber
import hashlib
import pandas as pd
from pdf2image import convert_from_path
from PIL import Image
from src.utils.logger import logger
from src.parsers.vision_extractor import run_vision_extraction


IMAGE_OUTPUT_DIR = "data/tmp/pdf_images"

MIN_IMAGE_WIDTH = 80
MIN_IMAGE_HEIGHT = 80
DIGITAL_TEXT_THRESHOLD = 200

# Safety cap to prevent quota explosion
MAX_VISION_CALLS_PER_DOC = 5


def _ensure_image_dir():
    os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)


# -----------------------------
# CID GARBAGE CLEANER
# -----------------------------
def _clean_cid_garbage(text: str) -> str:
    cleaned = re.sub(r'\(cid:\d+\)', '', text)
    cleaned = re.sub(r' {2,}', ' ', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


# -----------------------------
# SAFE convert_from_path WRAPPER
# Render-safe (no poppler required)
# -----------------------------
def _convert_page_to_image(path: str, page_number: int):
    """
    Converts a single PDF page to a PIL image.
    Uses pypdfium2 backend to avoid poppler dependency.
    Fully compatible with Render Free plan.
    """

    try:
        images = convert_from_path(
            path,
            dpi=300,
            first_page=page_number,
            last_page=page_number,
            backend="pypdfium2"
        )
        return images

    except Exception as e:
        logger.error(
            f"convert_from_path failed on page {page_number} "
            f"(pypdfium2 backend). Error: {e}"
        )
        return []


# -----------------------------
# TABLE FORMATTER
# -----------------------------
def _format_table(table, table_id=None):

    if not table or len(table) < 2:
        return []

    try:
        header = [str(cell).strip() if cell else "" for cell in table[0]]
        rows = [
            [str(cell).strip() if cell else "" for cell in row]
            for row in table[1:]
        ]

        df = pd.DataFrame(rows, columns=header)

        row_blocks = []

        for _, row in df.iterrows():
            block_lines = []
            block_lines.append(f"TABLE_ID = {table_id}")
            block_lines.append("TABLE_ROW_START")

            for col in df.columns:
                value = str(row[col]).strip()
                if value:
                    block_lines.append(f"{col} : {value}")

            block_lines.append("TABLE_ROW_END")

            row_text = "\n".join(block_lines).strip()

            if row_text:
                row_blocks.append(row_text)

        return row_blocks

    except Exception as e:
        logger.warning(f"Table formatting failed, using fallback: {e}")
        fallback_lines = []
        for row in table:
            cleaned = [
                str(cell).strip() if cell is not None else ""
                for cell in row
            ]
            fallback_lines.append(" | ".join(cleaned))

        return ["TABLE_FALLBACK\n" + "\n".join(fallback_lines)]


def _is_valid_bbox(x0, top, x1, bottom):
    if x1 <= x0 or bottom <= top:
        return False
    if (x1 - x0) < MIN_IMAGE_WIDTH:
        return False
    if (bottom - top) < MIN_IMAGE_HEIGHT:
        return False
    return True


# -----------------------------
# TABLE EXTRACTION
# -----------------------------
def _extract_tables(page, page_number):
    output_blocks = []
    found_tables = page.find_tables()

    for idx, table in enumerate(found_tables, start=1):
        extracted = table.extract()
        if extracted:
            formatted_rows = _format_table(
                extracted,
                table_id=f"PAGE_{page_number}_TABLE_{idx}"
            )

            for row_block in formatted_rows:
                output_blocks.append(f"\n{row_block}\n")

    return output_blocks


# -----------------------------
# SMART IMAGE DETECTOR
# -----------------------------
def _is_meaningful_image(x0, top, x1, bottom, page):

    page_width = page.width
    page_height = page.height
    page_area = page_width * page_height

    img_width = x1 - x0
    img_height = bottom - top
    img_area = img_width * img_height

    area_ratio = img_area / page_area
    width_ratio = img_width / page_width
    height_ratio = img_height / page_height

    if area_ratio >= 0.08:
        return True

    if width_ratio >= 0.35:
        return True

    if height_ratio >= 0.30:
        return True

    return False


# -----------------------------
# MAIN PDF EXTRACTION
# -----------------------------
def extract_pdf_text(path: str) -> str:

    logger.info(f"Extracting text + tables + vision from PDF: {path}")

    _ensure_image_dir()
    combined_output = []
    seen_hashes = set()
    vision_calls = 0

    with pdfplumber.open(path) as pdf:

        for page_number, page in enumerate(pdf.pages, start=1):

            logger.info(f"Page {page_number} contains {len(page.images)} raster images")

            combined_output.append(f"\n\n===== PAGE {page_number} =====\n")

            # 1️⃣ Extract digital text
            text = page.extract_text()
            if text:
                text = _clean_cid_garbage(text)
                combined_output.append(text)

            # 2️⃣ Extract structured tables
            table_blocks = _extract_tables(page, page_number)
            if table_blocks:
                logger.info(f"Page {page_number}: extracted {len(table_blocks)} table row blocks via pdfplumber")
            combined_output.extend(table_blocks)

            # 3️⃣ Chart-heavy detection
            if (
                len(page.images) >= 3
                and text
                and vision_calls < MAX_VISION_CALLS_PER_DOC
            ):
                logger.info(f"Chart-heavy page detected on page {page_number}. Running full-page vision.")
                try:
                    images = _convert_page_to_image(path, page_number)

                    if images:
                        full_page_img = images[0]
                        img_hash = hashlib.md5(full_page_img.tobytes()).hexdigest()

                        if img_hash not in seen_hashes:
                            seen_hashes.add(img_hash)

                            vision_text = run_vision_extraction(full_page_img)

                            if vision_text:
                                vision_calls += 1
                                combined_output.append(
                                    f"\n[FULL_PAGE_VISION_{page_number}]\n{vision_text}\n"
                                )

                    continue

                except Exception as e:
                    logger.error(f"Page {page_number}: chart-heavy vision failed: {e}")

            # 4️⃣ Per-image processing
            for img_index, img in enumerate(page.images, start=1):

                if vision_calls >= MAX_VISION_CALLS_PER_DOC:
                    break

                try:
                    x0 = img.get("x0")
                    top = img.get("top")
                    x1 = img.get("x1")
                    bottom = img.get("bottom")

                    if any(v is None for v in [x0, top, x1, bottom]):
                        continue

                    if not _is_valid_bbox(x0, top, x1, bottom):
                        continue

                    if not _is_meaningful_image(x0, top, x1, bottom, page):
                        continue

                    cropped = (
                        page.crop((x0, top, x1, bottom))
                        .to_image(resolution=300)
                        .original
                    )

                    img_hash = hashlib.md5(cropped.tobytes()).hexdigest()

                    if img_hash in seen_hashes:
                        continue

                    seen_hashes.add(img_hash)

                    vision_text = run_vision_extraction(cropped)

                    if vision_text:
                        vision_calls += 1
                        combined_output.append(
                            f"\n[IMAGE_VISION_PAGE_{page_number}_{img_index}]\n{vision_text}\n"
                        )

                except Exception:
                    continue

            # 5️⃣ Scanned fallback
            if (
                (not text or len(text) < DIGITAL_TEXT_THRESHOLD)
                and vision_calls < MAX_VISION_CALLS_PER_DOC
            ):
                try:
                    images = _convert_page_to_image(path, page_number)

                    if images:
                        full_page_img = images[0]
                        img_hash = hashlib.md5(full_page_img.tobytes()).hexdigest()

                        if img_hash not in seen_hashes:
                            seen_hashes.add(img_hash)

                            vision_text = run_vision_extraction(full_page_img)

                            if vision_text:
                                vision_calls += 1
                                combined_output.append(
                                    f"\n[FULL_PAGE_VISION_{page_number}]\n{vision_text}\n"
                                )

                except Exception:
                    continue

    return "\n".join(combined_output)