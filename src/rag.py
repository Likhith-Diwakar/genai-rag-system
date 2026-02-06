# src/rag.py

import subprocess
from collections import defaultdict
from src.query import query_vector_store
from src.logger import logger

OLLAMA_PATH = r"C:\Users\Admin\AppData\Local\Programs\Ollama\ollama.exe"
OLLAMA_MODEL = "mistral"


def call_ollama(prompt: str) -> str:
    logger.info("Calling Ollama LLM")

    result = subprocess.run(
        [
            OLLAMA_PATH,
            "run",
            OLLAMA_MODEL,
            "-p",
            prompt
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=120
    )

    output = result.stdout.strip()

    if not output:
        logger.warning("Ollama returned empty output")
        return "I do not know based on the provided documents."

    return output


def extract_query_terms(query: str) -> set:
    return {
        word.lower().strip("“”\"?,.")
        for word in query.split()
        if len(word) > 3
    }


def keyword_overlap_score(query_terms: set, text: str) -> int:
    text = text.lower()
    return sum(1 for term in query_terms if term in text)


def generate_answer(query: str, k: int = 5):
    logger.info(f"RAG query received: {query}")

    # 1️⃣ Retrieve top-k chunks
    documents, metadatas = query_vector_store(query, k)

    if not documents or not metadatas:
        logger.warning("No chunks retrieved from vector store")
        return "I do not know based on the provided documents.", []

    # 2️⃣ Extract query keywords
    query_terms = extract_query_terms(query)
    logger.info(f"Extracted query terms: {query_terms}")

    # 3️⃣ Score chunks per document
    doc_scores = defaultdict(int)
    doc_chunks = defaultdict(list)

    for doc, meta in zip(documents, metadatas):
        score = keyword_overlap_score(query_terms, doc)

        file_id = meta["file_id"]
        doc_scores[file_id] += score
        doc_chunks[file_id].append((doc, meta, score))

    # 4️⃣ Select dominant document
    dominant_file_id = max(doc_scores, key=doc_scores.get)

    if doc_scores[dominant_file_id] == 0:
        logger.warning("No keyword overlap in any document")
        return "I do not know based on the provided documents.", []

    dominant_chunks = doc_chunks[dominant_file_id]
    dominant_file_name = dominant_chunks[0][1]["file_name"]

    logger.info(
        f"Selected dominant document: {dominant_file_name} ({dominant_file_id})"
    )

    # 5️⃣ Build context from dominant document ONLY
    context_blocks = []

    for doc, meta, score in dominant_chunks:
        if score == 0:
            continue

        context_blocks.append(
            f"[Source: {meta['file_name']} | Chunk {meta['chunk_id']}]\n{doc}"
        )

    if not context_blocks:
        logger.warning("No usable chunks after dominance filtering")
        return "I do not know based on the provided documents.", []

    context = "\n\n".join(context_blocks)

    # 6️⃣ Grounded prompt
    prompt = f"""
You are a factual assistant.

Rules:
- Answer ONLY using the provided context.
- Do NOT combine information from different documents.
- Do NOT guess or infer.
- If the answer is not explicitly stated, reply exactly:
  "I do not know based on the provided documents."

Context:
{context}

Question:
{query}

Answer clearly and concisely.
"""

    answer = call_ollama(prompt)

    sources = [
        {
            "file_id": dominant_file_id,
            "file_name": dominant_file_name
        }
    ]

    return answer, sources


if __name__ == "__main__":
    q = "What are the rules for the Robowars competition?"
    ans, srcs = generate_answer(q)

    print("\nANSWER:\n", ans)
    print("\nSOURCES:")
    for s in srcs:
        print(f"- {s['file_name']} ({s['file_id']})")
