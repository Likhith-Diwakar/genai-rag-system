import os
import sys
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
CHROMA_BACKUP_FOLDER_ID = "1UzLrdaBuo96xnyvzc0ArqAm9Pn4sh_LG"


def upload_backup(file_path: str, backup_type: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError("Backup file not found.")

    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    filename = os.path.basename(file_path)

    if backup_type == "sqlite":
        folder_id = SQLITE_BACKUP_FOLDER_ID
    elif backup_type == "chroma":
        folder_id = CHROMA_BACKUP_FOLDER_ID
    else:
        raise ValueError("Invalid backup type. Use 'sqlite' or 'chroma'.")

    file_metadata = {
        "name": filename,
        "parents": [folder_id],
    }

    media = MediaFileUpload(
        file_path,
        mimetype="application/gzip",
        resumable=True,
    )

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id",
    ).execute()

    print(f"Uploaded successfully: {filename}")
    print(f"Drive File ID: {file.get('id')}")