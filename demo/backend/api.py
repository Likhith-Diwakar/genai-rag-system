import sys
import os

# --------------------------------------------------
# PATH FIX
# --------------------------------------------------

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
    print(f" Pipeline import error: {e}")

try:
    from scripts.restore_sqlite_from_drive import restore_sqlite_if_missing
except Exception as e:
    restore_sqlite_if_missing = None
    print(f" Restore import error: {e}")

# --------------------------------------------------
# APP INIT
# --------------------------------------------------

app = FastAPI()

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
        print(" Already initialized, skipping...")
        return

    try:
        print(" STARTUP INIT BEGIN")

        if restore_sqlite_if_missing:
            restore_sqlite_if_missing()
            print(" SQLite restored successfully")
        else:
            print(" Restore function not available — skipping SQLite restore")

        INITIALIZED = True
        print("STARTUP INIT COMPLETE")

    except Exception as e:
        print(f"❌ STARTUP ERROR: {str(e)}")

# --------------------------------------------------
# ROUTES
# --------------------------------------------------

@app.get("/")
def root():
    return {"status": "Backend running "}


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

            # FIX: ONLY TAKE TOP SOURCE
            if raw_sources and isinstance(raw_sources[0], dict):
                name = raw_sources[0].get("file_name")
                file_id = raw_sources[0].get("file_id")

                if name and file_id:
                    sources = [{
                        "name": name,
                        "url": f"https://drive.google.com/file/d/{file_id}/view"
                    }]
                else:
                    sources = []
            else:
                sources = []

            return {
                "response": answer or "No response generated.",
                "sources": sources
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