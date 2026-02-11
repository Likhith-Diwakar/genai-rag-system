# src/list_docs.py

from googleapiclient.discovery import build
from src.auth import get_credentials
from src.logger import logger

GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME = "application/pdf"

PDF_FOLDER_ID = "1xs66Xr4CGmK3ikgL7xXcyDwbFfwy6NnW"


def list_drive_documents():
    """
    - Google Docs & DOCX: from entire Drive
    - PDFs: ONLY from a specific folder
    """
    logger.info("Fetching Docs, DOCX (global) and PDFs (folder-scoped) from Drive")

    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    # Docs + DOCX (entire Drive)
    doc_query = (
        f"(mimeType='{GOOGLE_DOC_MIME}' "
        f"or mimeType='{DOCX_MIME}') "
        f"and trashed=false"
    )

    # PDFs (ONLY from specific folder)
    pdf_query = (
        f"mimeType='{PDF_MIME}' "
        f"and '{PDF_FOLDER_ID}' in parents "
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

    # Fetch PDFs from folder
    pdf_results = service.files().list(
        q=pdf_query,
        fields="files(id, name, mimeType)",
        pageSize=100,
    ).execute()

    files.extend(pdf_results.get("files", []))

    logger.info(f"Found {len(files)} total documents")

    for f in files:
        logger.debug(f"{f['name']} | {f['mimeType']} | {f['id']}")

    return files
