import sys
import os

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root   = os.path.abspath(os.path.join(_backend_dir, "..", ".."))

for _path in [_backend_dir, _repo_root]:
    if _path not in sys.path:
        sys.path.insert(0, _path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

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
        get_all_recent_activity,
        get_all_frequent_docs,
    )
    SESSION_ENABLED = True
    print("Session manager loaded successfully")
except Exception as e:
    SESSION_ENABLED = False
    print(f"Session manager unavailable: {e}")

app = FastAPI()
INITIALIZED = False

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


# ==================================================
# MODELS
# ==================================================

class QueryRequest(BaseModel):
    query:      str
    session_id: Optional[str] = None


class ClickPayload(BaseModel):
    session_id: str
    file_id:    str = ""
    file_name:  str = ""
    url:        str = ""


# ==================================================
# HELPER — return only the top (most relevant) source
# ==================================================

def _normalise_sources(raw_sources: list) -> list:
    for meta in raw_sources:
        if not isinstance(meta, dict):
            continue
        name    = meta.get("file_name") or meta.get("name") or ""
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
        query_raw  = request.query.strip()
        session_id = request.session_id or "anonymous"

        if SESSION_ENABLED:
            try:
                get_or_create_session(session_id)
            except Exception as e:
                print(f"Session init warning: {e}")

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
                        except Exception:
                            sources = []
                    if isinstance(sources, list) and len(sources) > 1:
                        sources = [sources[0]]
                    return {
                        "response":   cached["answer"],
                        "sources":    sources,
                        "cache_hit":  True,
                        "session_id": session_id,
                    }
            except Exception as e:
                print(f"Cache lookup warning: {e}")

        # Normal pipeline
        if run_pipeline is None:
            return {
                "response":   "Pipeline failed to load. Check backend logs.",
                "sources":    [],
                "cache_hit":  False,
                "session_id": session_id,
            }

        result  = run_pipeline(query_raw)
        answer  = None
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
                    "response":   CUSTOM_FALLBACK,
                    "sources":    [],
                    "cache_hit":  False,
                    "session_id": session_id,
                }

            raw_sources  = result.get("sources", [])
            sources      = _normalise_sources(raw_sources)
            final_answer = answer or "No response generated."

            if SESSION_ENABLED and final_answer != "No response generated.":
                try:
                    save_to_cache(session_id, query_raw, final_answer, sources)
                    save_message(session_id, query_raw, final_answer, sources)
                except Exception as e:
                    print(f"Post-pipeline save warning: {e}")

            return {
                "response":   final_answer,
                "sources":    sources,
                "cache_hit":  False,
                "session_id": session_id,
            }

        return {
            "response":   str(result),
            "sources":    [],
            "cache_hit":  False,
            "session_id": session_id,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "response":   f"Backend error: {str(e)}",
            "sources":    [],
            "cache_hit":  False,
            "session_id": request.session_id or "anonymous",
        }


# ==================================================
# HISTORY ENDPOINT  (session-specific — used by ChatOverlay)
# GET /history?session_id=<sid>
# ==================================================

@app.get("/history")
def get_history(session_id: str):
    if not SESSION_ENABLED:
        return {
            "session_id": session_id,
            "history":    {},
            "error":      "Session storage not configured"
        }
    try:
        history = get_chat_history(session_id)
        return {"session_id": session_id, "history": history}
    except Exception as e:
        return {"session_id": session_id, "history": {}, "error": str(e)}


# ==================================================
# TRACK CLICK ENDPOINT
# POST /track_click
# Saves an explicit doc-open event to Supabase
# so clicks persist across server restarts and are
# visible globally in the Frequently Visited card.
# ==================================================

@app.post("/track_click")
def track_click(payload: ClickPayload):
    if not payload.session_id or not payload.file_name:
        return {"status": "ignored"}

    if SESSION_ENABLED:
        try:
            from session_manager import supabase
            from datetime import datetime
            supabase.table("doc_clicks").insert({
                "session_id": payload.session_id,
                "file_id":    payload.file_id,
                "file_name":  payload.file_name,
                "url":        payload.url,
                "clicked_at": datetime.utcnow().isoformat(),
            }).execute()
        except Exception as e:
            # Non-fatal — doc_clicks table may not exist yet
            print(f"[track_click] Supabase insert warning: {e}")

    print(f"[track_click] session={payload.session_id} file={payload.file_name}")
    return {"status": "tracked"}


# ==================================================
# SEARCH DOCS ENDPOINT
# GET /search_docs?q=<query>
# ==================================================

import sqlite3

_TRACKER_DB = os.path.join(_repo_root, "data", "tracker.db")


def _get_tracker_connection():
    if not os.path.exists(_TRACKER_DB):
        fallback = os.path.join(_backend_dir, "data", "tracker.db")
        if os.path.exists(fallback):
            return sqlite3.connect(fallback)
        return None
    return sqlite3.connect(_TRACKER_DB)


@app.get("/search_docs")
def search_docs(q: str = ""):
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

        cols     = [row[1] for row in cursor.execute(f"PRAGMA table_info({target_table})").fetchall()]
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
            row_dict  = dict(row)
            file_name = row_dict.get(name_col, "")
            file_id   = row_dict.get(id_col, "") if id_col else ""
            url = f"https://drive.google.com/file/d/{file_id}/view" if file_id else ""
            results.append({"file_name": file_name, "file_id": file_id, "url": url})

        return results

    except Exception as e:
        print(f"/search_docs error: {e}")
        return []
    finally:
        conn.close()


# ==================================================
# DOCUMENTS ENDPOINT
# GET /documents
# Returns most recently indexed documents (global)
# Used by Dashboard 'Latest Documents' card
# ==================================================

@app.get("/documents")
def get_documents(limit: int = 10):
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

        cols          = [row[1] for row in cursor.execute(f"PRAGMA table_info({target_table})").fetchall()]
        name_col      = next((c for c in cols if "name" in c.lower()), cols[0] if cols else None)
        id_col        = next((c for c in cols if "id" in c.lower() and "file" in c.lower()), None)
        if id_col is None:
            id_col    = next((c for c in cols if "id" in c.lower()), None)
        timestamp_col = next((c for c in cols if any(
            k in c.lower() for k in ["time", "date", "created", "indexed", "modified"]
        )), None)

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
            results.append({"file_name": file_name, "file_id": file_id, "url": url})

        return results

    except Exception as e:
        print(f"/documents error: {e}")
        return []
    finally:
        conn.close()


# ==================================================
# FREQUENT DOCS ENDPOINT
# GET /frequent_docs
# Global — across ALL users/sessions
# Used by Dashboard 'Frequently Visited' card
# ==================================================

@app.get("/frequent_docs")
def get_frequent_docs():
    if not SESSION_ENABLED:
        return {"documents": []}
    try:
        docs = get_all_frequent_docs(limit=5)
        return {"documents": docs}
    except Exception as e:
        print(f"/frequent_docs error: {e}")
        return {"documents": []}


# ==================================================
# RECENT ACTIVITY ENDPOINT
# GET /recent_activity
# Global — across ALL users/sessions
# Used by Dashboard 'Recent Activity' card
# ==================================================

@app.get("/recent_activity")
def get_recent_activity():
    if not SESSION_ENABLED:
        return {"activity": []}
    try:
        activity = get_all_recent_activity(limit=20)
        return {"activity": activity}
    except Exception as e:
        print(f"/recent_activity error: {e}")
        return {"activity": []}