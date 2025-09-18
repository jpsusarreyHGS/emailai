import json
import logging
import azure.functions as func

from utils.db import query_container, upsert_item
from utils.blob import download_blob_bytes
from utils.ai_ocr import OCRClient


def ocr_attachments(req: func.HttpRequest) -> func.HttpResponse:
    """
    Perform OCR on all attachments for a given email.
    """
    try:
        email_id = req.route_params.get("email_id")
        if not email_id:
            return func.HttpResponse("Missing email_id", status_code=400)

        logging.info(f"Starting OCR for email {email_id}")

        # Step 1: Get email content doc
        query = "SELECT * FROM c WHERE c.id = @id"
        params = [{"name": "@id", "value": email_id}]
        items = query_container("emails-content", query, params)

        if not items:
            return func.HttpResponse(
                json.dumps({"error": f"Email {email_id} not found"}),
                status_code=404,
                mimetype="application/json"
            )

        email_doc = items[0]
        attachments = email_doc.get("attachments", [])
        if not attachments:
            return func.HttpResponse(
                json.dumps({"message": f"No attachments for {email_id}"}),
                status_code=200,
                mimetype="application/json"
            )

        client = OCRClient()
        results = []

        # Step 2: Process each attachment
        for att in attachments:
            ref = att.get("blobPath") or att.get("filename")
            try:
                blob_bytes = download_blob_bytes(ref)
                text = client.extract_text_from_image_bytes(blob_bytes)

                att.setdefault("ocr", {})
                att["ocr"].update({
                    "status": "success",
                    "text": text,
                    "engine": "aihub-aoai"
                })
                results.append({"filename": att.get("filename"), "status": "success"})
            except Exception as e:
                logging.error(f"OCR failed for {att.get('filename')}: {str(e)}")
                att.setdefault("ocr", {})
                att["ocr"].update({
                    "status": "failed",
                    "error": str(e)
                })
                results.append({"filename": att.get("filename"), "status": "failed"})

        # Step 3: Save updates
        upsert_item("emails-content", email_doc)

        return func.HttpResponse(
            json.dumps({
                "email_id": email_id,
                "attachments_processed": len(attachments),
                "results": results
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"OCR error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "OCR failed", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
