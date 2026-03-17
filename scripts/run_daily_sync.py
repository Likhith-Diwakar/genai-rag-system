import os
import sys
from datetime import datetime
import pytz

# --------------------------------------------------
# FIX PROJECT ROOT PATH
# --------------------------------------------------

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --------------------------------------------------
# IMPORT BUSINESS LOGIC
# --------------------------------------------------

from src.ingestion.main import run_sync
from scripts.backup_sqlite import backup_sqlite
from scripts.backup_qdrant import backup_qdrant
from scripts.upload_backup_to_drive import upload_backup

TIMEZONE = "Asia/Kolkata"

# --------------------------------------------------
# LOGGING
# --------------------------------------------------

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "daily_sync.log")


def log(message):
    timestamp = datetime.now(pytz.timezone(TIMEZONE))
    full_message = f"[{timestamp}] {message}"
    print(full_message, flush=True)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_message + "\n")


# --------------------------------------------------
# MAIN PIPELINE
# --------------------------------------------------

def run_daily_sync():

    log("========================================")
    log("Daily Pipeline Started")
    log("========================================")

    # STEP 1: DRIVE SYNC
    try:
        log("Starting Drive Sync...")
        run_sync(verbose=True)
        log("Drive Sync completed.")
    except Exception as e:
        log(f"Drive Sync failed: {e}")
        log("Pipeline stopped.")
        return

    # STEP 2: SQLITE BACKUP
    try:
        log("Starting SQLite Backup...")
        sqlite_path = backup_sqlite()
        upload_backup(sqlite_path, "sqlite")
        log("SQLite Backup completed.")
    except Exception as e:
        log(f"SQLite Backup failed: {e}")

    # STEP 3: QDRANT BACKUP
    try:
        log("Starting Qdrant Backup...")
        qdrant_path = backup_qdrant()
        upload_backup(qdrant_path, "qdrant")
        log("Qdrant Backup completed.")
    except Exception as e:
        log(f"Qdrant Backup failed: {e}")

    log("========================================")
    log("Daily Pipeline Finished")
    log("========================================")


if __name__ == "__main__":
    run_daily_sync()
