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

SQLITE_FOLDER_ID = os.getenv("SQLITE_FOLDER_ID")
QDRANT_FOLDER_ID = os.getenv("QDRANT_FOLDER_ID")


# --------------------------------------------------
# FIND EXISTING FILE
# --------------------------------------------------

def find_existing_file(service, folder_id, filename):
    query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"

    results = service.files().list(
        q=query,
        fields="files(id, name)",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()

    files = results.get("files", [])
    return files[0] if files else None


# --------------------------------------------------
# UPLOAD / UPDATE BACKUP
# --------------------------------------------------

def upload_backup(file_path: str, backup_type: str):

    if not os.path.exists(file_path):
        raise FileNotFoundError("Backup file not found.")

    # IMPORTANT: Use OAuth (not service account)
    creds = get_credentials(force_oauth=True)
    service = build("drive", "v3", credentials=creds)

    filename = os.path.basename(file_path)

    # --------------------------------------------------
    # SELECT FOLDER
    # --------------------------------------------------

    if backup_type == "sqlite":
        folder_id = SQLITE_FOLDER_ID
    elif backup_type == "qdrant":
        folder_id = QDRANT_FOLDER_ID
    else:
        raise ValueError("Invalid backup type. Use 'sqlite' or 'qdrant'.")

    if not folder_id:
        raise ValueError("Backup folder ID not set in environment variables")

    # --------------------------------------------------
    # PREPARE FILE
    # --------------------------------------------------

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

    # --------------------------------------------------
    # UPSERT LOGIC (UPDATE OR CREATE)
    # --------------------------------------------------

    existing_file = find_existing_file(service, folder_id, filename)

    if existing_file:
        # UPDATE (overwrite existing file)
        service.files().update(
            fileId=existing_file["id"],
            media_body=media,
            supportsAllDrives=True
        ).execute()

        print(f"Updated existing backup: {filename}")

    else:
        # CREATE new file
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
            supportsAllDrives=True
        ).execute()

        print(f"Created new backup: {filename}")
        print(f"Drive File ID: {file.get('id')}")