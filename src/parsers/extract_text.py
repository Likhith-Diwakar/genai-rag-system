from googleapiclient.discovery import build
from src.utils.auth import get_credentials
from src.utils.logger import logger


def extract_doc_text(doc_id: str) -> str:
    logger.info(f"Extracting text from Google Doc: {doc_id}")

    creds = get_credentials()
    docs_service = build("docs", "v1", credentials=creds)
    document = docs_service.documents().get(documentId=doc_id).execute()

    text_parts = []

    for element in document.get("body", {}).get("content", []):
        if "paragraph" in element:
            for run in element["paragraph"].get("elements", []):
                if "textRun" in run:
                    text_parts.append(run["textRun"]["content"])

    text = "".join(text_parts)
    logger.debug(f"Extracted {len(text)} characters")

    return text