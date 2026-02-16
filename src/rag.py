# src/rag.py

import os
import re
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

from groq import Groq

from src.query import query_vector_store
from src.logger import logger
from src.csv_reasoner import answer_csv_query, detect_numeric_intent
from src.sqlite_store import SQLiteStore


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
            temperature=0,
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

def extract_query_terms(query: str) -> set:
    return {
        word.lower().strip("“”\"?,.")
        for word in query.split()
        if len(word) > 3
    }


def keyword_overlap_score(query_terms: set, text: str) -> int:
    text = text.lower()
    return sum(1 for term in query_terms if term in text)


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

    sqlite_store = SQLiteStore()

    query_lower = query.lower()
    query_terms = extract_query_terms(query)
    numeric_intent = detect_numeric_intent(query)

    # ==========================================================
    # 1️⃣ STRICT CSV FILE NAME OVERRIDE
    # ==========================================================

    csv_file = extract_csv_filename(query_lower)

    if csv_file:

        if sqlite_store.table_exists(csv_file):
            logger.info(f"Strict SQLite override triggered: {csv_file}")

            structured_answer = answer_csv_query(query, csv_file)

            if structured_answer:
                return structured_answer, [
                    {"file_id": None, "file_name": csv_file}
                ]

            return "I do not know based on the provided documents.", []

        else:
            logger.warning(f"CSV table not found in SQLite: {csv_file}")
            return "I do not know based on the provided documents.", []

    # ==========================================================
    # 2️⃣ GENERIC CSV PRIORITY MODE
    # ==========================================================

    if numeric_intent or "row" in query_lower or "record" in query_lower:

        best_csv = None
        best_score = 0

        for table in sqlite_store.list_tables():

            df = sqlite_store.load_dataframe(table)
            if df is None:
                continue

            column_text = " ".join(df.columns).lower()

            score = sum(1 for term in query_terms if term in column_text)

            if "row" in query_lower or "record" in query_lower:
                score += 2

            if score > best_score:
                best_score = score
                best_csv = table

        if best_csv and best_score > 0:

            structured_answer = answer_csv_query(query, best_csv)

            if structured_answer:
                return structured_answer, [
                    {"file_id": None, "file_name": best_csv}
                ]

            return "I do not know based on the provided documents.", []

    # ==========================================================
    # 3️⃣ NORMAL TEXT RAG FLOW (CHROMA)
    # ==========================================================

    documents, metadatas = query_vector_store(query, k)

    if not documents:
        return "I do not know based on the provided documents.", []

    doc_scores = defaultdict(int)
    doc_chunks = defaultdict(list)

    for doc, meta in zip(documents, metadatas):
        score = keyword_overlap_score(query_terms, doc)
        file_id = meta["file_id"]
        doc_scores[file_id] += score
        doc_chunks[file_id].append((doc, meta))

    dominant_file_id = max(doc_scores, key=doc_scores.get)
    dominant_chunks = doc_chunks[dominant_file_id]
    dominant_file_name = dominant_chunks[0][1]["file_name"]

    # ==========================================================
    # 🔥 SMART CONTEXT REDUCTION (NO HARDCODING)
    # ==========================================================

    scored_chunks = []

    for doc, meta in dominant_chunks:
        score = keyword_overlap_score(query_terms, doc)
        scored_chunks.append((score, doc))

    scored_chunks.sort(reverse=True, key=lambda x: x[0])

    # Keep top 3 relevant chunks only
    top_chunks = [doc for score, doc in scored_chunks[:3]]

    context = "\n\n".join(top_chunks)

    system_message = """
You are a strict factual Retrieval-Augmented Generation (RAG) assistant.

Rules:
1. Answer ONLY using the provided context.
2. Do NOT use external knowledge.
3. Do NOT guess or assume.
4. If the answer is not clearly present, respond EXACTLY with:
   "I do not know based on the provided documents."
5. Preserve structured sections and include descriptive details when relevant.
"""

    user_message = f"""
Context:
{context}

Question:
{query}
"""

    answer = call_llm(system_message, user_message)

    if answer.strip() == "I do not know based on the provided documents.":
        return answer, []

    return answer, [
        {"file_id": dominant_file_id, "file_name": dominant_file_name}
    ]
