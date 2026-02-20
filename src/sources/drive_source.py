# src/list_docs.py

from googleapiclient.discovery import build
from src.utils.auth import get_credentials
from src.utils.logger import logger

GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"
CSV_MIME = "text/csv"

PDF_FOLDER_ID = "1xs66Xr4CGmK3ikgL7xXcyDwbFfwy6NnW"


def list_drive_documents():
    """
    - Google Docs & DOCX: from entire Drive
    - PDFs & CSV: ONLY from specific test folder
    """

    logger.info("Fetching Docs, DOCX (global) and PDFs/CSVs (folder-scoped) from Drive")

    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    # Docs + DOCX (entire Drive)
    doc_query = (
        f"(mimeType='{GOOGLE_DOC_MIME}' "
        f"or mimeType='{DOCX_MIME}') "
        f"and trashed=false"
    )

    # PDFs + CSV (ONLY from specific folder)
    folder_query = (
        f"('{PDF_FOLDER_ID}' in parents) and "
        f"(mimeType='{PDF_MIME}' or mimeType='{CSV_MIME}') "
        f"and trashed=false"
    )

    files = []

    # Fetch Docs & DOCX
    doc_results = service.files().list(
        q=doc_query,
        fields="files(id, name, mimeType)",
        pageSize=100,
    ).execute()

    files.extend(doc_results.get("files", []))

    # Fetch PDFs + CSV
    folder_results = service.files().list(
        q=folder_query,
        fields="files(id, name, mimeType)",
        pageSize=100,
    ).execute()

    files.extend(folder_results.get("files", []))

    logger.info(f"Found {len(files)} total documents")

    for f in files:
        logger.debug(f"{f['name']} | {f['mimeType']} | {f['id']}")

    return files
