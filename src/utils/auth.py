import os
import json
import base64
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


# --------------------------------------------------
# SERVICE ACCOUNT (CI)
# --------------------------------------------------

def _load_service_account():
    """
    Load service account credentials from environment (GitHub Actions).
    """
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not sa_json:
        return None

    try:
        logger.info("Using Service Account authentication (CI mode)")

        creds_dict = json.loads(sa_json)

        return service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES
        )

    except Exception as e:
        logger.error(f"Failed to load service account: {e}")
        return None


# --------------------------------------------------
# OAUTH FROM ENV (CI fallback)
# --------------------------------------------------

def _load_token_from_env():
    """
    Load OAuth token from base64-encoded GitHub secret.
    """
    token_base64 = os.getenv("GOOGLE_DRIVE_TOKEN")

    if not token_base64:
        return None

    try:
        logger.info("Loading OAuth token from environment")

        decoded = base64.b64decode(token_base64).decode("utf-8")
        token_data = json.loads(decoded)

        return Credentials.from_authorized_user_info(token_data, SCOPES)

    except Exception as e:
        logger.error(f"Failed to load token from environment: {e}")
        return None


# --------------------------------------------------
# OAUTH FROM LOCAL FILE
# --------------------------------------------------

def _load_token_from_file():
    """
    Load OAuth token from local file.
    """
    if not os.path.exists(TOKEN_FILE):
        return None

    try:
        logger.info("Loading OAuth token from local file")

        return Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    except Exception as e:
        logger.error(f"Failed to load token from file: {e}")
        return None


# --------------------------------------------------
# SAVE TOKEN (LOCAL)
# --------------------------------------------------

def _save_token(creds):
    """
    Save OAuth token locally.
    """
    try:
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
        logger.info("OAuth token saved locally")
    except Exception as e:
        logger.error(f"Failed to save token: {e}")


# --------------------------------------------------
# MAIN ENTRY
# --------------------------------------------------

def get_credentials():
    """
    Unified credential loader.

    Priority:
    1. Service Account (CI)
    2. OAuth token from environment
    3. OAuth token from local file
    4. OAuth login flow (local only)
    """

    # ==================================================
    # 1. SERVICE ACCOUNT (CI)
    # ==================================================
    creds = _load_service_account()
    if creds:
        return creds

    # ==================================================
    # 2. OAUTH TOKEN FROM ENV
    # ==================================================
    creds = _load_token_from_env()

    # ==================================================
    # 3. OAUTH TOKEN FROM LOCAL FILE
    # ==================================================
    if not creds:
        creds = _load_token_from_file()

    # ==================================================
    # 4. VALIDATE / REFRESH
    # ==================================================
    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            logger.info("Refreshing expired OAuth token")
            creds.refresh(Request())
            _save_token(creds)
            return creds
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")

    # ==================================================
    # 5. INTERACTIVE LOGIN (LOCAL ONLY)
    # ==================================================
    logger.info("Starting OAuth login flow (local only)")

    if not os.path.exists(CREDS_FILE):
        raise FileNotFoundError(
            "credentials.json not found. Required for OAuth login."
        )

    flow = InstalledAppFlow.from_client_secrets_file(
        CREDS_FILE,
        SCOPES,
    )

    creds = flow.run_local_server(port=0)

    _save_token(creds)

    return creds