import os
import requests
from dotenv import load_dotenv

# Load .env for local dev (Render ignores safely)
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "drive_docs"

# Save inside project backups folder
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


def backup_qdrant():

    if not QDRANT_URL or not QDRANT_API_KEY:
        raise ValueError("QDRANT_URL or QDRANT_API_KEY not set.")

    headers = {
        "api-key": QDRANT_API_KEY
    }

    # 1️⃣ Create snapshot on Qdrant Cloud
    create_response = requests.post(
        f"{QDRANT_URL}/collections/{COLLECTION_NAME}/snapshots",
        headers=headers,
    )
    create_response.raise_for_status()

    snapshot_name = create_response.json()["result"]["name"]

    # 2️⃣ Download snapshot
    download_response = requests.get(
        f"{QDRANT_URL}/collections/{COLLECTION_NAME}/snapshots/{snapshot_name}",
        headers=headers,
        stream=True,
    )
    download_response.raise_for_status()

    #  Always same filename (overwrite mode)
    backup_file = os.path.join(BACKUP_DIR, "qdrant_latest.snapshot")

    with open(backup_file, "wb") as f:
        for chunk in download_response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Qdrant backup updated: {backup_file}")

    return backup_file


if __name__ == "__main__":
    backup_qdrant()