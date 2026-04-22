import os
import sys
import gzip
import pickle
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils.auth import get_credentials

SQLITE_BACKUP_FOLDER_ID = os.getenv("SQLITE_BACKUP_FOLDER_ID")

DATA_DIR = os.getenv(
    "DATA_DIR",
    os.path.join(PROJECT_ROOT, "demo", "backend", "data")
)

SQLITE_DB_PATH = os.path.join(DATA_DIR, "tracker.db")


def restore_sqlite():
    if not SQLITE_BACKUP_FOLDER_ID:
        print("[restore] SQLITE_BACKUP_FOLDER_ID not set — skipping restore.")
        return None

    print(f"[restore] Restoring to: {SQLITE_DB_PATH}")

    try:
        creds = get_credentials()
        service = build("drive", "v3", credentials=creds)

        query = f"'{SQLITE_BACKUP_FOLDER_ID}' in parents and trashed=false"

        results = service.files().list(
            q=query,
            fields="files(id, name, createdTime)",
            orderBy="createdTime desc" 
        ).execute()

        files = results.get("files", [])

        if not files:
            print("[restore] No SQLite backup found in Drive.")
            return None

        latest = files[0]
        file_id = latest["id"]

        print(f"[restore] Found backup: {latest['name']}")

        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()

        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        fh.seek(0)

        db_bytes = pickle.load(gzip.GzipFile(fileobj=fh))

        os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)

        with open(SQLITE_DB_PATH, "wb") as f:
            f.write(db_bytes)

        print(f"[restore] SQLite restored → {SQLITE_DB_PATH}")
        return SQLITE_DB_PATH

    except Exception as e:
        print(f"[restore] ERROR: {e}")
        return None



if __name__ == "__main__":
    restore_sqlite()
