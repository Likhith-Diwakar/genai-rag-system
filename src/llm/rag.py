# src/rag.py

import os
import re
from dotenv import load_dotenv
load_dotenv()

from groq import Groq
from src.llm.query import query_vector_store
from src.utils.logger import logger


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
            max_tokens=1500,
        )

        return completion.choices[0].message.content.strip()

    except Exception:
        logger.exception(f"Groq call failed | model={model}")
        return ""


def call_llm(system_message: str, user_message: str) -> str:
    answer = call_groq(PRIMARY_MODEL, system_message, user_message)

    if answer:
        return answer

    logger.warning("Primary model failed. Falling back.")

    answer = call_groq(FALLBACK_MODEL, system_message, user_message)

    if answer:
        return answer

    return "I do not know based on the provided documents."


# ==========================================================
# HELPERS
# ==========================================================

def extract_csv_filename(query: str):
    match = re.search(r'([a-zA-Z0-9_\-]+\.csv)', query.lower())
    if match:
        return match.group(1)
    return None


def normalize_table_name(file_name: str):
    return file_name.replace(".", "_").replace(" ", "_").lower()


# ==========================================================
# MAIN RAG PIPELINE
# ==========================================================

def generate_answer(query: str, k: int = 5):

    logger.info(f"RAG query received: {query}")

    # 🔥 Increased retrieval window for better recall
    documents, metadatas, scores = query_vector_store(query, k=40)

    if not documents:
        logger.warning("No documents retrieved from vector store.")
        return "I do not know based on the provided documents.", []

    # ==========================================================
    # DOMINANT DOCUMENT SELECTION
    # ==========================================================

    highest_chunk_index = max(
        range(len(scores)),
        key=lambda i: scores[i]
    )

    dominant_file_id = metadatas[highest_chunk_index].get("file_id")

    if not dominant_file_id:
        logger.warning("Unable to determine dominant document.")
        return "I do not know based on the provided documents.", []

    dominant_file_name = metadatas[highest_chunk_index].get(
        "file_name", "UNKNOWN"
    )

    logger.info(
        f"Dominant document selected | file={dominant_file_name}"
    )

    # Collect chunks only from dominant file
    dominant_chunks = [
        (doc, meta, score)
        for doc, meta, score in zip(documents, metadatas, scores)
        if meta.get("file_id") == dominant_file_id
    ]

    # Sort by similarity score
    dominant_chunks.sort(key=lambda x: x[2], reverse=True)

    # Use top 8 chunks from dominant file
    top_chunks = dominant_chunks[:8]

    context = "\n\n".join([doc for doc, meta, score in top_chunks])

    # ==========================================================
    # TABLE-AWARE PROMPT
    # ==========================================================

    system_message = """
You are a factual Retrieval-Augmented Generation (RAG) assistant.

Instructions:
1. Use ONLY the provided context.
2. The context may contain structured data such as markdown tables.
3. You may interpret tables by matching headers with row values.
4. If multiple rows match the question, extract all relevant rows.
5. When answering numeric questions, return the exact numbers as written.
6. You may summarize structured or tabular data if clearly present.
7. Do NOT use external knowledge.
8. If the answer truly does not appear in the context, respond exactly with:
   "I do not know based on the provided documents."
"""

    user_message = f"""
Context:
{context}

Question:
{query}
"""

    answer = call_llm(system_message, user_message)

    if answer.strip() == "I do not know based on the provided documents.":
        logger.info("LLM returned strict unknown response.")
        return answer, []

    return answer, [
        {"file_id": dominant_file_id, "file_name": dominant_file_name}
    ]