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

class QueryRequest(BaseModel):
    query: str


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
# CHAT ENDPOINT
# ==================================================

@app.post("/chat")
def chat(request: QueryRequest):
    try:
        query = request.query.strip().lower()

        # ------------------------------------------
        # ✅ PRELOADED RESPONSE (NO API CALL)
        # ------------------------------------------

        if query in PRELOADED_QA:
            data = PRELOADED_QA[query]
            return {
                "response": data["answer"],
                "sources": [{
                    "name": data["source"],
                    "url": ""
                }]
            }

        # ------------------------------------------
        # NORMAL PIPELINE
        # ------------------------------------------

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

            # ------------------------------------------
            # NO ANSWER FIX
            # ------------------------------------------

            NO_ANSWER_TEXT = "I do not know based on the provided documents."

            CUSTOM_FALLBACK = (
                "I'm sorry, but I couldn't find relevant information in the indexed documents. "
                "Please try asking a more specific question related to the documents available in the connected Google Drive."
            )

            if answer and answer.strip() == NO_ANSWER_TEXT:
                return {
                    "response": CUSTOM_FALLBACK,
                    "sources": []
                }

            # ------------------------------------------
            # SINGLE SOURCE FIX
            # ------------------------------------------

            raw_sources = result.get("sources", [])

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