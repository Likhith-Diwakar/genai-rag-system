import sys
import os
import sqlite3
from pathlib import Path

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

try:
    from src.storage.tracker_db import TrackerDB
    _tracker = TrackerDB()
    TRACKER_ENABLED = True
    print("TrackerDB loaded successfully")
except Exception as e:
    _tracker = None
    TRACKER_ENABLED = False
    print(f"TrackerDB unavailable: {e}")

app = FastAPI()
INITIALIZED = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _get_tracker_db_path() -> str:
    base = os.getenv("DATA_DIR", os.path.join(_backend_dir, "data"))
    return str(Path(base) / "tracker.db")


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

        # ── Reconnect TrackerDB after restore ────────────────────────
        # The restore overwrites tracker.db on disk AFTER TrackerDB
        # already opened an empty connection at import time.
        # Close and reopen so search queries see the restored data.
        if TRACKER_ENABLED and _tracker is not None:
            try:
                _tracker.conn.close()
                _tracker.conn = sqlite3.connect(
                    _get_tracker_db_path(),
                    check_same_thread=False
                )
                _tracker.conn.execute("PRAGMA journal_mode=WAL;")
                print(f"TrackerDB reconnected to: {_get_tracker_db_path()}")
            except Exception as e:
                print(f"TrackerDB reconnect warning: {e}")
        # ─────────────────────────────────────────────────────────────

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


class QueryRequest(BaseModel):
    query:      str
    session_id: Optional[str] = None


class ClickPayload(BaseModel):
    session_id: str
    file_id:    str = ""
    file_name:  str = ""
    url:        str = ""


class TrackDocumentPayload(BaseModel):
    session_id: str
    file_name:  str
    file_url:   str


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


@app.get("/history")
def get_history(session_id: str):
    if not SESSION_ENABLED:
        return {"session_id": session_id, "history": {}, "error": "Session storage not configured"}
    try:
        history = get_chat_history(session_id)
        return {"session_id": session_id, "history": history}
    except Exception as e:
        return {"session_id": session_id, "history": {}, "error": str(e)}


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
            print(f"[track_click] Supabase insert warning: {e}")
    print(f"[track_click] session={payload.session_id} file={payload.file_name}")
    return {"status": "tracked"}


@app.post("/track-document")
def track_document(payload: TrackDocumentPayload):
    if not payload.session_id or not payload.file_name:
        return {"status": "ignored"}
    if SESSION_ENABLED:
        try:
            from session_manager import supabase
            from datetime import datetime
            now = datetime.utcnow()
            supabase.table("messages").insert({
                "session_id": payload.session_id,
                "query":      f"[document access] {payload.file_name}",
                "answer":     "",
                "sources":    [{"name": payload.file_name, "url": payload.file_url}],
                "timestamp":  now.isoformat(),
                "date_key":   now.strftime("%Y-%m-%d"),
                "query_hash": f"doc_access_{payload.file_name}_{now.timestamp()}",
            }).execute()
        except Exception as e:
            print(f"[track-document] Supabase insert error: {e}")
            return {"status": "error", "detail": str(e)}
    print(f"[track-document] session={payload.session_id} file={payload.file_name}")
    return {"status": "tracked"}


@app.get("/search_docs")
def search_docs(q: str = ""):
    if not q.strip():
        return []

    if TRACKER_ENABLED and _tracker is not None:
        try:
            rows = _tracker.conn.execute(
                """
                SELECT file_id, file_name
                FROM   files
                WHERE  LOWER(file_name) LIKE ?
                ORDER  BY file_name ASC
                LIMIT  5
                """,
                (f"%{q.lower()}%",)
            ).fetchall()
            results = []
            for file_id, file_name in rows:
                url = f"https://drive.google.com/file/d/{file_id}/view" if file_id else ""
                results.append({"file_name": file_name, "file_id": file_id, "url": url})
            print(f"[search_docs] (via TrackerDB) '{q}' → {len(results)} result(s): {[r['file_name'] for r in results]}")
            return results
        except Exception as e:
            print(f"[search_docs] TrackerDB query failed, falling back: {e}")

    db_path = _get_tracker_db_path()
    print(f"[search_docs] Opening fresh connection at: {db_path}")
    if not os.path.exists(db_path):
        print(f"[search_docs] CRITICAL: tracker.db not found at {db_path}")
        return []

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        tables = [row[0] for row in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        print(f"[search_docs] Tables in DB: {tables}")
        if "files" not in tables:
            print("[search_docs] `files` table not found")
            return []
        rows = cursor.execute(
            """
            SELECT file_id, file_name
            FROM   files
            WHERE  LOWER(file_name) LIKE ?
            ORDER  BY file_name ASC
            LIMIT  5
            """,
            (f"%{q.lower()}%",)
        ).fetchall()
        results = []
        for file_id, file_name in rows:
            url = f"https://drive.google.com/file/d/{file_id}/view" if file_id else ""
            results.append({"file_name": file_name, "file_id": file_id, "url": url})
        print(f"[search_docs] (fresh conn) '{q}' → {len(results)} result(s): {[r['file_name'] for r in results]}")
        return results
    except Exception as e:
        print(f"[search_docs] Exception: {e}")
        return []
    finally:
        if conn:
            conn.close()


@app.get("/debug-db")
def debug_db():
    info = {
        "cwd":             os.getcwd(),
        "DATA_DIR_env":    os.getenv("DATA_DIR", "not set"),
        "db_path":         _get_tracker_db_path(),
        "db_exists":       os.path.exists(_get_tracker_db_path()),
        "tracker_enabled": TRACKER_ENABLED,
        "tables":          [],
        "files_rows":      [],
        "error":           None,
    }
    if not info["db_exists"]:
        data_dir = os.path.dirname(_get_tracker_db_path())
        info["data_dir_contents"] = os.listdir(data_dir) if os.path.isdir(data_dir) else "directory missing"
        return info
    try:
        conn = sqlite3.connect(info["db_path"])
        cursor = conn.cursor()
        info["tables"] = [r[0] for r in cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        if "files" in info["tables"]:
            rows = cursor.execute("SELECT file_id, file_name FROM files").fetchall()
            info["files_rows"] = [{"file_id": r[0], "file_name": r[1]} for r in rows]
        conn.close()
    except Exception as e:
        info["error"] = str(e)
    return info


@app.get("/latest-documents")
def get_latest_documents():
    if not TRACKER_ENABLED or _tracker is None:
        return []
    try:
        docs = _tracker.get_latest_documents(limit=5)
        return docs
    except Exception as e:
        print(f"/latest-documents error: {e}")
        return []


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


@app.get("/recent_activity")
def get_recent_activity():
    if not SESSION_ENABLED:
        return {"activity": []}
    try:
        activity = get_all_recent_activity(limit=10)
        return {"activity": activity}
    except Exception as e:
        print(f"/recent_activity error: {e}")
        return {"activity": []}
