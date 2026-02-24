# src/embedding/vector_store.py

import os
import threading
import chromadb
from chromadb.config import Settings
from src.utils.logger import logger

# Disable Chroma telemetry
os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"
os.environ["ANONYMIZED_TELEMETRY"] = "false"

CHROMA_DIR = "data/chroma"

_client = None
_collection = None
_lock = threading.Lock()


def _initialize():
    global _client, _collection

    if _client is None:
        with _lock:
            if _client is None:
                logger.info("Initializing ChromaDB (telemetry disabled)")

                _client = chromadb.PersistentClient(
                    path=CHROMA_DIR,
                    settings=Settings(
                        anonymized_telemetry=False,
                        allow_reset=True
                    )
                )

                _collection = _client.get_or_create_collection(
                    name="drive_docs"
                )

    return _collection


class VectorStore:
    def __init__(self):
        self.collection = _initialize()

    def add_chunks(self, embeddings, documents, metadatas, ids):
        logger.info(f"Adding {len(documents)} chunks to ChromaDB")
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def delete_by_file_id(self, file_id: str):
        logger.warning(f"Deleting vectors for file_id={file_id}")
        self.collection.delete(where={"file_id": file_id})

    def count(self) -> int:
        count = self.collection.count()
        logger.info(f"Total vectors in ChromaDB: {count}")
        return count