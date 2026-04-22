# scripts/clear_qdrant.py

import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from src.embedding.vector_store import COLLECTION_NAME

load_dotenv()  # Load .env file

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")


def main():

    if not QDRANT_URL or not QDRANT_API_KEY:
        raise RuntimeError(
            "QDRANT_URL or QDRANT_API_KEY not set in environment."
        )

    client = QdrantClient(
        url=QDRANT_URL.strip(),
        api_key=QDRANT_API_KEY.strip(),
    )

    print(f"Deleting collection: {COLLECTION_NAME}")

    existing = [
        c.name for c in client.get_collections().collections
    ]

    if COLLECTION_NAME not in existing:
        print("Collection does not exist. Nothing to delete.")
        return

    client.delete_collection(COLLECTION_NAME)

    print("Collection deleted successfully.")


if __name__ == "__main__":
    main()
