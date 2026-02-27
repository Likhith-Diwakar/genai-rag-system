from abc import ABC, abstractmethod
from typing import Any


class BaseVectorStore(ABC):

    @abstractmethod
    def query(self, embedding: list, n_results: int) -> Any:
        pass

    @abstractmethod
    def count(self) -> int:
        pass

    @abstractmethod
    def add_chunks(self, embeddings, documents, metadatas, ids):
        pass

    @abstractmethod
    def delete_by_file_id(self, file_id: str):
        pass