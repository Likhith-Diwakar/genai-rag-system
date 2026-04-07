import os
import json
import re
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

IS_RENDER = bool(os.environ.get("RENDER") or os.environ.get("IS_RENDER"))


# --------------------------------------------------
# ROBUST JSON PARSER
# --------------------------------------------------

def _parse_service_account_json(raw: str) -> dict:
    """
    Render corrupts JSON env vars in multiple ways.
    Tries every known fix strategy before giving up.
    """

    # Strategy 1: parse as-is
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Strategy 2: double-escaped newlines \\n -> \n
    try:
        return json.loads(raw.replace("\\\\n", "\\n"))
    except Exception:
        pass

    # Strategy 3: actual newline characters -> \n escape
    try:
        fixed = raw.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")
        return json.loads(fixed)
    except Exception:
        pass

    # Strategy 4: fix only the private key block (most common Render issue)
    # Real newlines inside the private key value corrupt the JSON
    try:
        def escape_key_newlines(match):
            return match.group(0).replace("\n", "\\n").replace("\r", "")

        fixed = re.sub(
            r'-----BEGIN PRIVATE KEY-----.*?-----END PRIVATE KEY-----',
            escape_key_newlines,
            raw,
            flags=re.DOTALL
        )
        return json.loads(fixed)
    except Exception:
        pass

    # Strategy 5: base64-encoded JSON
    try:
        return json.loads(base64.b64decode(raw).decode("utf-8"))
    except Exception:
        pass

    raise ValueError(
        f"Could not parse GOOGLE_SERVICE_ACCOUNT_JSON. "
        f"First 100 chars: {raw[:100]!r}"
    )


# --------------------------------------------------
# SERVICE ACCOUNT (CI)
# --------------------------------------------------

def _load_service_account():
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not sa_json:
        logger.warning("GOOGLE_SERVICE_ACCOUNT_JSON env var is not set")
        return None

    try:
        logger.info("Using Service Account authentication (CI mode)")
        creds_dict = _parse_service_account_json(sa_json)
        return service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=SCOPES
        )

    except Exception as e:
        logger.error(f"Failed to load service account: {e}")
        return None


# --------------------------------------------------
# OAUTH FROM ENV (CI)
# --------------------------------------------------

def _load_token_from_env():
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
    if not os.path.exists(TOKEN_FILE):
        return None

    try:
        logger.info("Loading OAuth token from local file")
        return Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    except Exception as e:
        logger.error(f"Failed to load token from file: {e}")
        return None


# --------------------------------------------------
# SAVE TOKEN
# --------------------------------------------------

def _save_token(creds):
    try:
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
        logger.info("OAuth token saved locally")
    except Exception as e:
        logger.error(f"Failed to save token: {e}")


# --------------------------------------------------
# MAIN ENTRY
# --------------------------------------------------

def get_credentials(force_oauth=False):
    """
    Unified credential loader.

    Modes:
    - Default: Service Account → OAuth token fallback
    - force_oauth=True: Skip service account, use OAuth token only

    On Render: interactive OAuth is blocked — no browser available.
    """

    creds = None

    # ==================================================
    # 0. FORCE OAUTH (for backup uploads)
    # ==================================================
    if force_oauth:
        creds = _load_token_from_env() or _load_token_from_file()

        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("Refreshing OAuth token (forced mode)")
                creds.refresh(Request())
                _save_token(creds)
                return creds
            except Exception as e:
                logger.error(f"Forced OAuth refresh failed: {e}")

        if IS_RENDER:
            raise RuntimeError(
                "Force OAuth failed on Render. "
                "Set GOOGLE_DRIVE_TOKEN env var with a valid base64-encoded token."
            )

    # ==================================================
    # 1. SERVICE ACCOUNT (CI default)
    # ==================================================
    if not force_oauth:
        creds = _load_service_account()
        if creds:
            return creds

    # ==================================================
    # 2. OAUTH TOKEN (ENV / LOCAL)
    # ==================================================
    creds = _load_token_from_env() or _load_token_from_file()

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
    # 3. INTERACTIVE LOGIN (LOCAL ONLY — never on Render)
    # ==================================================

    if IS_RENDER:
        raise RuntimeError(
            "All Google authentication methods failed on Render.\n"
            "Fix: check that GOOGLE_SERVICE_ACCOUNT_JSON is set correctly "
            "in your Render environment variables."
        )

    logger.info("Starting OAuth login flow (local only)")

    if not os.path.exists(CREDS_FILE):
        raise FileNotFoundError(
            "credentials.json not found. Required for OAuth login."
        )

    flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)

    creds = flow.run_local_server(
        port=0,
        access_type="offline",
        prompt="consent"
    )

    _save_token(creds)
    return creds