from googleapiclient.discovery import build
from src.auth import get_credentials


def extract_doc_text(doc_id: str) -> str:
    creds = get_credentials()
    docs_service = build("docs", "v1", credentials=creds)

    document = docs_service.documents().get(documentId=doc_id).execute()

    text_parts = []

    for element in document.get("body", {}).get("content", []):
        if "paragraph" in element:
            for run in element["paragraph"].get("elements", []):
                if "textRun" in run:
                    text_parts.append(run["textRun"]["content"])

    return "".join(text_parts)


if __name__ == "__main__":
    #  TEMP test block
    TEST_DOC_ID = "16-UTkZOVl-NmRe4pcOrSJRoWOPw7eJ9Y5L__bVDOkNk"

    content = extract_doc_text(TEST_DOC_ID)
    print(content[:1000])  