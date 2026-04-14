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

# ── Session manager ───────────────────────────────────────────────
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
# PRELOADED ANSWERS
# ==================================================

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
}


# ==================================================
# MODELS
# ==================================================

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None


# ==================================================
# FIXED SOURCE NORMALISATION
# ==================================================

def _normalise_sources(raw_sources: list) -> list:
    """
    FIX:
    - Deduplicate sources
    - Return ONLY top relevant document (first unique)
    """
    seen = set()
    result = []

    for meta in raw_sources:
        if not isinstance(meta, dict):
            continue

        name = meta.get("file_name") or meta.get("name") or ""
        file_id = meta.get("file_id") or ""

        if not name:
            continue

        key = file_id or name

        if key in seen:
            continue

        seen.add(key)

        url = f"https://drive.google.com/file/d/{file_id}/view" if file_id else ""

        result.append({
            "name": name,
            "url": url
        })

        # IMPORTANT FIX → only 1 source
        if len(result) >= 1:
            break

    return result


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

        # PRELOADED
        if query_lower in PRELOADED_QA:
            data = PRELOADED_QA[query_lower]
            answer = data["answer"]
            sources = [{"name": data["source"], "url": ""}]

            if SESSION_ENABLED:
                save_message(session_id, query_raw, answer, sources)

            return {
                "response": answer,
                "sources": sources,
                "cache_hit": False,
                "session_id": session_id,
            }

        # CACHE
        if SESSION_ENABLED:
            try:
                cached = check_cache(session_id, query_raw)
                if cached and cached.get("answer"):
                    sources = cached.get("sources", [])
                    if isinstance(sources, str):
                        import json
                        sources = json.loads(sources)

                    return {
                        "response": cached["answer"],
                        "sources": sources,
                        "cache_hit": True,
                        "session_id": session_id,
                    }
            except Exception as e:
                print(f"Cache error: {e}")

        # PIPELINE
        if run_pipeline is None:
            return {
                "response": "Pipeline failed",
                "sources": [],
                "cache_hit": False,
                "session_id": session_id,
            }

        result = run_pipeline(query_raw)

        answer = (
            result.get("answer")
            or result.get("final_answer")
            or result.get("response")
            or result.get("output")
        )

        raw_sources = result.get("sources", [])
        sources = _normalise_sources(raw_sources)

        final_answer = answer or "No response generated."

        if SESSION_ENABLED:
            save_to_cache(session_id, query_raw, final_answer, sources)
            save_message(session_id, query_raw, final_answer, sources)

        return {
            "response": final_answer,
            "sources": sources,
            "cache_hit": False,
            "session_id": session_id,
        }

    except Exception as e:
        return {
            "response": str(e),
            "sources": [],
            "cache_hit": False,
            "session_id": request.session_id or "anonymous",
        }


# ==================================================
# HISTORY
# ==================================================

@app.get("/history")
def get_history(session_id: str):
    try:
        history = get_chat_history(session_id)
        return {"session_id": session_id, "history": history}
    except Exception as e:
        return {"session_id": session_id, "history": {}, "error": str(e)}