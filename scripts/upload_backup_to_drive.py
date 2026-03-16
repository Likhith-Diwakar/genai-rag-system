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

# 🔹 FOLDER IDS
SQLITE_BACKUP_FOLDER_ID = "1RZjb6ok7ub7lG_gYI5fecAkHAmIejSCm"
QDRANT_BACKUP_FOLDER_ID = "1jFOnY3dsC7e8gnQg4Ntj7VEYk2mtDmRN"


def delete_existing_file(service, folder_id, filename):
    """
    Delete existing backup file if it exists.
    Safe for CI environments where service account
    may not own the file.
    """

    query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"

    try:
        results = service.files().list(
            q=query,
            fields="files(id, name)"
        ).execute()

        files = results.get("files", [])

        if not files:
            return

        for file in files:
            try:
                service.files().delete(fileId=file["id"]).execute()
                print(f"Deleted old file: {file['name']}")
            except Exception as delete_error:
                print(
                    f"Warning: could not delete file {file['name']} "
                    f"(possibly owned by another account): {delete_error}"
                )

    except Exception as e:
        print(f"Warning: failed to check existing backups: {e}")


def upload_backup(file_path: str, backup_type: str):

    if not os.path.exists(file_path):
        raise FileNotFoundError("Backup file not found.")

    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    filename = os.path.basename(file_path)

    if backup_type == "sqlite":
        folder_id = SQLITE_BACKUP_FOLDER_ID
    elif backup_type == "qdrant":
        folder_id = QDRANT_BACKUP_FOLDER_ID
    else:
        raise ValueError("Invalid backup type. Use 'sqlite' or 'qdrant'.")

    # --------------------------------------------------
    # DELETE OLD FILE FIRST
    # --------------------------------------------------

    delete_existing_file(service, folder_id, filename)

    # --------------------------------------------------
    # PREPARE UPLOAD
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
    # UPLOAD FILE
    # --------------------------------------------------

    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id",
        ).execute()

        print(f"Uploaded successfully: {filename}")
        print(f"Drive File ID: {file.get('id')}")

    except Exception as e:
        raise RuntimeError(f"Backup upload failed: {e}")