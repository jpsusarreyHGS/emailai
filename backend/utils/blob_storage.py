import os
from urllib.parse import urlparse
from azure.storage.blob import BlobServiceClient

class BlobService:
    def __init__(self, conn_str: str | None = None, default_container: str | None = None):
        self._conn = conn_str or os.environ["AZURE_STORAGE_CONNECTION_STRING"]
        self._default_container = default_container or os.environ["BLOB_CONTAINER_EMAIL_ATTACHMENTS"]
        self._svc = BlobServiceClient.from_connection_string(self._conn)

    def _parse(self, ref: str):
        if ref.startswith("http"):
            u = urlparse(ref)
            parts = u.path.lstrip("/").split("/", 1)
            if len(parts) != 2:
                raise ValueError("Blob URL must contain /<container>/<blob>")
            return parts[0], parts[1]
        if "/" in ref:
            c, b = ref.split("/", 1)
            return c, b
        return self._default_container, ref

    def download_bytes(self, ref: str) -> bytes:
        c, b = self._parse(ref)
        bc = self._svc.get_blob_client(container=c, blob=b)
        return bc.download_blob().readall()
