import os
import json
import re
import base64
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from src.utils.logger import logger


# --------------------------------------------------
# SCOPES
# --------------------------------------------------

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents.readonly",
]


# --------------------------------------------------
# ROBUST JSON PARSER
# --------------------------------------------------

def _parse_service_account_json(raw: str) -> dict:
    """
    Handles multiple ways env vars get corrupted in CI / Render.
    Tries every known fix strategy before giving up.
    """

    # Strategy 1: parse as-is
    try:
        return json.loads(raw)
    except Exception:
        pass

    # Strategy 2: double-escaped newlines  \\n -> \n
    try:
        return json.loads(raw.replace("\\\\n", "\\n"))
    except Exception:
        pass

    # Strategy 3: literal newline characters -> escaped \n
    try:
        fixed = (
            raw.replace("\r\n", "\\n")
               .replace("\r",   "\\n")
               .replace("\n",   "\\n")
        )
        return json.loads(fixed)
    except Exception:
        pass

    # Strategy 4: fix only the private key block (most common Render / GHA issue)
    try:
        def _escape_key_newlines(match):
            return match.group(0).replace("\n", "\\n").replace("\r", "")

        fixed = re.sub(
            r'-----BEGIN PRIVATE KEY-----.*?-----END PRIVATE KEY-----',
            _escape_key_newlines,
            raw,
            flags=re.DOTALL,
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
        "Could not parse GOOGLE_SERVICE_ACCOUNT_JSON after all fix strategies. "
        f"First 100 chars: {raw[:100]!r}"
    )


# --------------------------------------------------
# SERVICE ACCOUNT LOADER
# --------------------------------------------------

def _load_service_account() -> service_account.Credentials | None:
    """
    Loads service account credentials from GOOGLE_SERVICE_ACCOUNT_JSON.
    Returns None (with a logged warning) if the env var is missing or invalid.
    """
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

    if not sa_json:
        logger.warning(
            "GOOGLE_SERVICE_ACCOUNT_JSON is not set. "
            "Google Drive operations will fail."
        )
        return None

    try:
        logger.info("Authenticating via Service Account (CI / production mode)")
        creds_dict = _parse_service_account_json(sa_json)
        return service_account.Credentials.from_service_account_info(
            creds_dict, scopes=SCOPES
        )
    except Exception as e:
        logger.error(f"Service account authentication failed: {e}")
        return None


# --------------------------------------------------
# LOCAL OAUTH HELPER  (development only)
# --------------------------------------------------

def _load_oauth_local() -> object | None:
    """
    Interactive OAuth flow — works only on a developer machine with a browser.
    Never called in CI (GitHub Actions / Render).
    Requires credentials.json in the project root.
    """
    # Import lazily so CI never needs these packages at import time
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    TOKEN_FILE = "token.json"
    CREDS_FILE = "credentials.json"

    # Try loading a cached token first
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            logger.info("Loaded OAuth token from local token.json")
        except Exception as e:
            logger.warning(f"Could not load token.json: {e}")

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
            logger.info("Refreshed and saved OAuth token")
            return creds
        except Exception as e:
            logger.warning(f"OAuth token refresh failed: {e}")

    # Full browser login
    if not os.path.exists(CREDS_FILE):
        raise FileNotFoundError(
            "credentials.json not found. "
            "Required for local OAuth login — download it from Google Cloud Console."
        )

    logger.info("Starting local OAuth login flow (browser required)")
    flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    logger.info("OAuth token saved to token.json")
    return creds


# --------------------------------------------------
# PUBLIC ENTRY POINT
# --------------------------------------------------

def get_credentials():
    """
    Returns valid Google credentials.

    Resolution order
    ────────────────
    1. Service Account via GOOGLE_SERVICE_ACCOUNT_JSON  ← always tried first
       Works in: GitHub Actions, Render, any CI/CD environment.

    2. Local OAuth flow (developer machines only)
       Triggered only when the service account env var is absent AND
       the runtime is NOT a known CI/CD environment.

    Raises:
        RuntimeError  — service account missing in a CI environment.
        FileNotFoundError — credentials.json missing for local OAuth.
    """

    # ── 1. Service Account (CI + production) ────────────────────────────
    creds = _load_service_account()
    if creds:
        return creds

    # ── 2. Detect CI environment ─────────────────────────────────────────
    is_ci = bool(
        os.environ.get("CI")                # GitHub Actions sets this automatically
        or os.environ.get("GITHUB_ACTIONS")
        or os.environ.get("RENDER")
        or os.environ.get("IS_RENDER")
    )

    if is_ci:
        raise RuntimeError(
            "Google authentication failed in CI environment.\n"
            "Fix: ensure GOOGLE_SERVICE_ACCOUNT_JSON is set correctly "
            "in your GitHub Actions / Render secrets."
        )

    # ── 3. Local OAuth fallback (developer machines only) ────────────────
    logger.info("Service account not found — falling back to local OAuth")
    return _load_oauth_local()