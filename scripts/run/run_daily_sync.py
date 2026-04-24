import os
import sys
import traceback
from datetime import datetime
import pytz

# --------------------------------------------------
# FIX PROJECT ROOT PATH
# --------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# --------------------------------------------------
# IMPORT BUSINESS LOGIC
# --------------------------------------------------
from pipeline.ingestion.main import run_sync
from scripts.backup.backup_sqlite import backup_sqlite
from scripts.backup.backup_qdrant import backup_qdrant
from scripts.backup.upload_backup_to_drive import upload_backup

TIMEZONE = "Asia/Kolkata"

# --------------------------------------------------
# LOGGING
# --------------------------------------------------
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "daily_sync.log")


def log(message: str) -> None:
    timestamp = datetime.now(pytz.timezone(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S %Z")
    full_message = f"[{timestamp}] {message}"
    print(full_message, flush=True)          # flush=True keeps GitHub Actions logs live
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_message + "\n")


# --------------------------------------------------
# MAIN PIPELINE
# --------------------------------------------------
def run_daily_sync() -> None:
    log("========================================")
    log("Daily Pipeline Started")
    log("========================================")

    # ── STEP 1: Drive Sync ───────────────────────────────────────────────
    # This step is critical — if it fails the backups are pointless,
    # so we stop the whole pipeline on failure.
    log("STEP 1/3 — Drive Sync")
    try:
        run_sync(verbose=True)
        log("Drive Sync completed successfully.")
    except Exception as e:
        log(f"Drive Sync FAILED: {e}")
        log(traceback.format_exc())
        log("Pipeline stopped — backup steps skipped.")
        sys.exit(1)          # non-zero exit marks the GitHub Actions job as failed

    # ── STEP 2: SQLite Backup ────────────────────────────────────────────
    # Non-critical — a backup failure should NOT block the Qdrant backup.
    log("STEP 2/3 — SQLite Backup")
    try:
        sqlite_path = backup_sqlite()
        log(f"SQLite backup created at: {sqlite_path}")
        upload_backup(sqlite_path, "sqlite")
        log("SQLite Backup uploaded successfully.")
    except Exception as e:
        log(f"SQLite Backup FAILED: {e}")
        log(traceback.format_exc())
        log("Continuing pipeline — Qdrant backup will still run.")

    # ── STEP 3: Qdrant Snapshot Backup ───────────────────────────────────
    log("STEP 3/3 — Qdrant Backup")
    try:
        qdrant_path = backup_qdrant()
        log(f"Qdrant snapshot created at: {qdrant_path}")
        upload_backup(qdrant_path, "qdrant")
        log("Qdrant Backup uploaded successfully.")
    except Exception as e:
        log(f"Qdrant Backup FAILED: {e}")
        log(traceback.format_exc())

    log("========================================")
    log("Daily Pipeline Finished")
    log("========================================")


if __name__ == "__main__":
    run_daily_sync()
