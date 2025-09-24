#backend\functions\ocr.py
import json
import logging
import azure.functions as func

from utils.db import query_container, upsert_item
from utils.blob import download_blob_bytes
from utils.ai_ocr import OCRClient
from functions.prompts.ocr import EXTRACT_RECEIPT_PROMPT
from difflib import SequenceMatcher


def calculate_text_similarity(text1, text2):
    """Calculate similarity between two texts (0-100)"""
    if not text1 or not text2:
        return 0
    return int(SequenceMatcher(None, text1.lower(), text2.lower()).ratio() * 100)


def ocr_attachments(req: func.HttpRequest) -> func.HttpResponse:
    """
    Perform OCR on all attachments for a given email.
    - Uses EXTRACT_RECEIPT_PROMPT to enforce JSON output
    - Cleans and upserts structured OCR results into Cosmos
    """
    try:
        email_id = req.route_params.get("email_id")
        if not email_id:
            return func.HttpResponse("Missing email_id", status_code=400)

        logging.info(f"Starting OCR for email {email_id}")

        # Step 1: Fetch email doc
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
        multiple_attachments = len(attachments) > 1
        results = []
        all_extracted_texts = []  # Store all OCR texts for similarity comparison

        # Step 2: Process each attachment
        for att in attachments:
            # Normalize reference and filename fields
            ref = att.get("blobPath") or att.get("name") or att.get("filename")
            try:
                blob_bytes = download_blob_bytes(ref)

                # OCR call with explicit JSON schema prompt
                structured_json = client.extract_text_from_image_bytes(
                    blob_bytes, prompt_override=EXTRACT_RECEIPT_PROMPT
                )

                logging.info(f"Raw OCR response for {att.get('name')}: {structured_json}")

                # Clean up `content='...'` wrapper if present
                if isinstance(structured_json, str) and structured_json.startswith("content="):
                    structured_json = structured_json.replace("content=", "").strip("'\"")
                
                logging.info(f"Cleaned OCR response: {structured_json}")

                # Parse JSON and enforce strict schema + duplication_score rule
                try:
                    parsed = json.loads(structured_json)

                    # Build strict payload with only required fields
                    merchant = parsed.get("merchant")
                    # Clean up merchant name if it has extra text
                    if merchant and isinstance(merchant, str):
                        # Remove newlines and extra text, take first 2 words
                        merchant = merchant.replace('\n', ' ').strip()
                        words = merchant.split()
                        if len(words) > 2:
                            merchant = ' '.join(words[:2])
                    
                    payload = {
                        "merchant": merchant,
                        "date": parsed.get("date"),
                        "total": parsed.get("total"),
                        "model": parsed.get("model"),
                        "store_number": parsed.get("store_number"),
                        "confidence_score": int(parsed.get("confidence_score", 0) or 0),
                        "duplication_score": int(parsed.get("duplication_score", 0) or 0),
                    }

                    if not multiple_attachments:
                        payload["duplication_score"] = 0

                    structured_json = json.dumps(payload)
                except Exception:
                    logging.warning("OCR returned non-JSON, attempting repair")
                    # Try to extract a JSON object from the string
                    try:
                        text = structured_json
                        start = text.find("{")
                        end = text.rfind("}")
                        if start != -1 and end != -1 and end > start:
                            candidate = text[start:end+1]
                            parsed = json.loads(candidate)
                            payload = {
                                "merchant": parsed.get("merchant"),
                                "date": parsed.get("date"),
                                "total": parsed.get("total"),
                                "model": parsed.get("model"),
                                "store_number": parsed.get("store_number"),
                                "confidence_score": int(parsed.get("confidence_score", 0) or 0),
                                "duplication_score": int(parsed.get("duplication_score", 0) or 0),
                            }
                            if not multiple_attachments:
                                payload["duplication_score"] = 0
                            structured_json = json.dumps(payload)
                        else:
                            raise ValueError("no json braces found")
                    except Exception:
                        logging.warning("No JSON found, attempting intelligent text parsing")
                        # Parse the raw receipt text intelligently
                        text = structured_json.lower()
                        
                        # Extract merchant (usually first line, just the business name)
                        merchant = None
                        lines = structured_json.split('\n')
                        if lines:
                            first_line = lines[0].strip()
                            if first_line:
                                # Take first line but clean it up
                                merchant = first_line
                                # Remove phone numbers
                                import re
                                merchant = re.sub(r'\(\d{3}\)\s*\d{3}-\d{4}', '', merchant)
                                # Remove addresses (numbers followed by street names) but keep business name
                                merchant = re.sub(r'\d+\s+[a-zA-Z\s]+(?:st|street|rd|road|ave|avenue|blvd|boulevard)', '', merchant)
                                # Remove suite numbers
                                merchant = re.sub(r'suite\s+[a-z0-9]+', '', merchant, flags=re.IGNORECASE)
                                # Clean up extra spaces
                                merchant = merchant.strip()
                                # Take first 2-3 words (business name)
                                words = merchant.split()
                                if len(words) > 2:
                                    merchant = ' '.join(words[:2])  # Take first 2 words for business name
                                merchant = merchant.strip()
                        
                        # Extract date (look for date patterns)
                        date = None
                        import re
                        date_patterns = [
                            r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YYYY or MM/DD/YY
                            r'\d{1,2}-\d{1,2}-\d{2,4}',  # MM-DD-YYYY
                            r'\d{4}-\d{1,2}-\d{1,2}',    # YYYY-MM-DD
                        ]
                        for pattern in date_patterns:
                            match = re.search(pattern, structured_json)
                            if match:
                                date = match.group()
                                break
                        
                        # Extract total (look for "Total" or "Balance Due" - get the final total)
                        total = None
                        # Look for the last occurrence of "Total" followed by a number
                        total_matches = re.findall(r'total[:\s]*\$?(\d+\.?\d*)', text)
                        if total_matches:
                            # Take the last total (usually the final amount)
                            total = total_matches[-1]
                        else:
                            # Fallback to balance due
                            balance_matches = re.findall(r'balance due[:\s]*\$?(\d+\.?\d*)', text)
                            if balance_matches:
                                total = balance_matches[-1]
                        
                        # Extract store number/address
                        store_number = None
                        # Look for address patterns or store numbers
                        address_patterns = [
                            r'\d+\s+[a-zA-Z\s]+(?:st|street|rd|road|ave|avenue|blvd|boulevard)',
                            r'suite\s+[a-z0-9]+',
                            r'store\s*#?\s*(\d+)',
                        ]
                        for pattern in address_patterns:
                            match = re.search(pattern, text)
                            if match:
                                store_number = match.group()
                                break
                        
                        # Calculate confidence based on how much we extracted
                        extracted_count = sum(1 for x in [merchant, date, total, store_number] if x is not None)
                        confidence_score = min(90, 20 + (extracted_count * 15))  # 20-80 based on extraction success
                        
                        payload = {
                            "merchant": merchant,
                            "date": date,
                            "total": total,
                            "model": None,  # Hard to extract from receipts
                            "store_number": store_number,
                            "confidence_score": confidence_score,
                            "duplication_score": 0 if not multiple_attachments else 50,
                        }
                        structured_json = json.dumps(payload)
                        logging.info(f"Intelligent parsing result: {payload}")

                # Save into attachment
                att.setdefault("ocr", {})
                att["ocr"].update({
                    "status": "success",
                    "text": structured_json,
                    "engine": "aihub-aoai"
                })

                # Store extracted text for similarity comparison
                try:
                    parsed_text = json.loads(structured_json)
                    extracted_text = f"{parsed_text.get('merchant', '')} {parsed_text.get('date', '')} {parsed_text.get('total', '')} {parsed_text.get('store_number', '')}"
                    all_extracted_texts.append(extracted_text.strip())
                except:
                    all_extracted_texts.append("")

                results.append({"filename": att.get("name") or att.get("filename"), "status": "success"})

            except Exception as e:
                logging.error(f"OCR failed for {att.get('filename')}: {str(e)}")
                att.setdefault("ocr", {})
                att["ocr"].update({
                    "status": "failed",
                    "error": str(e)
                })
                results.append({"filename": att.get("name") or att.get("filename"), "status": "failed"})

        # Step 3: Calculate overall scores
        overall_confidence = 0
        overall_duplication = 0
        
        if results:
            # Calculate average confidence
            confidence_scores = []
            for att in attachments:
                if att.get("ocr", {}).get("status") == "success":
                    try:
                        ocr_data = json.loads(att["ocr"]["text"])
                        confidence_scores.append(ocr_data.get("confidence_score", 0))
                    except:
                        pass
            overall_confidence = sum(confidence_scores) // len(confidence_scores) if confidence_scores else 0
            
            # Calculate duplication based on text similarity
            if len(all_extracted_texts) > 1:
                max_similarity = 0
                for i in range(len(all_extracted_texts)):
                    for j in range(i + 1, len(all_extracted_texts)):
                        similarity = calculate_text_similarity(all_extracted_texts[i], all_extracted_texts[j])
                        max_similarity = max(max_similarity, similarity)
                overall_duplication = max_similarity
            else:
                overall_duplication = 0
        
        # Update email doc with overall scores
        email_doc["overall_confidence"] = overall_confidence
        email_doc["overall_duplication"] = overall_duplication
        
        # Step 4: Save updated doc
        upsert_item("emails-content", email_doc)

        return func.HttpResponse(
            json.dumps({
                "email_id": email_id,
                "attachments_processed": len(attachments),
                "results": results
            }),
            status_code=200,
            mimetype="application/json",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        )

    except Exception as e:
        logging.error(f"OCR error: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "OCR failed", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        )
