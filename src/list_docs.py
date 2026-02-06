# src/list_docs.py

from googleapiclient.discovery import build
from src.auth import get_credentials
from src.logger import logger

GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def list_drive_documents():
    """
    Lists all Google Docs and DOCX files in Google Drive.
    Folder location does NOT matter.
    """
    logger.info("Fetching Google Docs and DOCX files from Drive")

    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    query = (
        f"(mimeType='{GOOGLE_DOC_MIME}' "
        f"or mimeType='{DOCX_MIME}') "
        f"and trashed=false"
    )

    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType)",
        pageSize=100,
    ).execute()

    files = results.get("files", [])
    logger.info(f"Found {len(files)} documents")

    for f in files:
        logger.debug(f"{f['name']} | {f['mimeType']} | {f['id']}")

    return files
