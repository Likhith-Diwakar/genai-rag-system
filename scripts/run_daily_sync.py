import os
import sys
from datetime import datetime
import pytz

# --------------------------------------------------
# FIX PROJECT ROOT PATH (Works from anywhere)
# --------------------------------------------------

# scripts/ folder path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# project root (one level up from scripts/)
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

# insert project root at start of Python path
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --------------------------------------------------
# Now imports will work correctly
# --------------------------------------------------

from src.ingestion.main import run_sync

TIMEZONE = "Asia/Kolkata"

# --------------------------------------------------
# Logging Setup
# --------------------------------------------------

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "daily_sync.log")


def log(message):
    timestamp = datetime.now(pytz.timezone(TIMEZONE))
    full_message = f"[{timestamp}] {message}"
    print(full_message)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_message + "\n")


def run_daily_sync():
    log("Starting scheduled sync...")

    try:
        run_sync(verbose=True)
        log("Sync completed successfully.")
    except Exception as e:
        log(f"Sync failed: {e}")


if __name__ == "__main__":
    run_daily_sync()