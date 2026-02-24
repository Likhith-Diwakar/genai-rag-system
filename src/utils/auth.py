import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# --------------------------------------------------
# UPDATED SCOPES (READ + WRITE ACCESS)
# --------------------------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/drive",  # Full Drive access
    "https://www.googleapis.com/auth/documents.readonly"
]

TOKEN_FILE = "token.json"
CREDS_FILE = "credentials.json"


def get_credentials():
    creds = None

    # Load existing token
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If credentials invalid or expired
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds