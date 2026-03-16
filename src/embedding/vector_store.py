# src/embedding/vector_store.py

import os
import threading
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from src.utils.logger import logger

# ----------------------------------------------------------
# Qdrant Configuration
# ----------------------------------------------------------

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "drive_docs"

_client = None
_lock = threading.Lock()


def _initialize():
    global _client

    if _client is None:
        with _lock:
            if _client is None:

                if not QDRANT_URL or not QDRANT_API_KEY:
                    raise RuntimeError(
                        "QDRANT_URL or QDRANT_API_KEY not set"
                    )

                logger.info("Initializing Qdrant Cloud connection")

                _client = QdrantClient(
                    url=QDRANT_URL.strip(),
                    api_key=QDRANT_API_KEY.strip(),
                )

                # Create collection if not exists
                existing_collections = [
                    c.name for c in _client.get_collections().collections
                ]

                if COLLECTION_NAME not in existing_collections:
                    logger.info("Creating Qdrant collection")

                    _client.create_collection(
                        collection_name=COLLECTION_NAME,
                        vectors_config=VectorParams(
                            size=384,  # bge-small-en-v1.5 dimension
                            distance=Distance.COSINE,
                        ),
                    )

    return _client


class VectorStore:
    def __init__(self):
        self.client = _initialize()

    # ------------------------------------------------------
    # ADD CHUNKS (Fixed UUID IDs)
    # ------------------------------------------------------
    def add_chunks(self, embeddings, documents, metadatas, ids):

        logger.info(f"Adding {len(documents)} chunks to Qdrant")

        points = []

        for i in range(len(documents)):

            payload = metadatas[i].copy()

            # --------------------------------------------------
            # Ensure page_number is stored safely if present
            # --------------------------------------------------
            if "page_number" in payload:
                try:
                    payload["page_number"] = int(payload["page_number"])
                except Exception:
                    payload["page_number"] = None

            payload["document"] = documents[i]

            # Convert deterministic UUID from string ID
            generated_id = str(
                uuid.uuid5(uuid.NAMESPACE_DNS, str(ids[i]))
            )

            points.append(
                PointStruct(
                    id=generated_id,
                    vector=embeddings[i],
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=COLLECTION_NAME,
            points=points,
        )

    # ------------------------------------------------------
    # DELETE BY FILE ID
    # ------------------------------------------------------
    def delete_by_file_id(self, file_id: str):

        logger.warning(f"Deleting vectors for file_id={file_id}")

        self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="file_id",
                        match=MatchValue(value=file_id),
                    )
                ]
            ),
        )

    # ------------------------------------------------------
    # COUNT
    # ------------------------------------------------------
    def count(self) -> int:

        count = self.client.count(
            collection_name=COLLECTION_NAME
        ).count

        logger.info(f"Total vectors in Qdrant: {count}")

        return count

    # ------------------------------------------------------
    # QUERY (Qdrant v1.17 compatible)
    # ------------------------------------------------------
    def query(self, embedding: list, n_results: int):

        results = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=embedding,
            limit=n_results,
            with_payload=True,
        )

        documents = []
        metadatas = []
        distances = []

        for hit in results.points:

            payload = hit.payload or {}

            documents.append(payload.get("document"))

            # Remove document field from metadata
            metadatas.append(
                {k: v for k, v in payload.items() if k != "document"}
            )

            # Convert similarity to distance-like value
            distances.append(1 - hit.score)

        return {
            "documents": [documents],
            "metadatas": [metadatas],
            "distances": [distances],
        }