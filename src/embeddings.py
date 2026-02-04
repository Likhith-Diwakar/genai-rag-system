import os
import logging

# ---- Silence HuggingFace / Transformers noise ----
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)

from openai import OpenAI
from openai import RateLimitError
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL = "text-embedding-3-small"

_local_model = None
OPENAI_FALLBACK_WARNED = False


def _get_local_model():

    global _local_model
    if _local_model is None:
        _local_model = SentenceTransformer(
            "all-MiniLM-L6-v2",
            device="cpu"
        )
    return _local_model


def embed_texts(texts: list[str]) -> list[list[float]]:

    global OPENAI_FALLBACK_WARNED

    api_key = os.getenv("OPENAI_API_KEY")

    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts
            )
            return [item.embedding for item in response.data]

        except RateLimitError:
            if not OPENAI_FALLBACK_WARNED:
                print(" OpenAI quota exceeded. Falling back to local embeddings.")
                OPENAI_FALLBACK_WARNED = True

        except Exception:
            if not OPENAI_FALLBACK_WARNED:
                print(" OpenAI error. Falling back to local embeddings.")
                OPENAI_FALLBACK_WARNED = True

    # ---- Local fallback (silent) ----
    model = _get_local_model()
    embeddings = model.encode(
        texts,
        show_progress_bar=False,
        convert_to_numpy=True
    )

    return embeddings.tolist()


if __name__ == "__main__":
    test_chunks = [
        "This is the first chunk of text.",
        "This is another chunk of text."
    ]

    vectors = embed_texts(test_chunks)
    print("Vectors:", len(vectors), "Dim:", len(vectors[0]))
