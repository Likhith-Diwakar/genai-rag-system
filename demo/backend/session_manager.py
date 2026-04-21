#Session Manager.py
import os
import hashlib
import math
import json
from datetime import datetime
from typing import Optional

from supabase import create_client, Client


# ==============================
# Supabase Init
# ==============================

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not set")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ==============================
# Utility
# ==============================

def _hash_query(query: str) -> str:
    return hashlib.sha256(query.strip().lower().encode()).hexdigest()


def _safe_json(val):
    if isinstance(val, str):
        try:
            return json.loads(val)
        except:
            return []
    return val or []


def _normalize_embedding(vec):
    if not vec:
        return None

    # If stored as string
    if isinstance(vec, str):
        try:
            vec = json.loads(vec)
        except:
            return None

    # Flatten nested lists
    if isinstance(vec, list) and len(vec) > 0 and isinstance(vec[0], list):
        vec = vec[0]

    # Ensure floats
    try:
        return [float(x) for x in vec]
    except:
        return None


def _embed_query(text: str) -> list:
    try:
        from src.providers.embeddings.bge_embedder import BGEEmbedder
        embedder = BGEEmbedder()
        vec = embedder.embed(text)
        return vec if isinstance(vec, list) else list(vec)
    except Exception:
        vec = [0.0] * 256
        text = text.lower()
        for i in range(len(text) - 1):
            idx = (ord(text[i]) ^ ord(text[i + 1])) % 256
            vec[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def _cosine_similarity(a: list, b: list) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


# ==============================
# Session
# ==============================

def get_or_create_session(session_id: str) -> dict:
    res = supabase.table("sessions").select("*").eq("session_id", session_id).execute()

    now = datetime.utcnow().isoformat()

    if res.data:
        supabase.table("sessions").update({
            "last_active": now
        }).eq("session_id", session_id).execute()
        return res.data[0]

    data = {
        "session_id": session_id,
        "created_at": now,
        "last_active": now,
        "message_count": 0,
    }

    supabase.table("sessions").insert(data).execute()
    return data


# ==============================
# Messages
# ==============================

def save_message(session_id: str, query: str, answer: str, sources: list):
    now = datetime.utcnow()

    msg = {
        "session_id": session_id,
        "query": query,
        "answer": answer,
        "sources": sources,
        "timestamp": now.isoformat(),
        "date_key": now.strftime("%Y-%m-%d"),
        "query_hash": _hash_query(query),
    }

    supabase.table("messages").insert(msg).execute()

    res = supabase.table("sessions").select("message_count").eq("session_id", session_id).execute()

    if res.data:
        count = res.data[0].get("message_count", 0)
        supabase.table("sessions").update({
            "message_count": count + 1,
            "last_active": now.isoformat()
        }).eq("session_id", session_id).execute()


def get_chat_history(session_id: str) -> dict:
    res = supabase.table("messages") \
        .select("*") \
        .eq("session_id", session_id) \
        .order("timestamp") \
        .execute()

    grouped = {}

    for d in res.data or []:
        date_key = d.get("date_key", "unknown")

        grouped.setdefault(date_key, []).append({
            "query": d.get("query", ""),
            "answer": d.get("answer", ""),
            "sources": _safe_json(d.get("sources")),
            "timestamp": d.get("timestamp", ""),
        })

    return dict(sorted(grouped.items(), reverse=True))


# ==============================
# Cache (SESSION LEVEL)
# ==============================

SEMANTIC_THRESHOLD = 0.88


def check_cache(session_id: str, query: str) -> Optional[dict]:
    query_hash = _hash_query(query)

    # Exact match
    res = supabase.table("cache") \
        .select("*") \
        .eq("session_id", session_id) \
        .eq("query_hash", query_hash) \
        .limit(1) \
        .execute()

    if res.data:
        entry = res.data[0]

        supabase.table("cache").update({
            "hit_count": entry.get("hit_count", 0) + 1
        }).eq("query_hash", query_hash).eq("session_id", session_id).execute()

        return {
            "answer": entry.get("answer"),
            "sources": _safe_json(entry.get("sources"))
        }

    # Semantic match
    try:
        query_embedding = _embed_query(query)

        all_entries = supabase.table("cache") \
            .select("*") \
            .eq("session_id", session_id) \
            .execute()

        best_score = 0.0
        best_entry = None

        for data in all_entries.data or []:
            emb = _normalize_embedding(data.get("query_embedding"))
            if not emb:
                continue

            score = _cosine_similarity(query_embedding, emb)

            if score > best_score:
                best_score = score
                best_entry = data

        if best_score >= SEMANTIC_THRESHOLD and best_entry:
            supabase.table("cache").update({
                "hit_count": best_entry.get("hit_count", 0) + 1
            }).eq("query_hash", best_entry.get("query_hash")) \
              .eq("session_id", session_id).execute()

            return {
                "answer": best_entry.get("answer"),
                "sources": _safe_json(best_entry.get("sources"))
            }

    except Exception as e:
        print(f"Semantic cache error: {e}")

    return None


def save_to_cache(session_id: str, query: str, answer: str, sources: list):
    query_hash = _hash_query(query)
    embedding = _embed_query(query)

    entry = {
        "query_hash": query_hash,
        "session_id": session_id,
        "query": query,
        "query_embedding": embedding,
        "answer": answer,
        "sources": sources,
        "hit_count": 0,
        "saved_at": datetime.utcnow().isoformat(),
    }

    supabase.table("cache").upsert(entry).execute()