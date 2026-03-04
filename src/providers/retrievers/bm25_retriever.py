# src/providers/retrievers/bm25_retriever.py

import os
import pickle
from typing import List, Dict
from rank_bm25 import BM25Okapi
from src.utils.logger import logger
from src.embedding.vector_store import VectorStore


class BM25Retriever:
    """
    Sparse lexical retriever using BM25.
    Complements dense embedding search.
    """

    def __init__(self, persist_path: str = "data/bm25_index.pkl"):
        self.persist_path = persist_path
        self.corpus: List[str] = []
        self.metadata_refs: List[Dict] = []
        self.bm25 = None
        self.vector_store = VectorStore()
        self._rebuilt_from_vector_store = False

    # -----------------------------
    # Tokenization
    # -----------------------------
    def _tokenize(self, text: str) -> List[str]:
        return text.lower().split()

    # -----------------------------
    # Build BM25
    # -----------------------------
    def _build_index(self):

        if not self.corpus:
            self.bm25 = None
            return

        tokenized_corpus = [self._tokenize(doc) for doc in self.corpus]
        self.bm25 = BM25Okapi(tokenized_corpus)

    # -----------------------------
    # Load from Qdrant if index missing
    # -----------------------------
    def _load_from_vector_store(self):

        if self._rebuilt_from_vector_store:
            return

        logger.info("Rebuilding BM25 index from vector store")

        try:

            self.corpus = []
            self.metadata_refs = []

            offset = None

            while True:

                points, offset = self.vector_store.client.scroll(
                    collection_name="drive_docs",
                    limit=100,
                    with_payload=True,
                    offset=offset
                )

                if not points:
                    break

                for point in points:

                    payload = point.payload or {}

                    document = payload.get("document")

                    if not document:
                        continue

                    metadata = {
                        k: v for k, v in payload.items()
                        if k != "document"
                    }

                    self.corpus.append(document)
                    self.metadata_refs.append(metadata)

                if offset is None:
                    break

            logger.info(f"BM25 rebuilt with {len(self.corpus)} chunks")

            self._build_index()
            self._persist()

            self._rebuilt_from_vector_store = True

        except Exception:
            logger.exception("Failed rebuilding BM25 from vector store")

    # -----------------------------
    # Add Chunks (during ingestion)
    # -----------------------------
    def add_chunks(self, documents: List[str], metadatas: List[Dict]):

        for doc, meta in zip(documents, metadatas):
            self.corpus.append(doc)
            self.metadata_refs.append(meta)

        self._build_index()
        self._persist()

        logger.info(f"BM25 index updated with {len(documents)} new chunks.")

    # -----------------------------
    # Query
    # -----------------------------
    def query(self, query: str, top_k: int = 10) -> List[Dict]:

        if not self.bm25:

            logger.warning("BM25 index not initialized.")

            if not self.corpus:
                self.load()

            if not self.corpus:
                self._load_from_vector_store()

            if not self.bm25:
                return []

        tokens = self._tokenize(query)

        scores = self.bm25.get_scores(tokens)

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True
        )[:top_k]

        results = []

        for idx in ranked_indices:

            if scores[idx] <= 0:
                continue

            results.append({
                "document": self.corpus[idx],
                "metadata": self.metadata_refs[idx],
                "score": float(scores[idx])
            })

        return results

    # -----------------------------
    # Persistence
    # -----------------------------
    def _persist(self):

        os.makedirs(os.path.dirname(self.persist_path), exist_ok=True)

        with open(self.persist_path, "wb") as f:

            pickle.dump({
                "corpus": self.corpus,
                "metadata_refs": self.metadata_refs
            }, f)

    # -----------------------------
    # Load saved index
    # -----------------------------
    def load(self):

        if not os.path.exists(self.persist_path):

            logger.info("No existing BM25 index found.")
            return

        with open(self.persist_path, "rb") as f:

            data = pickle.load(f)

        self.corpus = data.get("corpus", [])
        self.metadata_refs = data.get("metadata_refs", [])

        self._build_index()

        logger.info(f"BM25 index loaded with {len(self.corpus)} chunks.")