# src/ingestion/main.py
from dotenv import load_dotenv
load_dotenv()

import os
import time
import tempfile
import json
import requests

from src.ingestion.list_docs import list_drive_documents
from src.ingestion.download_file import download_drive_file

from src.providers.parsers.parser_router import ParserRouter
from src.providers.embeddings.bge_embedder import BGEEmbedder
from src.embedding.vector_store import VectorStore
from src.providers.chunking.chunking_router import ChunkingRouter
from src.providers.retrievers.bm25_retriever import BM25Retriever

from src.storage.tracker_db import TrackerDB
from src.storage.sqlite_store import SQLiteStore
from src.utils.logger import logger


GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"
CSV_MIME = "text/csv"


# -----------------------------
# Query Generator (OpenRouter)
# -----------------------------

class QueryGenerator:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set")

        self.url = "https://openrouter.ai/api/v1/chat/completions"

        self.models = [
            "meta-llama/llama-3-8b-instruct",
            "mistralai/mistral-7b-instruct",
            "meta-llama/llama-3-70b-instruct",
            "google/gemma-3-12b-it",
        ]

    def _build_prompt(self, chunks):
        chunks_text = "\n\n".join([
            f"Chunk {i+1}:\n{c[:500]}"
            for i, c in enumerate(chunks)
        ])
        num = len(chunks)
        return f"""You are generating search queries for a retrieval system.

For EACH chunk below output EXACTLY this format (no extra text, no preamble):

Chunk 1:
- query one
- query two
- query three

Chunk 2:
- query one
- query two
- query three

Rules:
- You MUST output all {num} chunks numbered exactly as shown.
- Every chunk MUST have exactly 3 queries.
- Do NOT skip any chunk.

TEXT CHUNKS:
{chunks_text}"""

    def _parse_response_text(self, text: str, num_chunks: int):
        import re
        results = []
        current = []

        chunk_header = re.compile(r"^[*]*chunk\s*\d+[*]*\s*:?[*]*\s*$", re.IGNORECASE)

        for line in text.split("\n"):
            stripped = line.strip()

            if chunk_header.match(stripped):
                if current:
                    results.append(current)
                current = []

            elif stripped.startswith("-"):
                query = stripped.lstrip("- ").strip()
                if query:
                    current.append(query)

        if current:
            results.append(current)

        while len(results) < num_chunks:
            results.append([])

        return results[:num_chunks]

    def _call_model(self, model: str, prompt: str, timeout: int = 60):
        response = requests.post(
            self.url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=timeout
        )

        response.raise_for_status()
        data = response.json()

        choices = data.get("choices", [])
        if not choices:
            logger.warning(f"No choices in response from {model}: {data}")
            return None

        choice = choices[0]
        finish_reason = choice.get("finish_reason")
        content = choice.get("message", {}).get("content")

        if content is None or finish_reason is None:
            logger.warning(f"{model} returned empty response")
            return None

        return content

    def generate_queries_batch(self, chunks):
        if not chunks:
            return []

        prompt = self._build_prompt(chunks)

        for attempt, model in enumerate(self.models, start=1):
            try:
                logger.info(f"Query generation | attempt={attempt} model={model}")

                text = self._call_model(model, prompt)

                if text:
                    results = self._parse_response_text(text, len(chunks))
                    logger.info(f"Query generation success | model={model}")
                    return results

            except requests.exceptions.Timeout:
                logger.warning(f"Timeout on {model}")

            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response else "?"

                if status == 429:
                    wait = 5 * attempt
                    logger.warning(f"Rate limited ({model}), waiting {wait}s")
                    time.sleep(wait)

                else:
                    logger.warning(f"HTTP {status} on {model}")

            except Exception as e:
                logger.warning(f"{model} error: {e}")

        logger.error("Query generation failed completely")
        return [[] for _ in chunks]


# -----------------------------
# MAIN
# -----------------------------

def main():

    logger.info("DEBUG: main() started")

    vector_store = VectorStore()
    embedder = BGEEmbedder()
    tracker = TrackerDB()
    sqlite_store = SQLiteStore()
    parser_router = ParserRouter()
    chunk_router = ChunkingRouter()

    bm25 = BM25Retriever()
    bm25.load()

    query_generator = QueryGenerator()

    docs = list_drive_documents()

    if not docs:
        logger.info("No documents found")
        return

    local_store = []

    drive_file_ids = {doc["id"] for doc in docs}
    tracked_file_ids = tracker.get_all_file_ids()

    deleted_file_ids = tracked_file_ids - drive_file_ids

    for file_id in deleted_file_ids:
        file_name = tracker.get_file_name(file_id)

        logger.info(f"File deleted → {file_name}")

        vector_store.delete_by_file_id(file_id)

        if file_name:
            try:
                sqlite_store.drop_table(file_name)
            except Exception:
                pass

        tracker.remove(file_id)

    for doc in docs:

        file_id   = doc["id"]
        file_name = doc["name"]
        mime_type = doc["mimeType"]

        if tracker.is_ingested(file_id):
            continue

        logger.info(f"New file detected → {file_name}")

        # ── LATEST DOCUMENTS: record this file immediately on detection ──
        # Builds the Google Drive view URL from file_id.
        # Inserts into latest_documents table (no-op if already present).
        # Automatically prunes to keep only the 5 most recent entries.
        try:
            file_url = f"https://drive.google.com/file/d/{file_id}/view"
            tracker.add_latest_document(file_id, file_name, file_url)
            logger.info(f"Latest documents updated → {file_name}")
        except Exception as e:
            # Non-fatal — ingestion continues even if this fails
            logger.warning(f"Failed to update latest_documents → {file_name} | {e}")
        # ────────────────────────────────────────────────────────────────

        text = ""

        try:
            if mime_type == CSV_MIME:
                parser = parser_router.route(file_name)
                parser.parse(file_id, file_name)
                tracker.mark_ingested(file_id, file_name)
                logger.info(f"Finished → {file_name}")
                continue

            if mime_type == GOOGLE_DOC_MIME:
                parser = parser_router.route(file_name)
                text = parser.parse(file_id)

            elif mime_type in [DOCX_MIME, PDF_MIME]:
                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                    download_drive_file(file_id, tmp.name)
                    temp_path = tmp.name

                parser = parser_router.route(file_name)
                text = parser.parse(temp_path)
                os.unlink(temp_path)

            else:
                tracker.mark_ingested(file_id, file_name)
                logger.info(f"Finished → {file_name}")
                continue

        except Exception as e:
            logger.warning(f"Extraction failed → {file_name} | {e}")
            tracker.mark_ingested(file_id, file_name)
            continue

        if not text or not text.strip():
            logger.warning(f"No text → {file_name}")
            tracker.mark_ingested(file_id, file_name)
            continue

        chunker = chunk_router.route(mime_type)
        chunks = chunker.chunk(text)

        if not chunks:
            tracker.mark_ingested(file_id, file_name)
            continue

        synthetic_queries_all = []

        for i in range(0, len(chunks), 10):
            batch = chunks[i:i + 10]
            batch_queries = query_generator.generate_queries_batch(batch)
            synthetic_queries_all.extend(batch_queries)

        logger.info(f"Query generation done → {file_name}")

        embeddings = embedder.embed(chunks)
        ids = [f"{file_id}_{i}" for i in range(len(chunks))]

        metadatas = []

        for i in range(len(chunks)):
            meta = {
                "file_id":            file_id,
                "file_name":          file_name,
                "chunk_id":           i,
                "synthetic_queries":  synthetic_queries_all[i] if i < len(synthetic_queries_all) else []
            }

            metadatas.append(meta)

            local_store.append({
                "id":       ids[i],
                "text":     chunks[i],
                "metadata": meta
            })

        vector_store.add_chunks(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids,
        )

        bm25.add_chunks(
            documents=chunks,
            metadatas=metadatas,
        )

        tracker.mark_ingested(file_id, file_name)

        logger.info(f"Finished → {file_name}")

    try:
        with open("local_chunks.json", "w", encoding="utf-8") as f:
            json.dump(local_store, f, indent=2)
        logger.info("Local JSON saved")

    except Exception as e:
        logger.warning(f"Failed to save JSON: {e}")

    logger.info("Ingestion completed")
    logger.info("DEBUG: main() finished")


def run_sync(verbose: bool = True):
    main()


if __name__ == "__main__":
    run_sync()