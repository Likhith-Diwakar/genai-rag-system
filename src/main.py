from src.list_docs import list_google_docs
from src.extract_text import extract_doc_text
from src.chunker import chunk_text
from src.embeddings import embed_texts
from src.vector_store import VectorStore
from src.tracker_db import TrackerDB


def main():
    print("Starting Drive -> Vector sync")

    # Initialize vector store and tracker
    store = VectorStore()
    tracker = TrackerDB()

    # Fetch Google Docs from Drive
    docs = list_google_docs()
    current_drive_ids = set()

    if not docs:
        print("No Google Docs found in Drive.")
        return

    for doc in docs:
        file_id = doc["id"]
        file_name = doc["name"]
        current_drive_ids.add(file_id)

        # Skip already ingested files
        if tracker.is_ingested(file_id):
            print(f"Skipping already ingested: {file_name}")
            continue

        print(f"Ingesting: {file_name}")

        # 1. Extract text
        text = extract_doc_text(file_id)

        if not text or not text.strip():
            print(f"Empty document, skipping: {file_name}")
            continue

        # 2. Chunk text
        chunks = chunk_text(text)

        if not chunks:
            print(f"No chunks created, skipping: {file_name}")
            continue

        # 3. Embed chunks
        embeddings = embed_texts(chunks)

        # 4. Store in vector DB
        ids = [f"{file_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "file_id": file_id,
                "file_name": file_name,
                "chunk_id": i,
            }
            for i in range(len(chunks))
        ]

        store.add_chunks(
            embeddings=embeddings,
            documents=chunks,
            metadatas=metadatas,
            ids=ids,
        )

        # 5. Mark file as ingested
        tracker.mark_ingested(file_id, file_name)
        print(f"Done: {file_name}")

    # Handle deletions (files removed from Drive)
    tracked_ids = tracker.get_all_file_ids()
    deleted_ids = tracked_ids - current_drive_ids

    for file_id in deleted_ids:
        print(f"Removing deleted file: {file_id}")
        store.delete_by_file_id(file_id)
        tracker.remove(file_id)

    print("Sync complete")


if __name__ == "__main__":
    main()
