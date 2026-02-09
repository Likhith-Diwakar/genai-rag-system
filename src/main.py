
# src/main.py

import os
import tempfile

from src.list_docs import list_drive_documents
from src.extract_text import extract_doc_text
from src.extract_docx import extract_docx_text
from src.download_file import download_drive_file
from src.chunker import chunk_text
from src.embeddings import embed_texts
from src.vector_store import VectorStore
from src.tracker_db import TrackerDB
from src.logger import logger


GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def main():
    logger.info("Starting Drive → Vector sync")

    store = VectorStore()
    tracker = TrackerDB()

    docs = list_drive_documents()
    current_drive_ids = set()

    if not docs:
        logger.warning("No documents found in Drive")
        return

    for doc in docs:
        file_id = doc["id"]
        file_name = doc["name"]
        mime_type = doc["mimeType"]

        current_drive_ids.add(file_id)

        if tracker.is_ingested(file_id):
            logger.info(f"Skipping already ingested: {file_name}")
            continue

        logger.info(f"Ingesting: {file_name}")

        # ---------- TEXT EXTRACTION ----------
        try:
            if mime_type == GOOGLE_DOC_MIME:
                text = extract_doc_text(file_id)

            elif mime_type == DOCX_MIME:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
                    download_drive_file(file_id, tmp.name)
                    text = extract_docx_text(tmp.name)
                os.unlink(tmp.name)

            else:
                logger.warning(f"Unsupported file type: {file_name}")
                continue

        except Exception as e:
            logger.exception(f"Failed to extract text from {file_name}: {e}")
            continue

        if not text.strip():
            logger.warning(f"Empty document, skipping: {file_name}")
            continue

        # ---------- CHUNKING ----------
        chunks = chunk_text(text)
        if not chunks:
            logger.warning(f"No chunks created: {file_name}")
            continue

        # ---------- EMBEDDING ----------
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

    # ---------- HANDLE DELETED FILES ----------
    tracked_ids = tracker.get_all_file_ids()
    deleted_ids = tracked_ids - current_drive_ids

    for file_id in deleted_ids:
        logger.warning(f"Removing deleted file vectors: {file_id}")
        store.delete_by_file_id(file_id)
        tracker.remove(file_id)

    logger.info("Drive sync complete")


if __name__ == "__main__":
    main()
