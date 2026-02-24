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
            max_tokens=1200,
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

    # Smaller retrieval window (faster + cleaner)
    documents, metadatas, scores = query_vector_store(query, k=15)

    if not documents:
        logger.warning("No documents retrieved from vector store.")
        return "I do not know based on the provided documents.", []

    # ==========================================================
    # SORT BY SCORE
    # ==========================================================

    combined = list(zip(documents, metadatas, scores))
    combined.sort(key=lambda x: x[2], reverse=True)

    # Smaller context window (reduces noise)
    top_k = 8
    top_chunks = combined[:top_k]

    context = "\n\n".join([doc for doc, meta, score in top_chunks])

    dominant_file_id = top_chunks[0][1].get("file_id")
    dominant_file_name = top_chunks[0][1].get("file_name", "UNKNOWN")

    logger.info(f"Top document contributing | file={dominant_file_name}")

    # ==========================================================
    # PROMPT
    # ==========================================================

    system_message = """
You are a document question answering system.

You must answer strictly using the provided context.

Instructions:
1. The context may contain normal text, structured tables, or numeric data.
2. Carefully match headers with values when tables are present.
3. Return exact numbers exactly as written.
4. Return exact percentages exactly as written.
5. If multiple values match, list them clearly.
6. Perform arithmetic only if explicitly required.
7. Do not hallucinate or use external knowledge.
8. If the answer truly does not appear in the context,
   respond exactly with:
   "I do not know based on the provided documents."
"""

    user_message = f"""
Context:
{context}

Question:
{query}

Answer:
"""

    answer = call_llm(system_message, user_message)

    if answer.strip() == "I do not know based on the provided documents.":
        logger.info("Model returned unknown response.")
        return answer, []

    return answer, [
        {"file_id": dominant_file_id, "file_name": dominant_file_name}
    ]