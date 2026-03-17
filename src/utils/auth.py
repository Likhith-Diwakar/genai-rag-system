# src/utils/auth.py

import os
import json
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from src.utils.logger import logger


# --------------------------------------------------
# SCOPES
# --------------------------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents.readonly",
]

TOKEN_FILE = "token.json"
CREDS_FILE = "credentials.json"


def get_credentials():
    """
    Cloud-safe + Local-safe credential loader.

    Priority:
    1️⃣ If GOOGLE_SERVICE_ACCOUNT_JSON exists → use Service Account (env)
    2️⃣ If credentials.json exists (CI) → use Service Account (file)
    3️⃣ Else → fallback to OAuth InstalledAppFlow (Local)
    """

    # ==================================================
    # 1️⃣ SERVICE ACCOUNT VIA ENV (CI preferred)
    # ==================================================

    credentials_json = (
        os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        or os.getenv("GOOGLE_CREDENTIALS_JSON")
    )

    if credentials_json:
        try:
            logger.info(
                "Loading Google credentials from environment variable (Service Account mode)"
            )

            credentials_info = json.loads(credentials_json)

            return service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=SCOPES,
            )

        except Exception as e:
            logger.error(f"Failed loading service account credentials from env: {e}")
            raise

    # ==================================================
    # 2️⃣ SERVICE ACCOUNT VIA FILE (GitHub Actions fallback)
    # ==================================================

    if os.path.exists(CREDS_FILE):
        try:
            logger.info(
                "Loading Google credentials from credentials.json (Service Account mode)"
            )

            return service_account.Credentials.from_service_account_file(
                CREDS_FILE,
                scopes=SCOPES,
            )

        except Exception as e:
            logger.error(f"Failed loading service account credentials from file: {e}")
            raise

    # ==================================================
    # 3️⃣ LOCAL MODE (OAuth flow)
    # ==================================================

    logger.info("Using local OAuth flow for Google authentication")

    creds = None

    # Load existing token
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If credentials invalid or expired
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_FILE):
                raise FileNotFoundError(
                    "credentials.json not found for local OAuth flow."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                CREDS_FILE,
                SCOPES,
            )
            creds = flow.run_local_server(port=0)

        # Save token locally
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds