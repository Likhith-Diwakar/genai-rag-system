from src.interfaces.base_vector_store import BaseVectorStore
from src.embedding.vector_store import VectorStore


class ChromaVectorStore(BaseVectorStore):

    def __init__(self):
        self.store = VectorStore()
        self.collection = self.store.collection

    def query(self, embedding: list, n_results: int):
        return self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"]
        )

    def count(self) -> int:
        return self.collection.count()

    def add_chunks(self, embeddings, documents, metadatas, ids):
        self.store.add_chunks(embeddings, documents, metadatas, ids)

    def delete_by_file_id(self, file_id: str):
        self.store.delete_by_file_id(file_id)