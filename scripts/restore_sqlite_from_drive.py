import os
import sys
import gzip
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.utils.auth import get_credentials

SQLITE_BACKUP_FOLDER_ID = os.getenv("SQLITE_BACKUP_FOLDER_ID")

_data_dir = os.getenv("DATA_DIR", os.path.join(PROJECT_ROOT, "demo", "backend", "data"))
SQLITE_DB_PATH = os.path.join(_data_dir, "tracker.db")


def restore_sqlite_if_missing():
    if not SQLITE_BACKUP_FOLDER_ID:
        print("[restore] SQLITE_BACKUP_FOLDER_ID not set — skipping restore.")
        return

    print(f"[restore] Restoring to: {SQLITE_DB_PATH}")
    print("[restore] Downloading latest SQLite backup from Drive...")

    try:
        creds = get_credentials()
        service = build("drive", "v3", credentials=creds)

        query = f"'{SQLITE_BACKUP_FOLDER_ID}' in parents and trashed=false"
        results = service.files().list(
            q=query,
            fields="files(id, name)",
        ).execute()

        files = results.get("files", [])
        if not files:
            print("[restore] No SQLite backup found in Drive — skipping.")
            return

        file_id = files[0]["id"]
        print(f"[restore] Found backup file: {files[0]['name']} (id={file_id})")

        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.seek(0)
        db_bytes = pickle.load(gzip.GzipFile(fileobj=fh))

        os.makedirs(os.path.dirname(SQLITE_DB_PATH), exist_ok=True)

        with open(SQLITE_DB_PATH, "wb") as f:
            f.write(db_bytes)

        print(f"[restore] SQLite restored successfully → {SQLITE_DB_PATH}")

    except Exception as e:
        print(f"[restore] ERROR during restore: {e}")
