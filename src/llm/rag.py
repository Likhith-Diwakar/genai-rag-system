# src/llm/rag.py

from src.providers.llm.groq_llm import GroqLLM
from src.providers.retrievers.hybrid_retriever import HybridRetriever
from src.utils.logger import logger


def generate_answer(query: str, k: int = 7):

    logger.info(f"RAG query received: {query}")

    # ✅ Use modular retriever
    retriever = HybridRetriever()
    documents, metadatas, scores = retriever.retrieve(query, k)

    if not documents:
        logger.warning("No documents retrieved from vector store.")
        return "I do not know based on the provided documents.", []

    combined = list(zip(documents, metadatas, scores))
    combined.sort(key=lambda x: x[2], reverse=True)

    # Structure-aware filtering
    structured_chunks = [
        item for item in combined
        if "TABLE_ROW_START" in item[0]
    ]

    if structured_chunks:
        logger.info("Structured table rows detected in retrieval. Prioritizing structured chunks.")
        combined = structured_chunks

    if not combined:
        logger.warning("No relevant chunks after filtering.")
        return "I do not know based on the provided documents.", []

    # Context control
    top_k = 5
    top_chunks = combined[:top_k]

    MAX_CONTEXT_CHARS = 5000

    context_parts = []
    current_length = 0

    for doc, meta, score in top_chunks:
        if current_length + len(doc) > MAX_CONTEXT_CHARS:
            break
        context_parts.append(doc)
        current_length += len(doc)

    context = "\n\n".join(context_parts)

    dominant_file_id = top_chunks[0][1].get("file_id")
    dominant_file_name = top_chunks[0][1].get("file_name", "UNKNOWN")

    logger.info(f"Top document contributing | file={dominant_file_name}")
    logger.info(f"Context length: {len(context)} chars from {len(context_parts)} chunk(s)")

    system_message = """
You are a document question answering system.

You must answer strictly using the provided context.

Instructions:
1. Always answer in a complete, natural sentence.
2. Match headers and values carefully.
3. Use only information present in the context.
4. Return exact numbers and percentages as written.
5. Do not combine rows unless explicitly asked.
6. Perform arithmetic only if explicitly requested.
7. Include units if present.
8. If the answer does not clearly appear in the context,
respond exactly with:
"I do not know based on the provided documents."
"""

    user_message = f"""
Context:
{context}

Question:
{query}

Answer in a complete sentence:
"""

    llm = GroqLLM()
    answer = llm.generate(system_message, user_message)

    if not answer.strip() or answer.strip() == "I do not know based on the provided documents.":
        logger.info("LLM could not find answer in provided context.")
        return "I do not know based on the provided documents.", []

    logger.info("LLM returned a grounded answer.")

    return answer, [
        {"file_id": dominant_file_id, "file_name": dominant_file_name}
    ]