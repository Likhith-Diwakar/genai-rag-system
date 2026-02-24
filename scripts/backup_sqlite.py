import os
import pickle
import gzip
from datetime import datetime

# --------------------------------------------------
# PROJECT ROOT
# --------------------------------------------------

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

# SQLite DB path
SQLITE_DB_PATH = os.path.join(PROJECT_ROOT, "data", "tracker.db")

# Backup folder
BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

# --------------------------------------------------
# BACKUP FUNCTION
# --------------------------------------------------

def backup_sqlite():
    if not os.path.exists(SQLITE_DB_PATH):
        raise FileNotFoundError("SQLite DB not found.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(
        BACKUP_DIR, f"tracker_backup_{timestamp}.pkl.gz"
    )

    with open(SQLITE_DB_PATH, "rb") as f:
        db_bytes = f.read()

    with gzip.open(backup_file, "wb") as f:
        pickle.dump(db_bytes, f)

    print(f"Backup created successfully: {backup_file}")

    return backup_file


if __name__ == "__main__":
    backup_sqlite()