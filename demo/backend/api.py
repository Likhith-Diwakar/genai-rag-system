import sys
import os

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.orchestration.langgraph_pipeline import run_pipeline

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str


@app.post("/chat")
def chat(request: QueryRequest):
    try:
        result = run_pipeline(request.query)

        answer = None
        sources = []

        if isinstance(result, dict):

            # Extract answer
            answer = (
                result.get("answer")
                or result.get("final_answer")
                or result.get("response")
                or result.get("output")
                or result.get("result")
            )

            # Extract sources with clickable links
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