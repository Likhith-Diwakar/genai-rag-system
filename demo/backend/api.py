import sys
import os

# --------------------------------------------------
# PATH FIX
# --------------------------------------------------

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --------------------------------------------------
# IMPORTS
# --------------------------------------------------

# LangGraph pipeline
try:
    from src.orchestration.langgraph_pipeline import run_pipeline
except Exception as e:
    run_pipeline = None
    print(f"❌ Pipeline import error: {e}")

# SQLite restore
try:
    from scripts.restore_sqlite import restore_sqlite_if_missing
except Exception as e:
    restore_sqlite_if_missing = None
    print(f"❌ Restore import error: {e}")

# --------------------------------------------------
# APP INIT
# --------------------------------------------------

app = FastAPI()

# --------------------------------------------------
# STARTUP EVENT (🔥 CRITICAL FIX)
# --------------------------------------------------

@app.on_event("startup")
def startup_event():
    try:
        print("🚀 Starting system initialization...")

        if restore_sqlite_if_missing:
            restore_sqlite_if_missing()
            print("✅ SQLite restoration complete")
        else:
            print("⚠️ Restore function not available")

    except Exception as e:
        print("❌ Startup failed:", str(e))


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
                "response": "Pipeline failed to load",
                "sources": []
            }

        result = run_pipeline(request.query)

        answer = None
        sources = []

        if isinstance(result, dict):

            # Extract answer robustly
            answer = (
                result.get("answer")
                or result.get("final_answer")
                or result.get("response")
                or result.get("output")
                or result.get("result")
            )

            # Extract sources
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

            # Remove duplicates
            unique_sources = {s["name"]: s for s in sources}.values()

            return {
                "response": answer or "No response generated.",
                "sources": list(unique_sources)
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