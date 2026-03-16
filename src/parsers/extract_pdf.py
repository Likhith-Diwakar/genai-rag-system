import os
import re
import pdfplumber
import pandas as pd
import unicodedata
from pdf2image import convert_from_path
from src.utils.logger import logger
from src.parsers.vision_extractor import run_vision_extraction


IMAGE_OUTPUT_DIR = "data/tmp/pdf_images"

MIN_IMAGE_WIDTH = 80
MIN_IMAGE_HEIGHT = 80
MAX_VISION_CALLS_PER_DOC = 5


def _ensure_image_dir():
    os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)


# --------------------------------------------------
# UNIVERSAL TEXT NORMALIZER
# --------------------------------------------------
def _normalize_text(text: str) -> str:

    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\x00-\x08\x0B-\x1F\x7F]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# --------------------------------------------------
# CID CLEANER
# --------------------------------------------------
def _clean_cid_garbage(text: str):
    cleaned = re.sub(r'\(cid:\d+\)', '', text)
    cleaned = re.sub(r' {2,}', ' ', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


# --------------------------------------------------
# TEXT QUALITY DETECTION (ALPHABET DENSITY)
# --------------------------------------------------
def _is_text_low_quality(text: str) -> bool:
    """
    Detects broken CID/font encoded text using alphabet density.
    If fewer than 40% of characters are alphabetic, treat as low quality.
    Works at both page level and line level.
    """

    if not text or len(text.strip()) < 10:
        return True

    total_chars = len(text)
    alpha_chars = sum(c.isalpha() for c in text)
    alpha_ratio = alpha_chars / max(total_chars, 1)

    return alpha_ratio < 0.40


# --------------------------------------------------
# SAFE PAGE TO IMAGE (no backend kwarg)
# --------------------------------------------------
def _convert_page_to_image(path: str, page_number: int):

    try:
        images = convert_from_path(
            path,
            dpi=300,
            first_page=page_number,
            last_page=page_number
        )
        return images

    except Exception as e:
        logger.error(
            f"convert_from_path failed on page {page_number}. Error: {e}"
        )
        return []


# --------------------------------------------------
# TABLE FORMATTER
# --------------------------------------------------
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
            row_text = _normalize_text(row_text)

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

        fallback_text = "TABLE_FALLBACK\n" + "\n".join(fallback_lines)
        return [_normalize_text(fallback_text)]


def _is_valid_bbox(x0, top, x1, bottom):
    if x1 <= x0 or bottom <= top:
        return False
    if (x1 - x0) < MIN_IMAGE_WIDTH:
        return False
    if (bottom - top) < MIN_IMAGE_HEIGHT:
        return False
    return True


# --------------------------------------------------
# TABLE EXTRACTION
# --------------------------------------------------
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


# --------------------------------------------------
# IMAGE SIGNIFICANCE DETECTION
# --------------------------------------------------
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


# --------------------------------------------------
# LINE-LEVEL GARBAGE FILTER
# --------------------------------------------------
def _filter_low_quality_lines(text: str, page_number: int) -> str:
    """
    Filters individual lines that are low-quality (CID garbage)
    while preserving the rest of the page text.
    Used when the overall page alpha ratio looks healthy but
    individual lines contain corrupted font glyphs.
    Only applies to short/medium lines — long lines are
    almost certainly real content and are always kept.
    """

    lines = text.split("\n")
    clean_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            clean_lines.append(line)
            continue

        # Long lines are almost certainly real content — always keep
        if len(stripped) > 80:
            clean_lines.append(line)
            continue

        if _is_text_low_quality(stripped):
            logger.debug(
                f"Page {page_number} | Dropped low-quality line: {repr(stripped[:60])}"
            )
            continue

        clean_lines.append(line)

    return "\n".join(clean_lines)


# --------------------------------------------------
# MAIN PDF EXTRACTION
# --------------------------------------------------
def extract_pdf_text(path: str) -> str:

    logger.info(f"Extracting text + tables + vision from PDF: {path}")

    _ensure_image_dir()
    combined_output = []
    vision_calls = 0

    with pdfplumber.open(path) as pdf:

        for page_number, page in enumerate(pdf.pages, start=1):

            logger.info(f"Page {page_number} contains {len(page.images)} raster images")

            combined_output.append(f"\n\n===== PAGE {page_number} =====\n")
            combined_output.append(f"PAGE_NUMBER : {page_number}")

            text = page.extract_text()

            if text:

                # Log page-level alpha ratio for diagnostics
                alpha_chars = sum(c.isalpha() for c in text)
                alpha_ratio = alpha_chars / max(len(text), 1)
                logger.info(
                    f"DEBUG Page {page_number} | alpha_ratio={alpha_ratio:.2f} | chars={len(text)}"
                )

                # Page-level OCR fallback: fires when whole page is heavily corrupted
                if _is_text_low_quality(text) and vision_calls < MAX_VISION_CALLS_PER_DOC:
                    logger.warning(
                        f"Low quality page detected (page {page_number}, "
                        f"alpha_ratio={alpha_ratio:.2f}). Using Vision OCR fallback."
                    )

                    images = _convert_page_to_image(path, page_number)

                    if images:
                        try:
                            vision_text = run_vision_extraction(images[0])
                            if vision_text:
                                text = vision_text
                                vision_calls += 1
                                logger.info(
                                    f"Vision OCR succeeded on page {page_number}. "
                                    f"vision_calls={vision_calls}"
                                )
                        except Exception as e:
                            logger.error(f"Vision extraction failed on page {page_number}: {e}")

                else:
                    # Line-level filter: removes only corrupted lines on otherwise good pages
                    text = _filter_low_quality_lines(text, page_number)

                text = _clean_cid_garbage(text)
                text = _normalize_text(text)
                combined_output.append(text)

            table_blocks = _extract_tables(page, page_number)
            combined_output.extend(table_blocks)

    return "\n".join(combined_output)
