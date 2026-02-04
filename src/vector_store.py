import chromadb
from chromadb.config import Settings

CHROMA_DIR = "data/chroma"


class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=CHROMA_DIR,
            settings=Settings(
                anonymized_telemetry=False
            )
        )

        self.collection = self.client.get_or_create_collection(
            name="drive_docs"
        )

    def add_chunks(
        self,
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
        ids: list[str],
    ):
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def query(self, query_embedding: list[float], n_results: int = 5):
        return self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

    def delete_by_file_id(self, file_id: str):
        self.collection.delete(
            where={"file_id": file_id}
        )

    def count(self):
        return self.collection.count()
