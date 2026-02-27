from typing import List
from src.interfaces.base_embedder import BaseEmbedder
from src.embedding.embeddings import embed_texts


class BGEEmbedder(BaseEmbedder):

    def embed(self, texts: List[str]) -> List[List[float]]:
        return embed_texts(texts)