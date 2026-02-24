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

SYNC_HOUR = 15
SYNC_MINUTE = 5

SQLITE_BACKUP_HOUR = 15
SQLITE_BACKUP_MINUTE = 10

CHROMA_BACKUP_HOUR = 15
CHROMA_BACKUP_MINUTE = 15

# ----------------------------------------------------------
# JOBS
# ----------------------------------------------------------

def run_drive_sync():
    print(f"[{datetime.now(TIMEZONE)}] Starting Drive Sync...")
    try:
        run_sync(verbose=True)
        print(f"[{datetime.now(TIMEZONE)}] Drive Sync completed.")
    except Exception as e:
        print(f"[{datetime.now(TIMEZONE)}] Drive Sync failed: {e}")


def run_sqlite_backup():
    print(f"[{datetime.now(TIMEZONE)}] Starting SQLite Backup...")
    try:
        file_path = backup_sqlite()
        upload_backup(file_path, "sqlite")
        print(f"[{datetime.now(TIMEZONE)}] SQLite Backup completed.")
    except Exception as e:
        print(f"[{datetime.now(TIMEZONE)}] SQLite Backup failed: {e}")


def run_chroma_backup():
    print(f"[{datetime.now(TIMEZONE)}] Starting Chroma Backup...")
    try:
        file_path = backup_chroma()
        upload_backup(file_path, "chroma")
        print(f"[{datetime.now(TIMEZONE)}] Chroma Backup completed.")
    except Exception as e:
        print(f"[{datetime.now(TIMEZONE)}] Chroma Backup failed: {e}")

# ----------------------------------------------------------
# START SCHEDULER
# ----------------------------------------------------------

def start_scheduler():
    scheduler = BackgroundScheduler(timezone=TIMEZONE)

    scheduler.add_job(
        run_drive_sync,
        CronTrigger(hour=SYNC_HOUR, minute=SYNC_MINUTE),
        id="drive_sync",
        replace_existing=True,
    )

    scheduler.add_job(
        run_sqlite_backup,
        CronTrigger(hour=SQLITE_BACKUP_HOUR, minute=SQLITE_BACKUP_MINUTE),
        id="sqlite_backup",
        replace_existing=True,
    )

    scheduler.add_job(
        run_chroma_backup,
        CronTrigger(hour=CHROMA_BACKUP_HOUR, minute=CHROMA_BACKUP_MINUTE),
        id="chroma_backup",
        replace_existing=True,
    )

    scheduler.start()

    print("========================================")
    print("Scheduler Started (IST)")
    print(f"Drive Sync    : {SYNC_HOUR:02d}:{SYNC_MINUTE:02d}")
    print(f"SQLite Backup : {SQLITE_BACKUP_HOUR:02d}:{SQLITE_BACKUP_MINUTE:02d}")
    print(f"Chroma Backup : {CHROMA_BACKUP_HOUR:02d}:{CHROMA_BACKUP_MINUTE:02d}")
    print("========================================")

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("Scheduler stopped cleanly.")


if __name__ == "__main__":
    start_scheduler()