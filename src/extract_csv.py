# src/extract_csv.py

import tempfile
import os
import pandas as pd

from src.download_file import download_drive_file
from src.sqlite_store import SQLiteStore
from src.logger import logger


def extract_csv_text(file_id: str, file_name: str):
    """
    Downloads CSV from Drive and stores it directly in SQLite.
    No embeddings.
    No text conversion.
    """

    logger.info(f"Downloading CSV for SQLite storage: {file_name}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        download_drive_file(file_id, tmp.name)
        temp_path = tmp.name

    try:
        df = pd.read_csv(temp_path)

        store = SQLiteStore()
        store.store_dataframe(file_name, df)

        logger.info(f"Stored CSV into SQLite: {file_name}")

    except Exception as e:
        logger.exception(f"Failed to store CSV in SQLite: {e}")

    finally:
        os.unlink(temp_path)