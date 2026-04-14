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

# ── Session manager (Firebase) ───────────────────────────────────────────────
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
# ✅ PRELOADED ANSWERS (MENTOR REQUIREMENT)
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


# ==================================================
# HELPER — return only the top (most relevant) source
# ==================================================

def _normalise_sources(raw_sources: list) -> list:
    """
    Pipeline returns retrieved_metas — a list of dicts with keys like
    file_id, file_name, chunk_id, etc., ranked by relevance.
    We return only the FIRST valid source (most relevant) in the shape
    the frontend expects: [{"name": "...", "url": "..."}]
    """
    for meta in raw_sources:
        if not isinstance(meta, dict):
            continue
        name = meta.get("file_name") or meta.get("name") or ""
        file_id = meta.get("file_id") or ""
        if not name:
            continue
        url = f"https://drive.google.com/file/d/{file_id}/view" if file_id else ""
        return [{"name": name, "url": url}]  # Return only the top source
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

        # ── Ensure session exists in Supabase ───────────────────────────────
        if SESSION_ENABLED:
            try:
                get_or_create_session(session_id)
            except Exception as e:
                print(f"Session init warning: {e}")

        # ------------------------------------------------------------------
        # ✅ PRELOADED RESPONSE (NO API CALL, NO CACHE WRITE NEEDED)
        # ------------------------------------------------------------------
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

        # ------------------------------------------------------------------
        # ✅ CACHE LOOKUP  (exact → semantic)
        # ------------------------------------------------------------------
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

                    # FORCE SINGLE SOURCE — old cache entries may have multiple
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

        # ------------------------------------------------------------------
        # NORMAL PIPELINE
        # ------------------------------------------------------------------
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

            # ── Return only the top (most relevant) source ─────────────────
            raw_sources = result.get("sources", [])
            sources = _normalise_sources(raw_sources)

            final_answer = answer or "No response generated."

            # ── Save to cache & history ────────────────────────────────────
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
    """
    Returns chat history for a session grouped by date.

    Response shape:
    {
        "session_id": "abc-123",
        "history": {
            "2026-04-14": [
                {"query": "...", "answer": "...", "sources": [...], "timestamp": "..."},
                ...
            ],
            "2026-04-13": [ ... ]
        }
    }
    """
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