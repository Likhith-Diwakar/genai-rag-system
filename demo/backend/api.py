import sys
import os

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# IMPORTANT: import inside try (prevents crash during startup)
try:
    from src.orchestration.langgraph_pipeline import run_pipeline
except Exception as e:
    run_pipeline = None
    print(f"Pipeline import error: {e}")

app = FastAPI()

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ ROOT ROUTE (VERY IMPORTANT FOR RENDER)
@app.get("/")
def root():
    return {"status": "Backend running 🚀"}

# ✅ HEALTH CHECK (Render friendly)
@app.get("/health")
def health():
    return {"status": "ok"}

# Request model
class QueryRequest(BaseModel):
    query: str

# ✅ CHAT ENDPOINT
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

            unique_sources = {s["name"]: s for s in sources}.values()

            return {
                "response": answer or "No response",
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