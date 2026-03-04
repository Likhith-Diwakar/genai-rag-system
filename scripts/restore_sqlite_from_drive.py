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

SQLITE_DB_PATH = os.path.join(PROJECT_ROOT, "data", "tracker.db")


def restore_sqlite_if_missing():

    if os.path.exists(SQLITE_DB_PATH):
        print("SQLite already exists locally. Skipping restore.")
        return

    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    query = f"'{SQLITE_BACKUP_FOLDER_ID}' in parents and trashed=false"

    results = service.files().list(
        q=query,
        fields="files(id, name)",
    ).execute()

    files = results.get("files", [])

    if not files:
        print("No SQLite backup found in Drive.")
        return

    file_id = files[0]["id"]

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

    print("SQLite restored successfully from Drive backup.")