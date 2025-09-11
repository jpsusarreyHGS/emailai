from datetime import datetime, timezone
from typing import Tuple, List, Dict, Any
import os
from azure.cosmos import CosmosClient

from utils.blob_storage import BlobService
from utils.ai_ocr import OCRClient

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _compute_ocr_summary(attachments: List[Dict[str, Any]]) -> str:
    if not attachments:
        return "none"
    statuses = [att.get("ocr", {}).get("status") for att in attachments]
    if any(s == "success" for s in statuses) and not any(s in (None, "pending", "failed") for s in statuses):
        return "complete"
    if all(s == "failed" for s in statuses if s is not None) and any(statuses):
        return "failed"
    if any(s == "success" for s in statuses):
        return "partial"
    return "pending"

class CosmosEmailStores:
    def __init__(self):
        db_name = os.environ["COSMOS_DB"]
        self.content_name = os.environ["COSMOS_CONTAINER_CONTENT"]
        self.status_name  = os.environ["COSMOS_CONTAINER_STATUS"]

        conn = os.environ.get("COSMOS_CONNECTION_STRING")
        if conn:
            # Use connection string (your setup)
            self.client = CosmosClient.from_connection_string(conn)
        else:
            # Fallback to endpoint/key if provided
            endpoint = os.environ["COSMOS_ACCOUNT_URI"]
            key = os.environ["COSMOS_KEY"]
            self.client = CosmosClient(endpoint, credential=key)

        db = self.client.get_database_client(db_name)
        self.content = db.get_container_client(self.content_name)
        self.status  = db.get_container_client(self.status_name)


    def get_email_content(self, id: str, pk: str | None = None):
        return self.content.read_item(id, partition_key=pk or id)

    def upsert_email_content(self, doc: dict):
        return self.content.upsert_item(doc)

    def get_email_status(self, id: str, pk: str | None = None):
        return self.status.read_item(id, partition_key=pk or id)

    def upsert_email_status(self, doc: dict):
        return self.status.upsert_item(doc)

def _find_attachment(email_doc: dict, filename: str) -> dict:
    atts = email_doc.get("attachments") or []
    # match by filename first
    for a in atts:
        if a.get("filename") == filename:
            return a
    # fallback: by blob name suffix
    for a in atts:
        bp = a.get("blobPath") or a.get("blobUrl") or ""
        if bp.endswith("/" + filename) or bp == filename:
            return a
    raise ValueError(f"Attachment '{filename}' not found on email {email_doc.get('id')}")

def ocr_attachment(email_id: str, filename: str, pk: str | None = None) -> dict:
    """Run OCR for a single attachment; updates emails-content + emails-status."""
    stores = CosmosEmailStores()
    blob = BlobService()
    ocr = OCRClient()

    doc = stores.get_email_content(email_id, pk=pk or email_id)
    att = _find_attachment(doc, filename)

    ref = att.get("blobPath") or att.get("blobUrl") or filename
    image_bytes = blob.download_bytes(ref)
    text = ocr.extract_text_from_image_bytes(image_bytes).strip()

    att.setdefault("ocr", {})
    att["ocr"].update({
        "status": "success",
        "text": text,
        "engine": "aihub-aoai",
        "textLength": len(text),
        "lastUpdated": _now_iso(),
        "filename": filename
    })

    # persist content
    stores.upsert_email_content(doc)

    # update status summary (optional but useful)
    try:
        status_doc = stores.get_email_status(email_id, pk=pk or email_id)
    except Exception:
        status_doc = {"id": email_id, "pk": pk or email_id}
    status_doc["ocrSummary"] = _compute_ocr_summary(doc.get("attachments") or [])
    stores.upsert_email_status(status_doc)

    return {
        "emailId": email_id,
        "filename": filename,
        "ocr": {
            "status": "success",
            "engine": "aihub-aoai",
            "textLength": len(text),
            "lastUpdated": att["ocr"]["lastUpdated"]
        }
    }

def ocr_all_attachments(email_id: str, pk: str | None = None) -> dict:
    """Run OCR for all attachments on an email."""
    stores = CosmosEmailStores()
    blob = BlobService()
    ocr = OCRClient()

    doc = stores.get_email_content(email_id, pk=pk or email_id)
    atts = doc.get("attachments") or []

    processed = 0
    succeeded = 0
    failed = 0
    errors = []

    for a in atts:
        filename = a.get("filename") or (a.get("blobPath") or a.get("blobUrl") or "").split("/")[-1]
        if not filename:
            continue
        processed += 1
        try:
            ref = a.get("blobPath") or a.get("blobUrl") or filename
            image_bytes = blob.download_bytes(ref)
            text = ocr.extract_text_from_image_bytes(image_bytes).strip()
            a.setdefault("ocr", {})
            a["ocr"].update({
                "status": "success",
                "text": text,
                "engine": "aihub-aoai",
                "textLength": len(text),
                "lastUpdated": _now_iso(),
                "filename": filename
            })
            succeeded += 1
        except Exception as e:
            failed += 1
            errors.append({"filename": filename, "error": str(e)})

    stores.upsert_email_content(doc)
    try:
        status_doc = stores.get_email_status(email_id, pk=pk or email_id)
    except Exception:
        status_doc = {"id": email_id, "pk": pk or email_id}
    status_doc["ocrSummary"] = _compute_ocr_summary(doc.get("attachments") or [])
    stores.upsert_email_status(status_doc)

    return {
        "emailId": email_id,
        "processed": processed,
        "succeeded": succeeded,
        "failed": failed,
        "errors": errors[:3]
    }
