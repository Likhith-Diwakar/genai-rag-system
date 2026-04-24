import os
import sys
import time
from datetime import datetime

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# ----------------------------------------------------------
# FIX PYTHON PATH
# ----------------------------------------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ----------------------------------------------------------
# IMPORT BUSINESS LOGIC
# ----------------------------------------------------------

from pipeline.ingestion.main import run_sync
from scripts.backup_sqlite import backup_sqlite
from scripts.backup_qdrant import backup_qdrant
from scripts.upload_backup_to_drive import upload_backup

# ----------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------

TIMEZONE = pytz.timezone("Asia/Kolkata")

SYNC_HOUR = 14
SYNC_MINUTE = 00

STEP_DELAY_SECONDS = 20  # 2 minutes delay between steps

# ----------------------------------------------------------
# PIPELINE JOB
# ----------------------------------------------------------

def run_full_pipeline():
    print("========================================")
    print(f"[{datetime.now(TIMEZONE)}] Daily Pipeline Started")
    print("========================================")

    # ------------------------------------------------------
    # STEP 1: DRIVE SYNC
    # ------------------------------------------------------

    print(f"[{datetime.now(TIMEZONE)}] Starting Drive Sync...")
    try:
        run_sync(verbose=True)
        print(f"[{datetime.now(TIMEZONE)}] Drive Sync completed.")
    except Exception as e:
        print(f"[{datetime.now(TIMEZONE)}] Drive Sync failed: {e}")
        print("Pipeline stopped. Backups will NOT run.")
        return

    # ------------------------------------------------------
    # STEP 2: SQLITE BACKUP
    # ------------------------------------------------------

    print(f"Waiting {STEP_DELAY_SECONDS} seconds before SQLite backup...")
    time.sleep(STEP_DELAY_SECONDS)

    print(f"[{datetime.now(TIMEZONE)}] Starting SQLite Backup...")
    try:
        sqlite_path = backup_sqlite()
        upload_backup(sqlite_path, "sqlite")
        print(f"[{datetime.now(TIMEZONE)}] SQLite Backup completed.")
    except Exception as e:
        print(f"[{datetime.now(TIMEZONE)}] SQLite Backup failed: {e}")

    # ------------------------------------------------------
    # STEP 3: QDRANT SNAPSHOT BACKUP
    # ------------------------------------------------------

    print(f"Waiting {STEP_DELAY_SECONDS} seconds before Qdrant backup...")
    time.sleep(STEP_DELAY_SECONDS)

    print(f"[{datetime.now(TIMEZONE)}] Starting Qdrant Backup...")
    try:
        qdrant_path = backup_qdrant()
        upload_backup(qdrant_path, "qdrant")
        print(f"[{datetime.now(TIMEZONE)}] Qdrant Backup completed.")
    except Exception as e:
        print(f"[{datetime.now(TIMEZONE)}] Qdrant Backup failed: {e}")

    print("========================================")
    print(f"[{datetime.now(TIMEZONE)}] Daily Pipeline Finished")
    print("========================================")


# ----------------------------------------------------------
# START SCHEDULER
# ----------------------------------------------------------

def start_scheduler():
    scheduler = BackgroundScheduler(timezone=TIMEZONE)

    scheduler.add_job(
        run_full_pipeline,
        CronTrigger(hour=SYNC_HOUR, minute=SYNC_MINUTE),
        id="daily_pipeline",
        replace_existing=True,
    )

    scheduler.start()

    print("========================================")
    print("Scheduler Started (IST)")
    print(f"Daily Pipeline Time : {SYNC_HOUR:02d}:{SYNC_MINUTE:02d}")
    print("Order: Sync → SQLite → Qdrant")
    print("========================================")

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("Scheduler stopped cleanly.")


if __name__ == "__main__":
    start_scheduler()
