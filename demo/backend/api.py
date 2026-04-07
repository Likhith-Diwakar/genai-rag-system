import sys
import os

# --------------------------------------------------
# PATH FIX
# --------------------------------------------------

# When Render runs from demo/backend/ as root directory,
# we need to add the repo root (two levels up) to sys.path
# so that "src.orchestration.langgraph_pipeline" can be found.
# Also add the current directory itself as a fallback.

_backend_dir = os.path.dirname(os.path.abspath(__file__))
_repo_root = os.path.abspath(os.path.join(_backend_dir, "..", ".."))

for _path in [_backend_dir, _repo_root]:
    if _path not in sys.path:
        sys.path.insert(0, _path)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --------------------------------------------------
# IMPORTS
# --------------------------------------------------

try:
    from src.orchestration.langgraph_pipeline import run_pipeline
except Exception as e:
    run_pipeline = None
    print(f"❌ Pipeline import error: {e}")

try:
    from scripts.restore_sqlite_from_drive import restore_sqlite_if_missing
except Exception as e:
    restore_sqlite_if_missing = None
    print(f"❌ Restore import error: {e}")

# --------------------------------------------------
# APP INIT
# --------------------------------------------------

app = FastAPI()

# Prevent duplicate restore on hot-reload
INITIALIZED = False

# --------------------------------------------------
# CORS
# --------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# STARTUP INIT
# --------------------------------------------------

@app.on_event("startup")
def startup_event():
    global INITIALIZED

    if INITIALIZED:
        print("⚠️ Already initialized, skipping...")
        return

    try:
        print("🚀 STARTUP INIT BEGIN")

        if restore_sqlite_if_missing:
            restore_sqlite_if_missing()
            print("✅ SQLite restored successfully")
        else:
            print("⚠️ Restore function not available — skipping SQLite restore")

        INITIALIZED = True
        print("🚀 STARTUP INIT COMPLETE")

    except Exception as e:
        # Log but don't crash — the API should still serve requests
        # even if the restore step fails
        print(f"❌ STARTUP ERROR: {str(e)}")


# --------------------------------------------------
# ROUTES
# --------------------------------------------------

@app.get("/")
def root():
    return {"status": "Backend running 🚀"}


@app.get("/health")
def health():
    return {"status": "ok"}


# --------------------------------------------------
# REQUEST MODEL
# --------------------------------------------------

class QueryRequest(BaseModel):
    query: str


# --------------------------------------------------
# CHAT ENDPOINT
# --------------------------------------------------

@app.post("/chat")
def chat(request: QueryRequest):
    try:
        if run_pipeline is None:
            return {
                "response": "Pipeline failed to load. Check backend logs.",
                "sources": []
            }

        result = run_pipeline(request.query)

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

            raw_sources = result.get("sources", [])

            for src in raw_sources:
                if isinstance(src, dict):
                    name = src.get("file_name")
                    file_id = src.get("file_id")

                    if name and file_id:
                        sources.append({
                            "name": name,
                            "url": f"https://drive.google.com/file/d/{file_id}/view"
                        })

            unique_sources = list({s["name"]: s for s in sources}.values())

            return {
                "response": answer or "No response generated.",
                "sources": unique_sources
            }

        return {
            "response": str(result),
            "sources": []
        }

    except Exception as e:
        return {
            "response": f"Backend error: {str(e)}",
            "sources": []
        }