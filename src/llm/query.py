# src/llm/query.py

import re
from src.embedding.embeddings import embed_texts
from src.embedding.vector_store import VectorStore
from src.utils.logger import logger


def _keyword_score(query: str, document: str) -> float:
    query_tokens = set(re.findall(r"\w+", query.lower()))
    doc_tokens = set(re.findall(r"\w+", document.lower()))

    if not query_tokens:
        return 0.0

    overlap = query_tokens.intersection(doc_tokens)
    return len(overlap) / len(query_tokens)


def _exact_phrase_boost(query: str, document: str) -> float:
    if query.lower() in document.lower():
        return 0.3
    return 0.0


def _file_name_boost(query: str, file_name: str) -> float:
    if not file_name:
        return 0.0
    if file_name.lower().replace(".pdf", "") in query.lower():
        return 0.25
    return 0.0


def query_vector_store(query: str, k: int = 5):
    logger.info(f"Vector query (semantic embedding): '{query}'")

    store = VectorStore()

    # ---------------- EMBEDDING ----------------
    try:
        query_embedding = embed_texts([query])[0]
    except Exception:
        logger.exception("Failed to embed query")
        return [], [], []

    # ---------------- VECTOR SEARCH ----------------
    try:
        results = store.collection.query(
            query_embeddings=[query_embedding],
            n_results=30,  # slightly higher pool
            include=["documents", "metadatas", "distances"]
        )
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
        keyword_boost = _keyword_score(query, doc)
        phrase_boost = _exact_phrase_boost(query, doc)
        file_boost = _file_name_boost(query, meta.get("file_name", ""))

        final_score = (
            0.80 * semantic_score +
            0.15 * keyword_boost +
            phrase_boost +
            file_boost
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