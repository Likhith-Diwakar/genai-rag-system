# src/ingestion/main.py

import os
import tempfile
import pandas as pd

from src.ingestion.list_docs import list_drive_documents
from src.ingestion.download_file import download_drive_file

from src.providers.parsers.parser_router import ParserRouter
from src.providers.embeddings.bge_embedder import BGEEmbedder
from src.providers.vectorstores.chroma_store import ChromaVectorStore
from src.providers.chunking.chunking_router import ChunkingRouter

from src.storage.tracker_db import TrackerDB
from src.storage.sqlite_store import SQLiteStore
from src.utils.logger import logger


GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"
CSV_MIME = "text/csv"


def main():

    vector_store = ChromaVectorStore()
    embedder = BGEEmbedder()
    tracker = TrackerDB()
    sqlite_store = SQLiteStore()
    parser_router = ParserRouter()
    chunk_router = ChunkingRouter()

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

        vector_store.delete_by_file_id(file_id)

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
            # CSV → SQLite (special case)
            # -------------------------------
            if mime_type == CSV_MIME:

                parser = parser_router.route(file_name)
                parser.parse(file_id, file_name)

                tracker.mark_ingested(file_id, file_name)
                continue

            # -------------------------------
            # Google Docs
            # -------------------------------
            if mime_type == GOOGLE_DOC_MIME:
                parser = parser_router.route(file_name)
                text = parser.parse(file_id)

            # -------------------------------
            # DOCX / PDF
            # -------------------------------
            elif mime_type in [DOCX_MIME, PDF_MIME]:

                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    download_drive_file(file_id, tmp.name)
                    temp_path = tmp.name

                parser = parser_router.route(file_name)
                text = parser.parse(temp_path)

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

        # -------------------------------
        # Chunking (MODULAR)
        # -------------------------------

        chunker = chunk_router.route(mime_type)
        chunks = chunker.chunk(text)

        if not chunks:
            logger.warning(f"No chunks created → {file_name}")
            tracker.mark_ingested(file_id, file_name)
            continue

        # -------------------------------
        # Embedding
        # -------------------------------

        embeddings = embedder.embed(chunks)

        ids = [f"{file_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "file_id": file_id,
                "file_name": file_name,
                "chunk_id": i,
            }
            for i in range(len(chunks))
        ]

        vector_store.add_chunks(
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