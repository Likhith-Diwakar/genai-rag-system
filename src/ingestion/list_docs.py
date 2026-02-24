# src/ingestion/list_docs.py

from googleapiclient.discovery import build
from src.utils.auth import get_credentials
from src.utils.logger import logger

GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"
CSV_MIME = "text/csv"

#  Your Target Folder
TARGET_FOLDER_ID = "1xs66Xr4CGmK3ikgL7xXcyDwbFfwy6NnW"


def list_drive_documents():
    """
    Fetch ONLY files inside TARGET_FOLDER_ID
    for:
        - Google Docs
        - DOCX
        - PDF
        - CSV
    """

    logger.info("Fetching documents ONLY from target folder")

    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    query = (
        f"('{TARGET_FOLDER_ID}' in parents) and "
        f"(mimeType='{GOOGLE_DOC_MIME}' "
        f"or mimeType='{DOCX_MIME}' "
        f"or mimeType='{PDF_MIME}' "
        f"or mimeType='{CSV_MIME}') "
        f"and trashed=false"
    )

    results = service.files().list(
        q=query,
        fields="files(id, name, mimeType, parents)",
        pageSize=100,
    ).execute()

    files = results.get("files", [])

    logger.info(f"Found {len(files)} documents in target folder")

    for f in files:
        logger.debug(f"{f['name']} | {f['mimeType']} | {f['id']}")

    return files