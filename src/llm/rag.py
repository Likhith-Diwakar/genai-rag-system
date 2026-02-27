import os
import re
from dotenv import load_dotenv
from groq import Groq, RateLimitError
from src.llm.query import query_vector_store
from src.utils.logger import logger

load_dotenv()

PRIMARY_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found. Check your .env file.")

client = Groq(api_key=api_key)


# ==========================================================
# LLM CALLING LAYER
# ==========================================================

def call_groq(model: str, system_message: str, user_message: str) -> str:
    try:
        logger.info(f"Calling Groq | model={model}")

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            max_tokens=600,
        )

        return completion.choices[0].message.content.strip()

    except RateLimitError:
        logger.warning(f"Rate limit reached for model={model}")
        return ""

    except Exception as e:
        logger.error(f"Groq error for model={model}: {e}")
        return ""


def call_llm(system_message: str, user_message: str) -> str:
    answer = call_groq(PRIMARY_MODEL, system_message, user_message)

    if answer:
        return answer

    logger.info("Primary model unavailable. Falling back.")

    answer = call_groq(FALLBACK_MODEL, system_message, user_message)

    if answer:
        return answer

    return "I do not know based on the provided documents."


# ==========================================================
# MAIN RAG PIPELINE (ZERO DOMAIN HARDCODING)
# ==========================================================

def generate_answer(query: str, k: int = 7):

    logger.info(f"RAG query received: {query}")

    documents, metadatas, scores = query_vector_store(query, k=k)

    if not documents:
        logger.warning("No documents retrieved from vector store.")
        return "I do not know based on the provided documents.", []

    combined = list(zip(documents, metadatas, scores))
    combined.sort(key=lambda x: x[2], reverse=True)

    # ---------------------------------------------
    # STRUCTURE-AWARE FILTERING (NOT DOMAIN AWARE)
    # ---------------------------------------------
    #
    # If the highest-ranked chunks are structured rows,
    # prioritize structured chunks.
    # Otherwise use normal chunks.
    #
    # No keyword logic.
    # No entity narrowing.
    # No domain assumptions.
    #
    # ---------------------------------------------

    structured_chunks = [
        item for item in combined
        if "TABLE_ROW_START" in item[0]
    ]

    # If majority of top results are structured, prefer them
    if structured_chunks:
        logger.info("Structured table rows detected in retrieval. Prioritizing structured chunks.")
        combined = structured_chunks

    if not combined:
        logger.warning("No relevant chunks after filtering.")
        return "I do not know based on the provided documents.", []

    # ---------------------------------------------
    # Context control (token efficiency)
    # ---------------------------------------------

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

    # ---------------------------------------------
    # Prompt
    # ---------------------------------------------

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

    answer = call_llm(system_message, user_message)

    if not answer.strip() or answer.strip() == "I do not know based on the provided documents.":
        logger.info("LLM could not find answer in provided context.")
        return "I do not know based on the provided documents.", []

    logger.info("LLM returned a grounded answer.")

    return answer, [
        {"file_id": dominant_file_id, "file_name": dominant_file_name}
    ]