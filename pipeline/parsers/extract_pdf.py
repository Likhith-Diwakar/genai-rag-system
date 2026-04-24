import os
import re
import pdfplumber
import pandas as pd
import unicodedata
from pdf2image import convert_from_path

from pipeline.utils.logger import logger
from pipeline.utils.metrics import metrics
from pipeline.parsers.vision_extractor import run_vision_extraction, GeminiQuotaExhaustedError


IMAGE_OUTPUT_DIR = "data/tmp/pdf_images"

MIN_IMAGE_WIDTH = 80
MIN_IMAGE_HEIGHT = 80


def _ensure_image_dir():
    os.makedirs(IMAGE_OUTPUT_DIR, exist_ok=True)


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\x00-\x08\x0B-\x1F\x7F]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _clean_cid_garbage(text: str):
    if not text:
        return ""
    text = re.sub(r"\(cid:\d+\)", "", text)
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _get_alpha_ratio(text: str) -> float:
    if not text:
        return 0.0
    total = len(text)
    alpha = sum(c.isalpha() for c in text)
    return alpha / max(total, 1)


def _is_text_low_quality(text: str) -> bool:
    return _get_alpha_ratio(text) < 0.40


def _convert_page_to_image(path: str, page_number: int):
    try:
        return convert_from_path(
            path,
            dpi=300,
            first_page=page_number,
            last_page=page_number
        )
    except Exception as e:
        logger.error(f"Image conversion failed page {page_number}: {e}")
        return []


def _extract_tables(page, page_number):
    output = []
    tables = page.find_tables()
    for idx, table in enumerate(tables, start=1):
        extracted = table.extract()
        if not extracted or len(extracted) < 2:
            continue
        try:
            header = extracted[0]
            rows = extracted[1:]
            df = pd.DataFrame(rows, columns=header)
            for _, row in df.iterrows():
                lines = [
                    f"TABLE_ID = PAGE_{page_number}_TABLE_{idx}",
                    "TABLE_ROW_START"
                ]
                for col in df.columns:
                    val = str(row[col]).strip()
                    if val:
                        lines.append(f"{col} : {val}")
                lines.append("TABLE_ROW_END")
                output.append(_normalize_text("\n".join(lines)))
        except Exception:
            continue
    return output


def _filter_low_quality_lines(text: str) -> str:
    if not text:
        return ""
    lines = text.split("\n")
    clean = []
    for line in lines:
        s = line.strip()
        if not s:
            clean.append(line)
            continue
        if len(s) > 80:
            clean.append(line)
            continue
        if _is_text_low_quality(s):
            continue
        clean.append(line)
    return "\n".join(clean)


def extract_pdf_text(path: str) -> str:

    logger.info(f"Extracting PDF: {path}")

    _ensure_image_dir()

    combined = []

    # vision_attempts: every OCR attempt regardless of outcome
    # vision_calls:    only successful OCR extractions
    vision_attempts = 0
    vision_calls = 0
    max_vision_calls = 3

    # Set True on first 429 — stops all further OCR calls for this document
    gemini_quota_exhausted = False

    with pdfplumber.open(path) as pdf:

        total_pages = len(pdf.pages)

        for page_number, page in enumerate(pdf.pages, start=1):

            combined.append(f"\n\n===== PAGE {page_number} =====\n")
            combined.append(f"PAGE_NUMBER : {page_number}")

            text = page.extract_text() or ""
            alpha_ratio = _get_alpha_ratio(text)

            logger.info(f"Page {page_number} | alpha_ratio={alpha_ratio:.2f}")

            use_ocr = False

            if _is_text_low_quality(text):
                use_ocr = True

            if page_number <= 2 and alpha_ratio < 0.6:
                use_ocr = True

            if use_ocr:

                if gemini_quota_exhausted:
                    # Quota already known exhausted — skip API call entirely
                    logger.info(
                        f"Page {page_number} | Gemini quota exhausted — "
                        f"using pdfplumber text fallback"
                    )
                    text = _filter_low_quality_lines(text)

                elif vision_calls >= max_vision_calls:
                    logger.info(
                        f"Page {page_number} | OCR budget exhausted "
                        f"({vision_calls}/{max_vision_calls}) — "
                        f"using pdfplumber text fallback"
                    )
                    text = _filter_low_quality_lines(text)

                else:
                    images = _convert_page_to_image(path, page_number)

                    if images:
                        vision_attempts += 1

                        # Count every OCR attempt before the API call is made
                        metrics.inc("ocr_attempts")

                        try:
                            vision_text = run_vision_extraction(images[0])

                            if vision_text:
                                text = vision_text
                                vision_calls += 1
                                # Count only extractions that returned usable text
                                metrics.inc("ocr_success")
                                logger.info(
                                    f"OCR success page {page_number} | "
                                    f"attempts={vision_attempts} "
                                    f"successes={vision_calls}"
                                )
                            else:
                                logger.warning(
                                    f"Page {page_number} | OCR returned empty text, "
                                    f"falling back to pdfplumber"
                                )
                                # API responded but returned nothing useful — treat as failure
                                metrics.inc("ocr_fail")
                                text = _filter_low_quality_lines(text)

                        except GeminiQuotaExhaustedError:
                            # 429 raised by vision_extractor — disable OCR immediately
                            logger.warning(
                                f"Page {page_number} | Gemini quota exhausted (429) — "
                                f"disabling OCR for all remaining pages, "
                                f"falling back to pdfplumber"
                            )
                            metrics.inc("ocr_fail")
                            gemini_quota_exhausted = True
                            text = _filter_low_quality_lines(text)

                        except Exception as e:
                            logger.warning(
                                f"Page {page_number} | OCR failed unexpectedly: {e} — "
                                f"falling back to pdfplumber"
                            )
                            metrics.inc("ocr_fail")
                            text = _filter_low_quality_lines(text)

                    else:
                        logger.warning(
                            f"Page {page_number} | Image conversion produced no output, "
                            f"falling back to pdfplumber"
                        )
                        text = _filter_low_quality_lines(text)

            else:
                text = _filter_low_quality_lines(text)

            text = _clean_cid_garbage(text)
            text = _normalize_text(text)

            if text:
                combined.append(text)

            tables = _extract_tables(page, page_number)
            combined.extend(tables)

    logger.info(
        f"PDF extraction complete | pages={total_pages} "
        f"ocr_attempts={vision_attempts} ocr_successes={vision_calls}"
    )

    return "\n".join(combined)
