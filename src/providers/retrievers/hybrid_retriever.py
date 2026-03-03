# src/providers/retrievers/hybrid_retriever.py

import re
from collections import defaultdict

from src.providers.embeddings.bge_embedder import BGEEmbedder
from src.providers.vectorstores.chroma_store import ChromaVectorStore
from src.providers.retrievers.bm25_retriever import BM25Retriever
from src.utils.logger import logger


class HybridRetriever:

    def __init__(self):
        self.embedder = BGEEmbedder()
        self.vector_store = ChromaVectorStore()
        self.bm25 = BM25Retriever()
        self.bm25.load()

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

    def _entity_density_boost(self, query: str, document: str) -> float:
        query_tokens = re.findall(r"\w+", query.lower())
        doc_lower = document.lower()

        meaningful_tokens = [
            t for t in query_tokens
            if len(t) >= 3 and not t.isdigit()
        ]

        if not meaningful_tokens:
            return 0.0

        matches = 0
        for token in meaningful_tokens:
            if re.search(rf"\b{re.escape(token)}\b", doc_lower):
                matches += 1

        density = matches / len(meaningful_tokens)

        return min(density * 0.20, 0.20)

    # ------------------------------------------------------------
    # Reciprocal Rank Fusion
    # ------------------------------------------------------------
    def _rrf_fusion(self, semantic_results, bm25_results, top_k, k_constant=60):
        """
        Standard Reciprocal Rank Fusion.
        RRF(doc) = Σ 1 / (k + rank)
        No score normalization required.
        """

        scores = defaultdict(float)
        chunk_lookup = {}

        # Semantic lane
        for rank, (doc, meta, _) in enumerate(semantic_results):
            chunk_key = f"{meta.get('file_id')}_{meta.get('chunk_id')}"
            scores[chunk_key] += 1.0 / (k_constant + rank + 1)
            chunk_lookup[chunk_key] = (doc, meta)

        # BM25 lane
        for rank, item in enumerate(bm25_results):
            doc = item["document"]
            meta = item["metadata"]
            chunk_key = f"{meta.get('file_id')}_{meta.get('chunk_id')}"
            scores[chunk_key] += 1.0 / (k_constant + rank + 1)
            chunk_lookup[chunk_key] = (doc, meta)

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        final_docs = []
        final_metas = []
        final_scores = []

        for chunk_key, score in ranked[:top_k]:
            doc, meta = chunk_lookup[chunk_key]
            final_docs.append(doc)
            final_metas.append(meta)
            final_scores.append(score)

        return final_docs, final_metas, final_scores

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
            f"fetching top {safe_n} candidates for semantic lane"
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

        # ---------------- SEMANTIC RE-RANK ----------------
        semantic_scored = []

        for doc, meta, dist in zip(documents, metadatas, distances):

            semantic_score = max(0, 1 - dist) if dist is not None else 0
            keyword_score = self._keyword_score(query, doc)
            phrase_boost = self._exact_phrase_boost(query, doc)
            file_boost = self._file_name_boost(query, meta.get("file_name", ""))
            number_boost = self._numbered_reference_boost(query, doc)
            structure_boost = self._structured_chunk_boost(doc)
            vision_boost = self._vision_chunk_boost(doc)
            entity_boost = self._entity_density_boost(query, doc)

            final_score = (
                0.55 * semantic_score +
                0.30 * keyword_score +
                phrase_boost +
                file_boost +
                number_boost +
                structure_boost +
                vision_boost +
                entity_boost
            )

            semantic_scored.append((doc, meta, final_score))

        semantic_scored.sort(key=lambda x: x[2], reverse=True)

        # ---------------- BM25 SPARSE LANE ----------------
        bm25_results = self.bm25.query(query, top_k=safe_n)

        # ---------------- RRF FUSION ----------------
        final_docs, final_metas, final_scores = self._rrf_fusion(
            semantic_scored,
            bm25_results,
            top_k=k
        )

        for i, (doc, meta, score) in enumerate(zip(final_docs, final_metas, final_scores)):
            logger.info(
                f"Hybrid hit {i + 1} | "
                f"file={meta.get('file_name')} | "
                f"chunk={meta.get('chunk_id')} | "
                f"rrf_score={score:.6f}"
            )

        logger.info(f"Retrieved {len(final_docs)} chunks via hybrid RRF search")

        return final_docs, final_metas, final_scores