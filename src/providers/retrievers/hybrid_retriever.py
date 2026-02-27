# src/providers/retrievers/hybrid_retriever.py

import re
from src.providers.embeddings.bge_embedder import BGEEmbedder
from src.providers.vectorstores.chroma_store import ChromaVectorStore
from src.utils.logger import logger


class HybridRetriever:

    def __init__(self):
        self.embedder = BGEEmbedder()
        self.vector_store = ChromaVectorStore()

    # ------------------------------------------------------------
    # Stable keyword scoring
    # ------------------------------------------------------------
    def _keyword_score(self, query: str, document: str) -> float:
        query_tokens = set(re.findall(r"\w+", query.lower()))
        doc_tokens = set(re.findall(r"\w+", document.lower()))

        if not query_tokens:
            return 0.0

        overlap = query_tokens.intersection(doc_tokens)
        return len(overlap) / len(query_tokens)

    def _exact_phrase_boost(self, query: str, document: str) -> float:
        if query.lower() in document.lower():
            return 0.3
        return 0.0

    def _file_name_boost(self, query: str, file_name: str) -> float:
        if not file_name:
            return 0.0

        base_name = file_name.lower().replace(".pdf", "")
        if base_name in query.lower():
            return 0.25

        return 0.0

    def _numbered_reference_boost(self, query: str, document: str) -> float:
        query_numbers = re.findall(r"\b\d+\b", query.lower())
        if not query_numbers:
            return 0.0

        doc_lower = document.lower()
        score = 0.0

        for number in query_numbers:
            if re.search(rf"\b{number}\b", doc_lower):
                score += 0.15

        return min(score, 0.3)

    def _structured_chunk_boost(self, document: str) -> float:
        colon_count = document.count(":")
        numeric_tokens = len(re.findall(r"\d+", document))

        score = 0.0

        if colon_count >= 3:
            score += 0.05

        if numeric_tokens >= 3:
            score += 0.05

        return min(score, 0.1)

    def _vision_chunk_boost(self, document: str) -> float:
        vision_markers = [
            "FULL_PAGE_VISION",
            "IMAGE_VISION",
            "CHART_TITLE",
            "DATA_POINTS",
            "X_AXIS_LABEL",
            "Y_AXIS_LABEL",
            "LEGEND",
        ]
        if any(marker in document for marker in vision_markers):
            return 0.15
        return 0.0

    # ------------------------------------------------------------
    # MAIN RETRIEVE METHOD
    # ------------------------------------------------------------
    def retrieve(self, query: str, k: int = 5):

        logger.info(f"Vector query (semantic embedding): '{query}'")

        # ---------------- EMBEDDING ----------------
        try:
            query_embedding = self.embedder.embed([query])[0]
        except Exception:
            logger.exception("Failed to embed query")
            return [], [], []

        # ---------------- VECTOR SEARCH ----------------
        CANDIDATE_MULTIPLIER = 4
        desired_n = k * CANDIDATE_MULTIPLIER

        try:
            collection_count = self.vector_store.count()
        except Exception:
            logger.warning("Could not fetch collection count. Defaulting candidate pool to k.")
            collection_count = k

        safe_n = max(1, min(desired_n, collection_count))

        logger.info(
            f"ChromaDB collection size: {collection_count} | "
            f"fetching top {safe_n} candidates for re-ranking"
        )

        try:
            results = self.vector_store.query(query_embedding, safe_n)
        except Exception:
            logger.exception("Vector store query failed")
            return [], [], []

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        if not documents:
            logger.warning("No results returned from vector store")
            return [], [], []

        # ---------------- HYBRID SCORING ----------------
        scored_results = []

        for doc, meta, dist in zip(documents, metadatas, distances):

            semantic_score = max(0, 1 - dist) if dist is not None else 0
            keyword_score = self._keyword_score(query, doc)
            phrase_boost = self._exact_phrase_boost(query, doc)
            file_boost = self._file_name_boost(query, meta.get("file_name", ""))
            number_boost = self._numbered_reference_boost(query, doc)
            structure_boost = self._structured_chunk_boost(doc)
            vision_boost = self._vision_chunk_boost(doc)

            final_score = (
                0.60 * semantic_score +
                0.25 * keyword_score +
                phrase_boost +
                file_boost +
                number_boost +
                structure_boost +
                vision_boost
            )

            scored_results.append((final_score, doc, meta))

        scored_results.sort(key=lambda x: x[0], reverse=True)
        top_results = scored_results[:k]

        final_docs = []
        final_metas = []
        final_scores = []

        for i, (final_score, doc, meta) in enumerate(top_results):
            logger.info(
                f"Hybrid hit {i + 1} | "
                f"file={meta.get('file_name')} | "
                f"chunk={meta.get('chunk_id')} | "
                f"final_score={final_score:.4f}"
            )

            final_docs.append(doc)
            final_metas.append(meta)
            final_scores.append(final_score)

        logger.info(f"Retrieved {len(final_docs)} chunks via hybrid search")

        return final_docs, final_metas, final_scores