from src.embeddings import embed_texts
from src.vector_store import VectorStore
from src.logger import logger


def query_vector_store(query: str, k: int = 5):
    logger.info(f"Vector query: '{query}'")

    store = VectorStore()
    query_embedding = embed_texts([query])[0]

    results = store.collection.query(
        query_embeddings=[query_embedding],
        n_results=k
    )

    logger.debug(f"Raw retrieval result keys: {results.keys()}")

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    logger.info(f"Retrieved {len(documents)} chunks")

    return documents, metadatas