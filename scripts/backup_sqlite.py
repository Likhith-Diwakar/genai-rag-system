import os
import pickle
import gzip

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

# Must match exactly where TrackerDB writes: demo/backend/data/tracker.db
SQLITE_DB_PATH = os.path.join(PROJECT_ROOT, "demo", "backend", "data", "tracker.db")
BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


def backup_sqlite():
    if not os.path.exists(SQLITE_DB_PATH):
        raise FileNotFoundError(f"SQLite DB not found at: {SQLITE_DB_PATH}")

    backup_file = os.path.join(BACKUP_DIR, "sqlite_latest.pkl.gz")

    with open(SQLITE_DB_PATH, "rb") as f:
        db_bytes = f.read()

    with gzip.open(backup_file, "wb") as f:
        pickle.dump(db_bytes, f)

    print(f"SQLite backup updated (pickled): {backup_file}")
    return backup_file


if __name__ == "__main__":
    backup_sqlite()
