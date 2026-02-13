# src/download_file.py
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from src.auth import get_credentials
from src.logger import logger
import io
import os


def download_drive_file(file_id: str, file_name: str, out_dir="data/tmp") -> str:
    os.makedirs(out_dir, exist_ok=True)

    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)

    done = False
    while not done:
        _, done = downloader.next_chunk()

    local_path = os.path.join(out_dir, file_name)
    with open(local_path, "wb") as f:
        f.write(fh.getvalue())

    logger.info(f"Downloaded file: {file_name}")
    return local_path
