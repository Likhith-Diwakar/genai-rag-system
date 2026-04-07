import os
import threading
from src.utils.logger import logger
from transformers import logging as hf_logging

hf_logging.set_verbosity_error()

# ----------------------------------------------------------
# Global model cache — loaded once, lazily, in a background
# thread so it never blocks the first request
# ----------------------------------------------------------

_model = None
_model_lock = threading.Lock()
_model_loading = False
_model_failed = False


def _load_model_background():
    """Load the cross-encoder in a background thread so startup
    and the first request are never blocked waiting for HuggingFace."""
    global _model, _model_loading, _model_failed

    try:
        logger.info("Loading CrossEncoder model in background...")
        from sentence_transformers import CrossEncoder

        model = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-6-v2",
            max_length=512
        )

        with _model_lock:
            _model = model
            _model_loading = False

        logger.info("CrossEncoder model loaded successfully")

    except Exception as e:
        logger.warning(f"CrossEncoder failed to load (reranking will be skipped): {e}")

        with _model_lock:
            _model_loading = False
            _model_failed = True


def _get_model():
    """Return model if loaded, None if still loading or failed."""
    global _model_loading

    with _model_lock:
        if _model is not None:
            return _model

        if _model_failed:
            return None

        # Kick off background load only once
        if not _model_loading:
            _model_loading = True
            t = threading.Thread(target=_load_model_background, daemon=True)
            t.start()

        return None  # Not ready yet — skip reranking this request


class CrossEncoderReranker:

    def __init__(self):
        # Trigger background model load immediately on first instantiation
        # so it's ready by the time real requests come in
        _get_model()

    def rerank(self, query, docs, metas, scores):
        """
        Rerank docs using cross-encoder if model is loaded.
        If model is still loading or failed, return original order —
        retrieval still works, just without reranking boost.
        """
        if not docs:
            return docs, metas, scores

        model = _get_model()

        if model is None:
            logger.info("CrossEncoder not ready yet — skipping rerank, using RRF order")
            return docs, metas, scores

        try:
            pairs = [(query, doc) for doc in docs]
            ce_scores = model.predict(pairs)

            combined = []
            for doc, meta, rrf_score, ce_score in zip(docs, metas, scores, ce_scores):
                final_score = (0.7 * float(ce_score)) + (0.3 * float(rrf_score))
                combined.append((doc, meta, final_score))

            combined.sort(key=lambda x: x[2], reverse=True)

            docs = [c[0] for c in combined]
            metas = [c[1] for c in combined]
            scores = [c[2] for c in combined]

            logger.info("Cross-encoder reranking applied")
            return docs, metas, scores

        except Exception as e:
            logger.warning(f"Cross-encoder reranking failed — using RRF order: {e}")
            return docs, metas, scores