# src/query.py

from src.embedding.embeddings import embed_texts
from src.embedding.vector_store import VectorStore
from src.utils.logger import logger


def query_vector_store(query: str, k: int = 5):
    logger.info(f"Vector query (semantic embedding): '{query}'")

    store = VectorStore()

    # ---------------- EMBED QUERY ----------------
    try:
        query_embedding = embed_texts([query])[0]
    except Exception:
        logger.exception("Failed to embed query")
        return [], []

    # ---------------- VECTOR SEARCH ----------------
    try:
        results = store.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )
    except Exception:
        logger.exception("Vector store query failed")
        return [], []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not documents:
        logger.warning("No results returned from vector store")
        return [], []

    # ---------------- LOG RESULTS ----------------
    for i, (meta, dist) in enumerate(zip(metadatas, distances)):
        file_name = meta.get("file_name", "UNKNOWN")
        chunk_id = meta.get("chunk_id", "UNKNOWN")

        # Convert distance to similarity score (if cosine distance)
        similarity = 1 - dist if dist is not None else None

        logger.info(
            f"Semantic hit {i + 1} | "
            f"file={file_name} | "
            f"chunk={chunk_id} | "
            f"distance={dist:.4f} | "
            f"similarity={similarity:.4f}"
        )

    logger.info(f"Retrieved {len(documents)} chunks via semantic search")

    return documents, metadatas
