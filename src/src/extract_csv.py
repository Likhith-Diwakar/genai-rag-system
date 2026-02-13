# src/extract_csv.py

import csv
from src.logger import logger


def extract_csv_text(file_path: str) -> str:
    logger.info(f"Extracting text from CSV: {file_path}")

    lines = []

    with open(file_path, newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        for row in reader:
            cleaned = [cell.strip() for cell in row if cell.strip()]
            if cleaned:
                lines.append(" | ".join(cleaned))

    text = "\n".join(lines)
    logger.info(f"Extracted {len(lines)} rows from CSV")

    return text
