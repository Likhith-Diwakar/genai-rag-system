import sys
import os

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.abspath(os.path.join(_backend_dir, "..", ".."))

for _path in [_backend_dir, _repo_root]:
    if _path not in sys.path:
        sys.path.insert(0, _path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from collections import defaultdict

try:
    from src.orchestration.langgraph_pipeline import run_pipeline
except Exception as e:
    run_pipeline = None
    print(f"Pipeline import error: {e}")

try:
    from scripts.restore_sqlite_from_drive import restore_sqlite_if_missing
except Exception as e:
    restore_sqlite_if_missing = None
    print(f"Restore import error: {e}")

# ── Session manager (Supabase) ───────────────────────────────────────────────
try:
    from session_manager import (
        get_or_create_session,
        save_message,
        get_chat_history,
        check_cache,
        save_to_cache,
    )
    SESSION_ENABLED = True
    print("Session manager loaded successfully")
except Exception as e:
    SESSION_ENABLED = False
    print(f"Session manager unavailable: {e}")

app = FastAPI()
INITIALIZED = False

# ── In-memory click store ─────────────────────────────────────────────────────
# Structure: { session_id: [ {file_id, file_name, url}, ... ] }
click_store: dict = defaultdict(list)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    global INITIALIZED
    if INITIALIZED:
        print("Already initialized, skipping...")
        return
    try:
        print("STARTUP INIT BEGIN")
        if restore_sqlite_if_missing:
            restore_sqlite_if_missing()
            print("SQLite restored successfully")
        INITIALIZED = True
        print("STARTUP INIT COMPLETE")
    except Exception as e:
        print(f"STARTUP ERROR: {str(e)}")


@app.get("/")
def root():
    return {"status": "Backend running"}


@app.get("/health")
def health():
    return {"status": "ok"}



PRELOADED_QA = {
    "what is generative ai": {
        "answer": "Generative AI is a type of artificial intelligence that uses neural networks and deep learning algorithms to generate new content such as text, images, audio, and video.",
        "source": "Generative-AI-and-LLMs-for-Dummies.pdf"
    },
    "what is retrieval-augmented generation": {
        "answer": "Retrieval-Augmented Generation (RAG) is a technique that combines a language model with a retrieval system to fetch relevant documents and generate more accurate responses.",
        "source": "Generative-AI-and-LLMs-for-Dummies.pdf"
    },
    "what does the no objection certificate state": {
        "answer": "The No Objection Certificate states that Mr. Likhith Diwakar is permitted to pursue an internship from January 2026 to July 2026.",
        "source": "No Objection Certificate .pdf"
    },
    "what is prompt engineering": {
        "answer": "Prompt engineering is the practice of designing and structuring input prompts to guide the output of a language model effectively.",
        "source": "Generative-AI-and-LLMs-for-Dummies.pdf"
    },
    "what is zero-shot prompting": {
        "answer": "Zero-shot prompting is when a model is asked to perform a task without any prior examples.",
        "source": "Generative-AI-and-LLMs-for-Dummies.pdf"
    },
    "what is few-shot prompting": {
        "answer": "Few-shot prompting involves providing a few examples to guide the model's response.",
        "source": "Generative-AI-and-LLMs-for-Dummies.pdf"
    },
    "what is in-context learning": {
        "answer": "In-context learning is when a model learns from examples provided within the prompt itself.",
        "source": "Generative-AI-and-LLMs-for-Dummies.pdf"
    }
}


# ==================================================
# MODELS
# ==================================================

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


class ClickPayload(BaseModel):
    session_id: str
    file_id: str = ""
    file_name: str = ""
    url: str = ""


# ==================================================
# HELPER — return only the top (most relevant) source
# ==================================================

def _normalise_sources(raw_sources: list) -> list:
    for meta in raw_sources:
        if not isinstance(meta, dict):
            continue
        name = meta.get("file_name") or meta.get("name") or ""
        file_id = meta.get("file_id") or ""
        if not name:
            continue
        url = f"https://drive.google.com/file/d/{file_id}/view" if file_id else ""
        return [{"name": name, "url": url}]
    return []


# ==================================================
# CHAT ENDPOINT
# ==================================================

@app.post("/chat")
def chat(request: QueryRequest):
    try:
        query_raw = request.query.strip()
        query_lower = query_raw.lower()
        session_id = request.session_id or "anonymous"

        if SESSION_ENABLED:
            try:
                get_or_create_session(session_id)
            except Exception as e:
                print(f"Session init warning: {e}")

        # Preloaded response
        if query_lower in PRELOADED_QA:
            data = PRELOADED_QA[query_lower]
            answer = data["answer"]
            sources = [{"name": data["source"], "url": ""}]
            if SESSION_ENABLED:
                try:
                    save_message(session_id, query_raw, answer, sources)
                except Exception as e:
                    print(f"Save message warning (preloaded): {e}")
            return {
                "response": answer,
                "sources": sources,
                "cache_hit": False,
                "session_id": session_id,
            }

        # Cache lookup
        if SESSION_ENABLED:
            try:
                cached = check_cache(session_id, query_raw)
                if cached and cached.get("answer"):
                    print(f"Cache hit for session={session_id} query='{query_raw[:60]}'")
                    sources = cached.get("sources", [])
                    if isinstance(sources, str):
                        import json
                        try:
                            sources = json.loads(sources)
                        except:
                            sources = []
                    if isinstance(sources, list) and len(sources) > 1:
                        sources = [sources[0]]
                    return {
                        "response": cached["answer"],
                        "sources": sources,
                        "cache_hit": True,
                        "session_id": session_id,
                    }
            except Exception as e:
                print(f"Cache lookup warning: {e}")

        # Normal pipeline
        if run_pipeline is None:
            return {
                "response": "Pipeline failed to load. Check backend logs.",
                "sources": [],
                "cache_hit": False,
                "session_id": session_id,
            }

        result = run_pipeline(query_raw)
        answer = None
        sources = []

        if isinstance(result, dict):
            answer = (
                result.get("answer")
                or result.get("final_answer")
                or result.get("response")
                or result.get("output")
                or result.get("result")
            )

            NO_ANSWER_TEXT = "I do not know based on the provided documents."
            CUSTOM_FALLBACK = (
                "I'm sorry, but I couldn't find relevant information in the indexed documents. "
                "Please try asking a more specific question related to the documents available "
                "in the connected Google Drive."
            )

            if answer and answer.strip() == NO_ANSWER_TEXT:
                return {
                    "response": CUSTOM_FALLBACK,
                    "sources": [],
                    "cache_hit": False,
                    "session_id": session_id,
                }

            raw_sources = result.get("sources", [])
            sources = _normalise_sources(raw_sources)
            final_answer = answer or "No response generated."

            if SESSION_ENABLED and final_answer != "No response generated.":
                try:
                    save_to_cache(session_id, query_raw, final_answer, sources)
                    save_message(session_id, query_raw, final_answer, sources)
                except Exception as e:
                    print(f"Post-pipeline save warning: {e}")

            return {
                "response": final_answer,
                "sources": sources,
                "cache_hit": False,
                "session_id": session_id,
            }

        return {
            "response": str(result),
            "sources": [],
            "cache_hit": False,
            "session_id": session_id,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "response": f"Backend error: {str(e)}",
            "sources": [],
            "cache_hit": False,
            "session_id": request.session_id or "anonymous",
        }


# ==================================================
# HISTORY ENDPOINT
# ==================================================

@app.get("/history")
def get_history(session_id: str):
    if not SESSION_ENABLED:
        return {
            "session_id": session_id,
            "history": {},
            "error": "Session storage not configured"
        }
    try:
        history = get_chat_history(session_id)
        return {"session_id": session_id, "history": history}
    except Exception as e:
        return {"session_id": session_id, "history": {}, "error": str(e)}


# ==================================================
 TRACK CLICK ENDPOINT
# POST /track_click
# Called silently when user clicks a source document
# ==================================================

@app.post("/track_click")
def track_click(payload: ClickPayload):
    """
    Tracks when a user explicitly opens a source document link.
    Stored in-memory per session_id.
    NOTE: Resets on server restart — use a DB for persistence.
    """
    if not payload.session_id or not payload.file_name:
        return {"status": "ignored"}

    click_store[payload.session_id].append({
        "file_id":   payload.file_id,
        "file_name": payload.file_name,
        "url":       payload.url,
    })

    print(f"[track_click] session={payload.session_id} file={payload.file_name}")
    return {"status": "tracked"}


# ==================================================
# SEARCH DOCS ENDPOINT
# GET /search_docs?q=<query>
# ==================================================

import sqlite3

_TRACKER_DB = os.path.join(_repo_root, "data", "tracker.db")


def _get_tracker_connection():
    """Returns a sqlite3 connection to tracker.db, or None if unavailable."""
    if not os.path.exists(_TRACKER_DB):
        fallback = os.path.join(_backend_dir, "data", "tracker.db")
        if os.path.exists(fallback):
            return sqlite3.connect(fallback)
        return None
    return sqlite3.connect(_TRACKER_DB)


@app.get("/search_docs")
def search_docs(q: str = ""):
    """
    Search indexed documents by file name.
    Matches file_name LIKE %q% (case-insensitive).
    Returns: [{file_name, file_id, url}]
    """
    if not q.strip():
        return []

    conn = _get_tracker_connection()
    if conn is None:
        return []

    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        tables = [row[0] for row in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        target_table = None
        for t in ["files", "documents", "tracker", "indexed_files"]:
            if t in tables:
                target_table = t
                break

        if target_table is None:
            return []

        cols = [row[1] for row in cursor.execute(f"PRAGMA table_info({target_table})").fetchall()]
        name_col = next((c for c in cols if "name" in c.lower() or "file" in c.lower()), cols[0] if cols else None)
        id_col   = next((c for c in cols if "id" in c.lower() and "file" in c.lower()), None)
        if id_col is None:
            id_col = next((c for c in cols if "id" in c.lower()), None)

        if name_col is None:
            return []

        rows = cursor.execute(
            f"SELECT * FROM {target_table} WHERE LOWER({name_col}) LIKE ? LIMIT 20",
            (f"%{q.lower()}%",)
        ).fetchall()

        results = []
        for row in rows:
            row_dict = dict(row)
            file_name = row_dict.get(name_col, "")
            file_id   = row_dict.get(id_col, "") if id_col else ""
            url = f"https://drive.google.com/file/d/{file_id}/view" if file_id else ""
            results.append({
                "file_name": file_name,
                "file_id":   file_id,
                "url":       url,
            })

        return results

    except Exception as e:
        print(f"/search_docs error: {e}")
        return []
    finally:
        conn.close()


# ==================================================
# DOCUMENTS ENDPOINT
# GET /documents
# ==================================================

@app.get("/documents")
def get_documents(limit: int = 10):
    """
    Returns the most recently indexed documents.
    Used by the Dashboard 'Latest Documents' card.
    Returns: [{file_name, file_id, url}]
    """
    conn = _get_tracker_connection()
    if conn is None:
        return []

    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        tables = [row[0] for row in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        target_table = None
        for t in ["files", "documents", "tracker", "indexed_files"]:
            if t in tables:
                target_table = t
                break

        if target_table is None:
            return []

        cols = [row[1] for row in cursor.execute(f"PRAGMA table_info({target_table})").fetchall()]
        name_col      = next((c for c in cols if "name" in c.lower()), cols[0] if cols else None)
        id_col        = next((c for c in cols if "id" in c.lower() and "file" in c.lower()), None)
        if id_col is None:
            id_col = next((c for c in cols if "id" in c.lower()), None)
        timestamp_col = next((c for c in cols if any(k in c.lower() for k in ["time", "date", "created", "indexed", "modified"])), None)

        if name_col is None:
            return []

        if timestamp_col:
            query = f"SELECT * FROM {target_table} ORDER BY {timestamp_col} DESC LIMIT ?"
        else:
            query = f"SELECT * FROM {target_table} ORDER BY rowid DESC LIMIT ?"

        rows = cursor.execute(query, (limit,)).fetchall()

        results = []
        for row in rows:
            row_dict  = dict(row)
            file_name = row_dict.get(name_col, "")
            file_id   = row_dict.get(id_col, "") if id_col else ""
            url = f"https://drive.google.com/file/d/{file_id}/view" if file_id else ""
            results.append({
                "file_name": file_name,
                "file_id":   file_id,
                "url":       url,
            })

        return results

    except Exception as e:
        print(f"/documents error: {e}")
        return []
    finally:
        conn.close()


# ==================================================
#  UPDATED: FREQUENT DOCS ENDPOINT
# GET /frequent_docs?session_id=<sid>
# Primary:      click_store  (explicit opens via /track_click)
# Supplementary: session chat history (so docs appear even before first click)
# Returns top 5 sorted by click count desc
# ==================================================

@app.get("/frequent_docs")
def get_frequent_docs(session_id: str):
    """
    Returns top 5 most-accessed documents for a session.
    Counts are driven by /track_click calls (explicit opens).
    Chat-history sources are included with count=0 as a fallback
    so they still appear in the dashboard before any clicks.
    """
    freq: dict = {}  # file_name → {count, file_id, url}

    # ── Source 1: explicit clicks (primary) ──────────────────────────────────
    for click in click_store.get(session_id, []):
        name = click.get("file_name", "")
        if not name:
            continue
        if name not in freq:
            freq[name] = {
                "count":   0,
                "file_id": click.get("file_id", ""),
                "url":     click.get("url", ""),
            }
        freq[name]["count"] += 1

    # ── Source 2: chat history sources (supplementary, no double-count) ──────
    if SESSION_ENABLED:
        try:
            history = get_chat_history(session_id)
            for date_msgs in history.values():
                for msg in date_msgs:
                    sources = msg.get("sources") or []
                    if isinstance(sources, str):
                        import json as _json
                        try:
                            sources = _json.loads(sources)
                        except Exception:
                            sources = []
                    for src in sources:
                        if not isinstance(src, dict):
                            continue
                        name = src.get("name") or src.get("file_name") or ""
                        if not name:
                            continue
                        # Only register if not already in freq (from click_store)
                        if name not in freq:
                            url = src.get("url") or ""
                            file_id = ""
                            if "/d/" in url:
                                parts = url.split("/d/")
                                if len(parts) > 1:
                                    file_id = parts[1].split("/")[0]
                            freq[name] = {
                                "count":   0,
                                "file_id": file_id,
                                "url":     url,
                            }
        except Exception as e:
            print(f"/frequent_docs history error: {e}")

    if not freq:
        return {"documents": []}

    # Sort by count desc, take top 5
    sorted_docs = sorted(freq.items(), key=lambda x: x[1]["count"], reverse=True)[:5]

    return {
        "documents": [
            {
                "file_name": name,
                "file_id":   data["file_id"],
                "url":       data["url"] or (
                    f"https://drive.google.com/file/d/{data['file_id']}/view"
                    if data["file_id"] else ""
                ),
                "count": data["count"],
            }
            for name, data in sorted_docs
        ]
    }
