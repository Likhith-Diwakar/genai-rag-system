# src/rag.py

import requests
import re
from collections import defaultdict
from src.query import query_vector_store
from src.logger import logger

# ------------------------------------------------------------------
# Ollama HTTP configuration (PRIMARY + FALLBACK)
# ------------------------------------------------------------------
OLLAMA_URL = "http://localhost:11434/api/generate"
PRIMARY_MODEL = "qwen2.5:3b-instruct"
FALLBACK_MODEL = "tinyllama"
TIMEOUT = 120


# ------------------------------------------------------------------
# Utility: strip ANSI / junk characters
# ------------------------------------------------------------------
ANSI_ESCAPE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def clean_output(text: str) -> str:
    if not text:
        return ""
    return ANSI_ESCAPE.sub("", text).strip()


# ------------------------------------------------------------------
# Ollama HTTP call (with fallback)
# ------------------------------------------------------------------
def _run_ollama(model: str, prompt: str) -> str:
    logger.info(f"Calling Ollama via HTTP | model={model}")

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        resp = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=TIMEOUT,
        )
    except Exception:
        logger.exception(f"Ollama HTTP request failed | model={model}")
        return ""

    if resp.status_code != 200:
        logger.error(f"Ollama HTTP error | model={model} | status={resp.status_code}")
        return ""

    data = resp.json()
    answer = clean_output(data.get("response", ""))

    if not answer:
        logger.warning(f"Ollama returned empty response | model={model}")
        return ""

    logger.info(f"Ollama response generated successfully | model={model}")
    return answer


def call_ollama(prompt: str) -> str:
    answer = _run_ollama(PRIMARY_MODEL, prompt)
    if answer:
        return answer

    logger.warning("Primary model failed, falling back to backup model")
    answer = _run_ollama(FALLBACK_MODEL, prompt)
    if answer:
        return answer

    logger.error("All Ollama models failed")
    return "I do not know based on the provided documents."


# ------------------------------------------------------------------
# Keyword helpers (ONLY for dominance, NOT retrieval)
# ------------------------------------------------------------------
def extract_query_terms(query: str) -> set:
    return {
        word.lower().strip("“”\"?,.")
        for word in query.split()
        if len(word) > 3
    }


def keyword_overlap_score(query_terms: set, text: str) -> int:
    text = text.lower()
    return sum(1 for term in query_terms if term in text)


# ------------------------------------------------------------------
# SECTION-AWARE CONTEXT EXTRACTION (FIXED)
# ------------------------------------------------------------------
def extract_relevant_sections(scored_chunks, max_sections: int = 2):
    """
    Groups chunks by detected section headers.
    Supports:
    - Short headers (e.g., "Preamble")
    - Long question headers (e.g., "What happens if ...?")
    """

    section_scores = defaultdict(int)
    section_chunks = defaultdict(list)

    current_section = "UNKNOWN"

    for doc, meta, score in scored_chunks:
        lines = doc.splitlines()

        for line in lines:
            line = line.strip()

            if (
                len(line) >= 5
                and line[0].isupper()
                and (
                    line.endswith("?")           # FIX: allow question headers
                    or len(line.split()) <= 10   # keep short-title heuristic
                )
            ):
                current_section = line

        section_scores[current_section] += score
        section_chunks[current_section].append(doc)

    ranked_sections = sorted(
        section_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    selected_sections = []
    for section, score in ranked_sections:
        if score <= 0:
            continue
        selected_sections.append((section, section_chunks[section]))
        if len(selected_sections) >= max_sections:
            break

    return selected_sections


# ------------------------------------------------------------------
# Main RAG pipeline
# ------------------------------------------------------------------
def generate_answer(query: str, k: int = 5):
    logger.info(f"RAG query received: {query}")

    # 1️⃣ Semantic retrieval
    documents, metadatas = query_vector_store(query, k)

    if not documents or not metadatas:
        logger.warning("No chunks retrieved from vector store")
        return "I do not know based on the provided documents.", []

    logger.info(
        "Semantic retrieval completed. "
        "Keyword scoring will be used ONLY for dominant document selection."
    )

    # 2️⃣ Keyword extraction (dominance only)
    query_terms = extract_query_terms(query)
    logger.info(f"Extracted query terms (dominance only): {query_terms}")

    # 3️⃣ Score chunks per document
    doc_scores = defaultdict(int)
    doc_chunks = defaultdict(list)

    for doc, meta in zip(documents, metadatas):
        score = keyword_overlap_score(query_terms, doc)
        file_id = meta["file_id"]

        doc_scores[file_id] += score
        doc_chunks[file_id].append((doc, meta, score))

    # 4️⃣ Dominant document selection
    dominant_file_id = max(doc_scores, key=doc_scores.get)

    if doc_scores[dominant_file_id] == 0:
        logger.warning("No keyword overlap in any document")
        return "I do not know based on the provided documents.", []

    dominant_chunks = doc_chunks[dominant_file_id]
    dominant_file_name = dominant_chunks[0][1]["file_name"]

    logger.info(
        f"Selected dominant document: {dominant_file_name} ({dominant_file_id})"
    )

    # 5️⃣ Section-aware context
    selected_sections = extract_relevant_sections(dominant_chunks)

    if not selected_sections:
        logger.warning("No relevant sections extracted")
        return "I do not know based on the provided documents.", []

    context_blocks = []
    for section_title, section_docs in selected_sections:
        block = section_title + "\n\n" + "\n\n".join(section_docs)
        context_blocks.append(block)

    context = "\n\n".join(context_blocks)

    # 6️⃣ Grounded prompt
    prompt = f"""
You are a factual assistant answering questions using structured documents.

Instructions:
- Use ONLY the information present in the context.
- Identify the section that answers the question.
- Use the section title as the heading.
- Preserve original terminology and structure.
- Present the answer as labeled points or bullet-style lines.
- Do NOT summarize or generalize.
- Do NOT add new information.
- Do NOT merge content from different documents.

If the answer cannot be derived, reply exactly:
"I do not know based on the provided documents."

Context:
{context}

Question:
{query}

Answer:
"""

    answer = call_ollama(prompt)

    sources = [
        {
            "file_id": dominant_file_id,
            "file_name": dominant_file_name,
        }
    ]

    return answer, sources


# ------------------------------------------------------------------
# Local test
# ------------------------------------------------------------------
if __name__ == "__main__":
    q = "What happens if an athlete or participant fails to respect these policies?"
    ans, srcs = generate_answer(q)

    print("\nANSWER:\n", ans)
    print("\nSOURCES:")
    for s in srcs:
        print(f"- {s['file_name']} ({s['file_id']})")
