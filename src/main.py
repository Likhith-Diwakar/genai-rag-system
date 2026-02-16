# src/main.py

import os
import tempfile

from src.list_docs import list_drive_documents
from src.extract_text import extract_doc_text
from src.extract_docx import extract_docx_text
from src.extract_pdf import extract_pdf_text
from src.download_file import download_drive_file
from src.chunker import chunk_text
from src.embeddings import embed_texts
from src.vector_store import VectorStore
from src.tracker_db import TrackerDB
from src.logger import logger
from src.sqlite_store import SQLiteStore

import pandas as pd


GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"
CSV_MIME = "text/csv"


def main():
    logger.info("Starting Drive → Storage sync")

    store = VectorStore()
    tracker = TrackerDB()
    sqlite_store = SQLiteStore()

    docs = list_drive_documents()

    if not docs:
        logger.warning("No documents found in Drive")
        return

    for doc in docs:
        file_id = doc["id"]
        file_name = doc["name"]
        mime_type = doc["mimeType"]

        if tracker.is_ingested(file_id):
            logger.info(f"Skipping already ingested: {file_name}")
            continue

        logger.info(f"Ingesting: {file_name}")

        try:

            # ==========================================================
            # CSV → SQLITE
            # ==========================================================
            if mime_type == CSV_MIME:

                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                    download_drive_file(file_id, tmp.name)
                    temp_path = tmp.name

                try:
                    df = pd.read_csv(temp_path)
                    sqlite_store.store_dataframe(file_name, df)
                finally:
                    os.unlink(temp_path)

                tracker.mark_ingested(file_id, file_name)
                logger.info(f"Stored CSV in SQLite: {file_name}")
                continue

            # ==========================================================
            # TEXT DOCUMENTS → CHROMA
            # ==========================================================

            if mime_type == GOOGLE_DOC_MIME:
                text = extract_doc_text(file_id)

            elif mime_type == DOCX_MIME:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                    download_drive_file(file_id, tmp.name)
                    temp_path = tmp.name
                text = extract_docx_text(temp_path)
                os.unlink(temp_path)

            elif mime_type == PDF_MIME:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    download_drive_file(file_id, tmp.name)
                    temp_path = tmp.name
                text = extract_pdf_text(temp_path)
                os.unlink(temp_path)

            else:
                logger.warning(f"Unsupported file type: {file_name}")
                continue

        except Exception as e:
            logger.exception(f"Failed to extract text from {file_name}: {e}")
            continue

        if not text.strip():
            logger.warning(f"Empty document, skipping: {file_name}")
            continue

        chunks = chunk_text(text)

        if not chunks:
            logger.warning(f"No chunks created: {file_name}")
            continue

        embeddings = embed_texts(chunks)

        ids = [f"{file_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "file_id": file_id,
                "file_name": file_name,
                "chunk_id": i,
            }
            for i in range(len(chunks))
        ]

        store.add_chunks(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids,
        )

        tracker.mark_ingested(file_id, file_name)
        logger.info(f"Completed ingestion: {file_name}")

    logger.info("Drive sync complete")


if __name__ == "__main__":
    main()
