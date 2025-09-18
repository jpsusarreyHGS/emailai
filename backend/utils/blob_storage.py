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

  def upload_image(self, image_data: bytes, blob_name: str, container: str | None = None, content_type: str | None = None) -> str:
    """
    Upload an image file (as bytes) to blob storage.

    Args:
        image_data: The image data as bytes (e.g., from Graph API attachment)
        blob_name: The name/path for the blob (e.g., "images/receipt-001.jpg")
        container: Optional container name (defaults to default container)
        content_type: Optional content type (e.g., "image/jpeg", "image/png")

    Returns:
        The blob reference that can be used to retrieve the image
    """
    container = container or self._default_container
    bc = self._svc.get_blob_client(container=container, blob=blob_name)

    # Set content type if provided for proper display in browsers
    content_settings = None
    if content_type:
      from azure.storage.blob import ContentSettings
      content_settings = ContentSettings(content_type=content_type)

    bc.upload_blob(image_data, overwrite=True, content_settings=content_settings)

    # Return a reference that can be used with other methods
    return f"{blob_name}"
