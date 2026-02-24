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

from src.ingestion.main import run_sync
from scripts.backup_sqlite import backup_sqlite
from scripts.backup_chroma import backup_chroma
from scripts.upload_backup_to_drive import upload_backup

# ----------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------

TIMEZONE = pytz.timezone("Asia/Kolkata")

# Only ONE schedule time (for sync)
SYNC_HOUR = 11
SYNC_MINUTE = 20

# Delay (in seconds) between steps
STEP_DELAY_SECONDS = 180  # 3 minutes

# ----------------------------------------------------------
# PIPELINE JOB (ORDER GUARANTEED)
# ----------------------------------------------------------

def run_full_pipeline():
    print("========================================")
    print(f"[{datetime.now(TIMEZONE)}] Daily Pipeline Started")
    print("========================================")

    # ------------------------------------------------------
    # STEP 1: DRIVE SYNC (MANDATORY)
    # ------------------------------------------------------

    print(f"[{datetime.now(TIMEZONE)}] Starting Drive Sync...")
    try:
        run_sync(verbose=True)
        print(f"[{datetime.now(TIMEZONE)}] Drive Sync completed.")
    except Exception as e:
        print(f"[{datetime.now(TIMEZONE)}] Drive Sync failed: {e}")
        print("Pipeline stopped. Backups will NOT run.")
        return  # STOP PIPELINE

    # ------------------------------------------------------
    # STEP 2: SQLITE BACKUP (OPTIONAL CONTINUE)
    # ------------------------------------------------------

    print(f"Waiting {STEP_DELAY_SECONDS} seconds before SQLite backup...")
    time.sleep(STEP_DELAY_SECONDS)

    print(f"[{datetime.now(TIMEZONE)}] Starting SQLite Backup...")
    try:
        file_path = backup_sqlite()
        upload_backup(file_path, "sqlite")
        print(f"[{datetime.now(TIMEZONE)}] SQLite Backup completed.")
    except Exception as e:
        print(f"[{datetime.now(TIMEZONE)}] SQLite Backup failed: {e}")
        print("Continuing to Chroma backup...")

    # ------------------------------------------------------
    # STEP 3: CHROMA BACKUP (ALWAYS AFTER SQLITE ATTEMPT)
    # ------------------------------------------------------

    print(f"Waiting {STEP_DELAY_SECONDS} seconds before Chroma backup...")
    time.sleep(STEP_DELAY_SECONDS)

    print(f"[{datetime.now(TIMEZONE)}] Starting Chroma Backup...")
    try:
        file_path = backup_chroma()
        upload_backup(file_path, "chroma")
        print(f"[{datetime.now(TIMEZONE)}] Chroma Backup completed.")
    except Exception as e:
        print(f"[{datetime.now(TIMEZONE)}] Chroma Backup failed: {e}")

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
    print("Order: Sync → SQLite → Chroma")
    print("========================================")

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("Scheduler stopped cleanly.")


if __name__ == "__main__":
    start_scheduler()