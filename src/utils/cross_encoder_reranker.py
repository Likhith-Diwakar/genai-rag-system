import os
from dotenv import load_dotenv

load_dotenv()

os.environ["HF_TOKEN"] = os.getenv("HF_TOKEN")
from sentence_transformers import CrossEncoder
from src.utils.logger import logger
from transformers import logging
logging.set_verbosity_error()

class CrossEncoderReranker:

    def __init__(self):

        try:
            self.model = CrossEncoder(
                "cross-encoder/ms-marco-MiniLM-L-6-v2",
                max_length=512
            )
        except Exception:
            logger.exception("Failed to load CrossEncoder model")
            self.model = None

    def rerank(self, query, docs, metas, scores):

        if self.model is None:
            return docs, metas, scores

        try:

            pairs = [(query, doc) for doc in docs]

            ce_scores = self.model.predict(pairs)

            combined = []

            for doc, meta, rrf_score, ce_score in zip(docs, metas, scores, ce_scores):

                final_score = (0.7 * ce_score) + (0.3 * rrf_score)

                combined.append((doc, meta, final_score))

            combined.sort(key=lambda x: x[2], reverse=True)

            docs = [c[0] for c in combined]
            metas = [c[1] for c in combined]
            scores = [c[2] for c in combined]

            logger.info("Cross-encoder reranking applied")

            return docs, metas, scores

        except Exception:

            logger.exception("Cross encoder reranking failed")

            return docs, metas, scores