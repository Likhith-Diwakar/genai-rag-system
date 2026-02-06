# src/embeddings.py
from typing import List
from sentence_transformers import SentenceTransformer
from src.logger import logger

MODEL_NAME = "BAAI/bge-m3"
_model = None


def _load_model():
    global _model
    if _model is None:
        logger.info("Loading BGE-M3 embedding model")
        _model = SentenceTransformer(
            MODEL_NAME,
            trust_remote_code=True
        )
        logger.info("BGE-M3 loaded successfully")
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        logger.warning("No texts received for embedding")
        return []

    logger.info(f"Embedding {len(texts)} chunks")
    model = _load_model()

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    logger.debug(f"Embedding dimension = {len(embeddings[0])}")
    return embeddings.tolist()
