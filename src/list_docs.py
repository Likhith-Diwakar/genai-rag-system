from googleapiclient.discovery import build
from src.auth import get_credentials


def list_google_docs():
    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    results = service.files().list(
        q="mimeType='application/vnd.google-apps.document' and trashed=false",
        fields="files(id, name)",
        pageSize=50
    ).execute()

    files = results.get("files", [])

    if not files:
        print("No Google Docs found.")
        return []

    print("Google Docs in your Drive:\n")
    for f in files:
        print(f"{f['name']}  ->  {f['id']}")

 
    return files


if __name__ == "__main__":
    list_google_docs()