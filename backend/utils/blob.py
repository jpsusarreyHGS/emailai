# backend/utils/blob.py
import os
from azure.storage.blob import BlobServiceClient

def _blob_client():
    conn = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    return BlobServiceClient.from_connection_string(conn)

def download_blob_bytes(ref: str) -> bytes:
    """
    Accepts either '<folder>/<blob>' inside the default container,
    or a full https URL to the blob.
    """
    svc = _blob_client()
    default_container = os.environ["BLOB_CONTAINER_EMAIL_ATTACHMENTS"]

    if ref.startswith("http"):
        from urllib.parse import urlparse
        u = urlparse(ref)
        parts = u.path.lstrip("/").split("/", 2)  # [container, maybe folder, blob]
        if len(parts) < 2:
            raise ValueError("Blob URL must contain /<container>/<blob>")
        container = parts[0]
        blob = "/".join(parts[1:])
    else:
        container = default_container
        blob = ref  # e.g. "email1/receipt-001.jpg"

    return svc.get_blob_client(container=container, blob=blob).download_blob().readall()
