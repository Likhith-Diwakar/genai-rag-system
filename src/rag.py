import subprocess
from src.query import query_vector_store

OLLAMA_PATH = r"C:\Users\Admin\AppData\Local\Programs\Ollama\ollama.exe"
OLLAMA_MODEL = "mistral"


def call_ollama(prompt: str) -> str:
    result = subprocess.run(
        [OLLAMA_PATH, "run", OLLAMA_MODEL],
        input=prompt,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="ignore"
    )
    return result.stdout.strip()


def generate_answer(query: str, k: int = 5):
    documents, metadatas = query_vector_store(query, k)

    context_blocks = []
    sources = []

    for doc, meta in zip(documents, metadatas):
        context_blocks.append(doc)

        if isinstance(meta, dict):
            sources.append({
                "file_id": meta.get("file_id"),
                "file_name": meta.get("file_name", "Unknown Document")
            })

    context = "\n\n".join(context_blocks)

    prompt = f"""
You are a helpful assistant.
Answer the question ONLY using the context below.
If the answer is not present, say you do not know.

Context:
{context}

Question:
{query}

Answer clearly and concisely.
"""

    answer = call_ollama(prompt)
    return answer, sources


if __name__ == "__main__":
    q = "What is my capstone project about?"
    ans, srcs = generate_answer(q)

    print("\nANSWER:\n", ans)
    print("\nSOURCES:")
    for s in srcs:
        print(f"- {s['file_name']} ({s['file_id']})")
