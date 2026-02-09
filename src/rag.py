# src/rag.py

import requests
import re
from collections import defaultdict
from src.query import query_vector_store
from src.logger import logger

# ------------------------------------------------------------------
# Ollama HTTP configuration (STABLE)
# ------------------------------------------------------------------
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:3b-instruct"
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
# Ollama HTTP call
# ------------------------------------------------------------------
def call_ollama(prompt: str) -> str:
    logger.info(f"Calling Ollama via HTTP | model={OLLAMA_MODEL}")

    payload = {
        "model": OLLAMA_MODEL,
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
        logger.exception("Ollama HTTP request failed")
        return "I do not know based on the provided documents."

    if resp.status_code != 200:
        logger.error(f"Ollama HTTP error: {resp.status_code}")
        return "I do not know based on the provided documents."

    data = resp.json()
    answer = clean_output(data.get("response", ""))

    if not answer:
        logger.warning("Ollama returned empty response")
        return "I do not know based on the provided documents."

    logger.info("Ollama response generated successfully")
    return answer


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
# SECTION-AWARE CONTEXT EXTRACTION (CORE FIX)
# ------------------------------------------------------------------
def extract_relevant_section(scored_chunks):
    """
    Groups chunks by detected section headers and returns
    ONLY the most relevant section.
    """
    section_scores = defaultdict(int)
    section_chunks = defaultdict(list)

    current_section = "UNKNOWN"

    for doc, meta, score in scored_chunks:
        lines = doc.splitlines()

        for line in lines:
            line = line.strip()
            # Heuristic for section headers
            if (
                len(line) >= 5
                and len(line.split()) <= 6
                and line[0].isupper()
            ):
                current_section = line

        section_scores[current_section] += score
        section_chunks[current_section].append(doc)

    best_section = max(section_scores, key=section_scores.get)

    return best_section, section_chunks[best_section]


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

    # 2️⃣ Keyword extraction (dominance only)
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

    # 5️⃣ SECTION-AWARE CONTEXT (🔥 THIS IS THE FIX)
    section_title, section_docs = extract_relevant_section(dominant_chunks)

    if not section_docs:
        logger.warning("No relevant section extracted")
        return "I do not know based on the provided documents.", []

    context = section_title + "\n\n" + "\n\n".join(section_docs)

    # 6️⃣ Structured, generic prompt (NO hard-coding)
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
- Do NOT merge content from different sections.

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
    q = "What are the rules for Robowars competition?"
    ans, srcs = generate_answer(q)

    print("\nANSWER:\n", ans)
    print("\nSOURCES:")
    for s in srcs:
        print(f"- {s['file_name']} ({s['file_id']})")
