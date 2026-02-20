from azure.storage.blob import BlobServiceClient
from src.sources.base import BaseSource
from src.utils.logger import logger
import os


class AzureBlobSource(BaseSource):

    def __init__(self):
        self.connection_string = os.getenv("AZURE_BLOB_CONNECTION_STRING")
        self.container_name = os.getenv("AZURE_BLOB_CONTAINER")

        if not self.connection_string or not self.container_name:
            raise ValueError("Azure Blob env variables not set")

        self.client = BlobServiceClient.from_connection_string(
            self.connection_string
        )

        self.container = self.client.get_container_client(self.container_name)

    def list_files(self):
        logger.info("Fetching files from Azure Blob")

        blobs = self.container.list_blobs()

        files = []

        for blob in blobs:
            files.append({
                "id": blob.name,  # blob name acts as file_id
                "name": blob.name,
                "mimeType": self._infer_mime(blob.name)
            })

        logger.info(f"Found {len(files)} blobs")

        return files

    def download_file(self, file_id, destination):
        logger.info(f"Downloading blob → {file_id}")

        blob_client = self.container.get_blob_client(file_id)

        with open(destination, "wb") as f:
            data = blob_client.download_blob()
            f.write(data.readall())

    def _infer_mime(self, filename):
        filename = filename.lower()

        if filename.endswith(".pdf"):
            return "application/pdf"
        elif filename.endswith(".docx"):
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif filename.endswith(".csv"):
            return "text/csv"
        else:
            return "application/octet-stream"
