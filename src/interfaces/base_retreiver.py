from abc import ABC, abstractmethod
from typing import List, Tuple

class BaseRetriever(ABC):

    @abstractmethod
    def retrieve(self, query: str, k: int) -> Tuple[List[str], List[dict], List[float]]:
        pass