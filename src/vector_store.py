# src/vector_store.py

import chromadb
from chromadb.config import Settings
from src.logger import logger

CHROMA_DIR = "data/chroma"


class VectorStore:
    def __init__(self):
        logger.info("Initializing ChromaDB")
        self.client = chromadb.PersistentClient(
            path=CHROMA_DIR,
            settings=Settings(anonymized_telemetry=False)
        )

        self.collection = self.client.get_or_create_collection(
            name="drive_docs"
        )

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
