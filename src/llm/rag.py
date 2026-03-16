# src/llm/rag.py

import re

from src.providers.llm.groq_llm import GroqLLM
from src.providers.llm.openrouter_llm import OpenRouterLLM
from src.providers.llm.gemini_llm import GeminiLLM

from src.providers.retrievers.hybrid_retriever import HybridRetriever
from src.llm.llm_router import route_llm

from src.utils.logger import logger


def generate_answer(query: str, k: int = 7):

    logger.info(f"RAG query received: {query}")

    retriever = HybridRetriever()
    documents, metadatas, scores = retriever.retrieve(query, k)

    if not documents:
        logger.warning("No documents retrieved from vector store.")
        return "I do not know based on the provided documents.", []

    combined = list(zip(documents, metadatas, scores))

    # ---------------------------------------------------------
    # Structured override (intent-aware)
    # ---------------------------------------------------------

    numeric_tokens = re.findall(r"\b\d+\b", query)
    table_keywords = {"table", "row", "column", "value", "percentage", "percent"}

    is_table_query = (
        bool(numeric_tokens)
        or any(word in query.lower() for word in table_keywords)
    )

    structured_chunks = [
        item for item in combined
        if "TABLE_ROW_START" in item[0]
    ]

    if is_table_query and structured_chunks:
        logger.info("Table-oriented query detected. Using structured prioritization.")
        combined = structured_chunks
    else:
        logger.info("Using semantic ranking without forced structured override.")

    if not combined:
        logger.warning("No relevant chunks after filtering.")
        return "I do not know based on the provided documents.", []

    # ---------------------------------------------------------
    # Lexical alignment boost (chunk-level)
    # ---------------------------------------------------------

    query_tokens = [
        token.lower()
        for token in re.findall(r"\b[a-zA-Z]{3,}\b", query)
    ]

    if query_tokens:
        boosted = []
        non_boosted = []

        for item in combined:
            doc_text = item[0].lower()
            match_count = sum(token in doc_text for token in query_tokens)

            if match_count > 0:
                boosted.append((match_count, item))
            else:
                non_boosted.append(item)

        boosted.sort(key=lambda x: (-x[0], -x[1][2]))
        combined = [item for _, item in boosted] + non_boosted

        logger.info("Applied lexical alignment re-ranking.")

    # ---------------------------------------------------------
    # GLOBAL TOP-K CONTEXT SELECTION
    # ---------------------------------------------------------

    combined.sort(key=lambda x: x[2], reverse=True)

    MAX_CONTEXT_CHARS = 5000
    GLOBAL_TOP_K = min(k, 7)

    selected_chunks = []
    current_length = 0
    seen_chunk_ids = set()

    for doc, meta, score in combined:

        if len(selected_chunks) >= GLOBAL_TOP_K:
            break

        chunk_id = meta.get("chunk_id")
        file_id = meta.get("file_id")

        chunk_key = f"{file_id}_{chunk_id}"

        if chunk_key in seen_chunk_ids:
            continue

        if current_length + len(doc) > MAX_CONTEXT_CHARS:
            continue

        selected_chunks.append((doc, meta, score))
        seen_chunk_ids.add(chunk_key)
        current_length += len(doc)

    if not selected_chunks:
        logger.warning("Context empty after global ranking.")
        return "I do not know based on the provided documents.", []

    context = "\n\n".join([doc for doc, _, _ in selected_chunks])

    logger.info(
        f"Context length: {len(context)} chars from {len(selected_chunks)} chunk(s)"
    )

    # ---------------------------------------------------------
    # LLM CALL
    # ---------------------------------------------------------

    system_message = """
You are a document question answering system.

You must answer strictly using the provided context.

Instructions:

1. Always answer in a complete, natural sentence unless the question explicitly asks for code.
2. Match headers and values carefully when dealing with structured data such as tables.
3. Use only information present in the provided context.
4. Return exact numbers, percentages, and values exactly as written in the context.
5. Do not combine rows or records unless the question explicitly requests aggregation.
6. Perform arithmetic only if the question explicitly asks for a calculation.

Code handling rules:

7. If the context contains a code snippet that answers the question, return that code exactly as it appears in the context.
8. If the context describes a programming task or algorithm but does not contain code, generate the code based strictly on the description present in the context.
9. Do not introduce libraries, algorithms, or implementation details that are not implied by the context.

Grounding rule:

10. If the answer cannot be derived from the provided context, respond exactly with:

"I do not know based on the provided documents."
"""

    user_message = f"""
Context:
{context}

Question:
{query}

Answer in a complete sentence:
"""

    # ---------------------------------------------------------
    # MODEL ROUTING
    # ---------------------------------------------------------

    model_name = route_llm(query)

    logger.info(f"Router selected model: {model_name}")

    if model_name == "groq":
        llm = GroqLLM()

    elif model_name == "gpt4o":
        llm = OpenRouterLLM("openai/gpt-4o-mini")

    elif model_name == "claude":
        llm = OpenRouterLLM("anthropic/claude-3-haiku")

    elif model_name == "gemini":
        llm = GeminiLLM()

    else:
        logger.warning("Router returned unknown model. Falling back to Groq.")
        llm = GroqLLM()

    answer = llm.generate(system_message, user_message)

    if (
        not answer.strip()
        or answer.strip()
        == "I do not know based on the provided documents."
    ):
        logger.info("LLM could not find answer in provided context.")
        return "I do not know based on the provided documents.", []

    logger.info("LLM returned a grounded answer.")

    # ---------------------------------------------------------
    # TRUE SOURCE DETECTION (QUERY-ALIGNED SOURCE)
    # ---------------------------------------------------------

    source_files = []
    query_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", query.lower()))

    best_match = None
    best_score = -1

    for doc, meta, _ in selected_chunks:
        doc_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", doc.lower()))
        overlap = len(query_tokens.intersection(doc_tokens))

        if overlap > best_score:
            best_score = overlap
            best_match = meta

    if best_match:
        source_files.append({
            "file_id": best_match.get("file_id"),
            "file_name": best_match.get("file_name", "UNKNOWN")
        })

    return answer, source_files