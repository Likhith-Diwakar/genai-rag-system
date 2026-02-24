import os
import tarfile
from datetime import datetime

# --------------------------------------------------
# PROJECT ROOT
# --------------------------------------------------

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

CHROMA_DIR = os.path.join(PROJECT_ROOT, "data", "chroma")

BACKUP_DIR = os.path.join(PROJECT_ROOT, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


def backup_chroma():
    if not os.path.exists(CHROMA_DIR):
        raise FileNotFoundError("Chroma directory not found.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(
        BACKUP_DIR,
        f"chroma_backup_{timestamp}.tar.gz"
    )

    with tarfile.open(backup_file, "w:gz") as tar:
        tar.add(CHROMA_DIR, arcname="chroma")

    print(f"Chroma backup created successfully: {backup_file}")

    return backup_file


if __name__ == "__main__":
    backup_chroma()