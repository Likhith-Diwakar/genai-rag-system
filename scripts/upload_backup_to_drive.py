import os
import sys
import mimetypes
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --------------------------------------------------
# FIX PYTHON PATH
# --------------------------------------------------

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --------------------------------------------------

from src.utils.auth import get_credentials

# --------------------------------------------------
# ENV (NO HARDCODING)
# --------------------------------------------------

SQLITE_BACKUP_FOLDER_ID = os.getenv("SQLITE_BACKUP_FOLDER_ID")
QDRANT_BACKUP_FOLDER_ID = os.getenv("QDRANT_BACKUP_FOLDER_ID")


# --------------------------------------------------
# DELETE EXISTING FILE
# --------------------------------------------------

def delete_existing_file(service, folder_id, filename):
    query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"

    results = service.files().list(
        q=query,
        fields="files(id, name)"
    ).execute()

    files = results.get("files", [])

    for file in files:
        service.files().delete(fileId=file["id"]).execute()
        print(f"Deleted old file: {file['name']}", flush=True)


# --------------------------------------------------
# UPLOAD BACKUP
# --------------------------------------------------

def upload_backup(file_path: str, backup_type: str):

    if not os.path.exists(file_path):
        raise FileNotFoundError("Backup file not found.")

    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    filename = os.path.basename(file_path)

    # SELECT FOLDER
    if backup_type == "sqlite":
        folder_id = SQLITE_BACKUP_FOLDER_ID
    elif backup_type == "qdrant":
        folder_id = QDRANT_BACKUP_FOLDER_ID
    else:
        raise ValueError("Invalid backup type. Use 'sqlite' or 'qdrant'.")

    if not folder_id:
        raise ValueError("Backup folder ID not set in environment variables")

    print(f"Uploading {filename} to folder {folder_id}", flush=True)

    # DELETE OLD FILE
    delete_existing_file(service, folder_id, filename)

    # PREPARE UPLOAD
    file_metadata = {
        "name": filename,
        "parents": [folder_id],
    }

    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "application/octet-stream"

    media = MediaFileUpload(
        file_path,
        mimetype=mime_type,
        resumable=True,
    )

    # UPLOAD NEW FILE
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id",
    ).execute()

    print(f"Uploaded successfully: {filename}", flush=True)
    print(f"Drive File ID: {file.get('id')}", flush=True)
