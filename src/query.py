from src.embeddings import embed_texts
from src.vector_store import VectorStore


def query_vector_store(query: str, k: int = 5):

    # Load vector store (persistent Chroma DB)
    store = VectorStore()

    # Embed the query
    query_embedding = embed_texts([query])[0]

    # Perform semantic search
    results = store.collection.query(
        query_embeddings=[query_embedding],
        n_results=k
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    return documents, metadatas


if __name__ == "__main__":
    # Simple local test
    query = "What is the capstone project about?"

    docs, metas = query_vector_store(query, k=5)

    print("\nTop results:\n")
    for i, (doc, meta) in enumerate(zip(docs, metas)):
        print(f"--- Result {i + 1} ---")
        print(f"Source file_id: {meta.get('file_id')}")
        print(doc[:500])  # truncate for readability
        print()
