import os
import tempfile

from src.ingestion.list_docs import list_drive_documents
from src.parsers.extract_text import extract_doc_text
from src.parsers.extract_docx import extract_docx_text
from src.parsers.extract_pdf import extract_pdf_text
from src.ingestion.download_file import download_drive_file
from src.chunking.chunker import chunk_text
from src.embedding.embeddings import embed_texts
from src.embedding.vector_store import VectorStore
from src.storage.tracker_db import TrackerDB
from src.storage.sqlite_store import SQLiteStore
from src.utils.logger import logger

import pandas as pd


GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"
CSV_MIME = "text/csv"


def main():

    store = VectorStore()
    tracker = TrackerDB()
    sqlite_store = SQLiteStore()

    # ✅ Already filtered at source level
    docs = list_drive_documents()

    if not docs:
        logger.info("No documents found in target folder.")
        return

    # ===============================
    # DELETION LOGIC
    # ===============================

    drive_file_ids = {doc["id"] for doc in docs}
    tracked_file_ids = tracker.get_all_file_ids()

    deleted_file_ids = tracked_file_ids - drive_file_ids

    for file_id in deleted_file_ids:

        file_name = tracker.get_file_name(file_id)

        logger.info(f"File deleted from Drive → {file_name}")

        store.delete_by_file_id(file_id)

        if file_name:
            try:
                sqlite_store.drop_table(file_name)
            except Exception:
                pass

        tracker.remove(file_id)

    # ===============================
    # INGESTION LOGIC
    # ===============================

    for doc in docs:

        file_id = doc["id"]
        file_name = doc["name"]
        mime_type = doc["mimeType"]

        if tracker.is_ingested(file_id):
            continue

        logger.info(f"New file detected → {file_name}")

        text = ""

        try:

            # -------------------------------
            # CSV → SQLite
            # -------------------------------
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
                continue

            # -------------------------------
            # Google Doc
            # -------------------------------
            if mime_type == GOOGLE_DOC_MIME:
                text = extract_doc_text(file_id)

            # -------------------------------
            # DOCX
            # -------------------------------
            elif mime_type == DOCX_MIME:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                    download_drive_file(file_id, tmp.name)
                    temp_path = tmp.name
                text = extract_docx_text(temp_path)
                os.unlink(temp_path)

            # -------------------------------
            # PDF
            # -------------------------------
            elif mime_type == PDF_MIME:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    download_drive_file(file_id, tmp.name)
                    temp_path = tmp.name
                text = extract_pdf_text(temp_path)
                os.unlink(temp_path)

            else:
                tracker.mark_ingested(file_id, file_name)
                continue

        except Exception:
            logger.warning(f"Extraction failed → {file_name}")
            tracker.mark_ingested(file_id, file_name)
            continue

        if not text or not text.strip():
            logger.warning(f"No text extracted → {file_name}")
            tracker.mark_ingested(file_id, file_name)
            continue

        # ✅ Pass mime type to chunker (important for PDF strategy)
        chunks = chunk_text(text, mime_type=mime_type)

        if not chunks:
            logger.warning(f"No chunks created → {file_name}")
            tracker.mark_ingested(file_id, file_name)
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


def run_sync(verbose: bool = True):
    main()


if __name__ == "__main__":
    run_sync()