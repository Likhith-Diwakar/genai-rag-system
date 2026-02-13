# src/extract_csv.py

import csv
import tempfile
import os
from src.download_file import download_drive_file
from src.logger import logger


def extract_csv_text(file_id: str) -> str:
    """
    Downloads a CSV file from Google Drive and converts it into
    structured semantic text.

    Strategy:
    - First line: schema description
    - Then: one structured block per row
    """

    logger.info(f"Extracting text from CSV: {file_id}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        download_drive_file(file_id, tmp.name)
        temp_path = tmp.name

    structured_output = []

    try:
        with open(temp_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            headers = reader.fieldnames
            if not headers:
                logger.warning("CSV has no headers")
                return ""

            # Add schema summary
            structured_output.append(
                "CSV Schema:\n" + ", ".join(headers) + "\n"
            )

            # Row-based structured conversion
            for row_index, row in enumerate(reader):
                row_lines = [f"Row {row_index + 1}:"]
                for key in headers:
                    value = row.get(key, "")
                    row_lines.append(f"{key}: {value}")
                structured_output.append("\n".join(row_lines))

    except Exception as e:
        logger.exception(f"Failed to parse CSV: {e}")
        return ""

    finally:
        os.unlink(temp_path)

    final_text = "\n\n".join(structured_output)

    logger.info(f"CSV extraction completed | length={len(final_text)} characters")

    return final_text
