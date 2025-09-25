# backend\functions\emails.py
import base64
import json
import logging

import azure.functions as func
from utils.blob_storage import BlobService
from utils.db import (bulk_upsert_items, process_html_content, query_container,
                      upsert_item)
from utils.graph import (ensure_token_or_auth_url, get_default_scopes,
                         get_message_attachment_content, list_inbox_messages,
                         list_message_attachments)


def get_cors_headers():
  """Return standard CORS headers for all responses."""
  return {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type"
  }


def get_emails_by_status(req: func.HttpRequest) -> func.HttpResponse:
  """
  Get emails from emails-content based on their status.

  Parameters:
  - status (optional): Filter emails by this status. Supports 'new', 'categorized'. 
                      If not provided, returns all emails.
  """
  try:
    # Get status parameter from query string or request body
    status = req.params.get('status')
    if not status:
      try:
        req_body = req.get_json()
        if req_body:
          status = req_body.get('status')
      except ValueError:
        pass

    if status:
      logging.info(f'Getting emails with status: {status}')

      # Validate status parameter
      valid_statuses = ['new', 'categorized']
      if status not in valid_statuses:
        return func.HttpResponse(
            json.dumps({"error": f"Invalid status. Supported statuses: {', '.join(valid_statuses)}"}),
            status_code=400,
            mimetype="application/json",
            headers=get_cors_headers()
        )

      # Query emails-content directly for records with the specified status
      content_query = "SELECT * FROM c WHERE c.status = @status"
      parameters = [{"name": "@status", "value": status}]
      email_contents = query_container('emails-content', content_query, parameters)

      logging.info(f'Found {len(email_contents)} emails with status: {status}')

      # Return filtered results
      return func.HttpResponse(
          json.dumps({"emails": email_contents, "status_filter": status}),
          status_code=200,
          mimetype="application/json",
          headers=get_cors_headers()
      )

    else:
      logging.info('Getting all emails (no status filter)')

      # No status filter - get all emails from emails-content
      content_query = "SELECT * FROM c"
      email_contents = query_container('emails-content', content_query)

      logging.info(f'Retrieved {len(email_contents)} total emails')

      # Return all emails
      return func.HttpResponse(
          json.dumps({"emails": email_contents, "status_filter": None}),
          status_code=200,
          mimetype="application/json",
          headers=get_cors_headers()
      )

  except Exception as e:
    logging.error(f"Error retrieving emails: {str(e)}")
    return func.HttpResponse(
        json.dumps({"error": "Failed to retrieve emails"}),
        status_code=500,
        mimetype="application/json",
        headers=get_cors_headers()
    )


def get_emails_by_assigned_agent(req: func.HttpRequest) -> func.HttpResponse:
  """
  Get emails from emails-content based on their assigned_agent.

  Parameters:
  - assigned_agent (optional): Filter emails by this assigned_agent. 
                              If not provided, returns all emails.
  """
  try:
    # Get assigned_agent parameter from query string or request body
    assigned_agent = req.params.get('assigned_agent')
    if not assigned_agent:
      try:
        req_body = req.get_json()
        if req_body:
          assigned_agent = req_body.get('assigned_agent')
      except ValueError:
        pass

    if assigned_agent:
      logging.info(f'Getting emails with assigned_agent: {assigned_agent}')

      # Query emails-content directly for records with the specified assigned_agent
      content_query = "SELECT * FROM c WHERE c.assigned_agent = @assigned_agent"
      parameters = [{"name": "@assigned_agent", "value": assigned_agent}]
      email_contents = query_container('emails-content', content_query, parameters)

      logging.info(f'Found {len(email_contents)} emails with assigned_agent: {assigned_agent}')

      # Return filtered results
      return func.HttpResponse(
          json.dumps({"emails": email_contents, "assigned_agent_filter": assigned_agent}),
          status_code=200,
          mimetype="application/json",
          headers=get_cors_headers()
      )

    else:
      logging.info('Getting all emails (no assigned_agent filter)')

      # No assigned_agent filter - get all emails from emails-content
      content_query = "SELECT * FROM c"
      email_contents = query_container('emails-content', content_query)

      logging.info(f'Retrieved {len(email_contents)} total emails')

      # Return all emails
      return func.HttpResponse(
          json.dumps({"emails": email_contents, "assigned_agent_filter": None}),
          status_code=200,
          mimetype="application/json",
          headers=get_cors_headers()
      )

  except Exception as e:
    logging.error(f"Error retrieving emails by assigned_agent: {str(e)}")
    return func.HttpResponse(
        json.dumps({"error": "Failed to retrieve emails by assigned_agent"}),
        status_code=500,
        mimetype="application/json",
        headers=get_cors_headers()
    )


def ingest_emails(req: func.HttpRequest) -> func.HttpResponse:
  """
  Ingest unread emails from Outlook inbox via Microsoft Graph.
  """
  try:
    # Handle authentication
    access_token, auth_url = ensure_token_or_auth_url(scopes=get_default_scopes())
    if auth_url and not access_token:
      return func.HttpResponse(
          json.dumps({"error": "unauthenticated", "authUrl": auth_url}),
          status_code=401,
          mimetype="application/json",
          headers=get_cors_headers()
      )

    logging.info('Fetching unread emails from Outlook inbox')

    # Fetch unread emails using Graph API
    messages_response = list_inbox_messages(access_token=access_token, unread=True)
    unread_emails = messages_response.get('value', [])

    logging.info(f'Successfully fetched {len(unread_emails)} unread emails')

    # Fetch attachments for emails that have them
    emails_with_attachments = 0
    for email in unread_emails:
      if email.get('hasAttachments', False):
        try:
          attachments_response = list_message_attachments(
            access_token=access_token, message_id=email['id'])
          email['attachments'] = attachments_response.get('value', [])
          emails_with_attachments += 1
          logging.info(
            f'Fetched {len(email["attachments"])} attachments for email: {email.get("subject", "No Subject")}')

          # Upload attachments to blob storage and create filtered attachment objects
          blob_service = BlobService()
          attachments_uploaded = 0
          filtered_attachments = []

          for attachment in email['attachments']:
            try:
              content_response = get_message_attachment_content(
                access_token=access_token,
                message_id=email['id'],
                attachment_id=attachment['id']
              )

              # Get the base64 content and decode it
              content_bytes_b64 = content_response.get('contentBytes')
              if content_bytes_b64:
                content_bytes = base64.b64decode(content_bytes_b64)

                # Create blob name: email_id/filename
                blob_name = f"{email['id']}/{attachment.get('name', 'unknown_attachment')}"

                # Upload to blob storage
                blob_ref = blob_service.upload_image(
                  image_data=content_bytes,
                  blob_name=blob_name,
                  content_type=attachment.get('contentType')
                )

                # Create filtered attachment object with only required fields
                filtered_attachment = {
                  'name': attachment.get('name'),
                  'contentType': attachment.get('contentType'),
                  'blobPath': blob_ref,
                  'ocr': {
                    'status': 'pending',
                    'text': None,
                    'model': None,
                    'lastUpdated': None
                  }
                }
                filtered_attachments.append(filtered_attachment)
                attachments_uploaded += 1
                logging.info(
                  f'Uploaded attachment to blob storage: {attachment.get("name", "Unknown")} -> {blob_ref}')
              else:
                logging.warning(f'No content bytes found for attachment {attachment["id"]}')
                # Create filtered attachment object with null blob path
                filtered_attachment = {
                  'name': attachment.get('name'),
                  'contentType': attachment.get('contentType'),
                  'blobPath': None,
                  'ocr': {
                    'status': 'pending',
                    'text': None,
                    'model': None,
                    'lastUpdated': None
                  }
                }
                filtered_attachments.append(filtered_attachment)

            except Exception as e:
              logging.warning(
                f'Failed to upload attachment {attachment["id"]} to blob storage: {str(e)}')
              # Create filtered attachment object with null blob path
              filtered_attachment = {
                'name': attachment.get('name'),
                'contentType': attachment.get('contentType'),
                'blobPath': None,
                'ocr': {
                  'status': 'pending',
                  'text': None,
                  'model': None,
                  'lastUpdated': None
                }
              }
              filtered_attachments.append(filtered_attachment)

          # Replace the full attachment objects with filtered ones
          email['attachments'] = filtered_attachments
          logging.info(
            f'Uploaded {attachments_uploaded}/{len(filtered_attachments)} attachments to blob storage')
        except Exception as e:
          logging.warning(f'Failed to fetch attachments for email {email["id"]}: {str(e)}')
          email['attachments'] = []
      else:
        email['attachments'] = []

      # Add status field to each email
      email['status'] = 'new'

    logging.info(f'Processed attachments for {emails_with_attachments} emails with attachments')

    # Process HTML content to plain text
    logging.info('Processing HTML content to plain text')
    processed_emails = process_html_content(unread_emails)

    # Upload emails to CosmosDB
    logging.info(f'Uploading {len(processed_emails)} emails to CosmosDB container: emails-content')
    try:
      upsert_results = bulk_upsert_items('emails-content', processed_emails)
      logging.info(f'Successfully upserted {len(upsert_results)} emails to CosmosDB')
    except Exception as e:
      logging.error(f'Failed to upsert emails to CosmosDB: {str(e)}')
      # Continue execution - we still want to return the emails even if DB upload fails

    return func.HttpResponse(
        json.dumps({
            "message": f"Successfully fetched {len(processed_emails)} unread emails",
            "emails": processed_emails,
            "count": len(processed_emails)
        }),
        status_code=200,
        mimetype="application/json",
        headers=get_cors_headers()
    )

  except Exception as e:
    logging.exception("Failed to ingest emails from inbox")
    return func.HttpResponse(
        json.dumps({"error": "failed_to_ingest_emails", "details": str(e)}),
        status_code=500,
        mimetype="application/json",
        headers=get_cors_headers()
    )


def save_email_edits(req: func.HttpRequest) -> func.HttpResponse:
  """
  Save user edits from the frontend into the email doc.
  - If OCR fields are provided, update the OCR JSON in the matching attachment(s)
  - If draft_body is provided, update email_doc.draft_reply.body
  Confidence/duplication scores remain unchanged.
  """
  try:
    body = req.get_json()
    email_id = body.get("id")
    if not email_id:
      return func.HttpResponse("Missing email id", status_code=400)

    # Fetch existing doc
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

    # 1) Update draft if provided
    draft_body = body.get("draft_body") or body.get("draft") or body.get("body")
    if draft_body is not None:
      if not isinstance(email_doc.get("draft_reply"), dict):
        email_doc["draft_reply"] = {"template": "response", "body": ""}
      email_doc["draft_reply"]["body"] = draft_body

    # 2) Update OCR fields if provided
    editable_fields = ["merchant", "date", "total", "model", "store_number"]
    has_ocr_field = any(field in body for field in editable_fields)
    if has_ocr_field and attachments:
      target_filename = body.get("filename") or body.get("name")
      updated = False
      for att in attachments:
        att_name = att.get("name") or att.get("filename")
        if target_filename and att_name != target_filename:
          continue
        ocr_data = {}
        if att.get("ocr") and att["ocr"].get("text"):
          try:
            ocr_data = json.loads(att["ocr"]["text"])
          except Exception:
            logging.warning("Failed to parse OCR JSON; resetting")
            ocr_data = {}
        for field in editable_fields:
          if field in body:
            ocr_data[field] = body[field]
        ocr_data["confidence_score"] = ocr_data.get("confidence_score", 0)
        ocr_data["duplication_score"] = ocr_data.get("duplication_score", 0)
        if "ocr" not in att:
          att["ocr"] = {}
        att["ocr"]["text"] = json.dumps(ocr_data)
        updated = True
      if not updated and target_filename:
        logging.info("No matching attachment found to update OCR fields")

    # Save updated email doc
    upsert_item("emails-content", email_doc)

    return func.HttpResponse(
        json.dumps(email_doc, indent=2),
        status_code=200,
        mimetype="application/json",
        headers=get_cors_headers()
    )

  except Exception as e:
    logging.error("Error saving email edits", exc_info=True)
    return func.HttpResponse(
        json.dumps({"error": str(e)}),
        status_code=500,
        mimetype="application/json",
        headers=get_cors_headers()
    )


def fetch_email_by_id(req: func.HttpRequest) -> func.HttpResponse:
  """
  Fetch a single email document by ID from emails-content.
  Uses route param: email_id
  """
  try:
    email_id = req.route_params.get("email_id")
    if not email_id:
      return func.HttpResponse(
          json.dumps({"error": "email_id route parameter is required"}),
          status_code=400,
          mimetype="application/json"
      )

    logging.info(f"Fetching email with id: {email_id}")

    # Query Cosmos DB
    query = "SELECT * FROM c WHERE c.id = @id"
    params = [{"name": "@id", "value": email_id}]
    items = query_container("emails-content", query, params)

    if not items:
      return func.HttpResponse(
          json.dumps({"error": f"No email found with id: {email_id}"}),
          status_code=404,
          mimetype="application/json"
      )

    # Return the single email document
    return func.HttpResponse(
        json.dumps(items[0]),
        status_code=200,
        mimetype="application/json",
        headers=get_cors_headers()
    )

  except Exception as e:
    logging.error(f"Error in fetch_email_by_id: {str(e)}")
    return func.HttpResponse(
        json.dumps({"error": "Failed to fetch email by id", "details": str(e)}),
        status_code=500,
        mimetype="application/json",
        headers=get_cors_headers()
    )


def update_email_ticket(req: func.HttpRequest) -> func.HttpResponse:
  """
  Update the ticket status of a specific email identified by its ID.
  """
  try:
    # Get email_id from route parameters
    email_id = req.route_params.get("email_id")
    if not email_id:
      return func.HttpResponse(
          json.dumps({"error": "email_id route parameter is required"}),
          status_code=400,
          mimetype="application/json",
          headers=get_cors_headers()
      )

    # Get ticket value from request body
    try:
      req_body = req.get_json()
      if not req_body:
        return func.HttpResponse(
            json.dumps({"error": "Request body is required"}),
            status_code=400,
            mimetype="application/json",
            headers=get_cors_headers()
        )
    except ValueError:
      return func.HttpResponse(
          json.dumps({"error": "Invalid JSON in request body"}),
          status_code=400,
          mimetype="application/json",
          headers=get_cors_headers()
      )

    ticket = req_body.get('ticket')
    if not ticket:
      return func.HttpResponse(
          json.dumps({"error": "ticket field is required in request body"}),
          status_code=400,
          mimetype="application/json",
          headers=get_cors_headers()
      )

    # Validate ticket value
    valid_ticket_values = ['new', 'open', 'closed']
    if ticket not in valid_ticket_values:
      return func.HttpResponse(
          json.dumps({
              "error": f"Invalid ticket value. Must be one of: {', '.join(valid_ticket_values)}",
              "provided": ticket
          }),
          status_code=400,
          mimetype="application/json",
          headers=get_cors_headers()
      )

    logging.info(f"Updating ticket status for email {email_id} to: {ticket}")

    # Find the email by ID
    query = "SELECT * FROM c WHERE c.id = @id"
    parameters = [{"name": "@id", "value": email_id}]
    email_items = query_container('emails-content', query, parameters)

    if not email_items:
      return func.HttpResponse(
          json.dumps({"error": f"No email found with id: {email_id}"}),
          status_code=404,
          mimetype="application/json",
          headers=get_cors_headers()
      )

    # Update the ticket field
    email_doc = email_items[0]
    old_ticket = email_doc.get('ticket', 'not set')
    email_doc['ticket'] = ticket

    # Save the updated email
    upsert_item('emails-content', email_doc)

    logging.info(
      f"Successfully updated email {email_id} ticket status from '{old_ticket}' to '{ticket}'")

    # Return success response with updated email
    return func.HttpResponse(
        json.dumps({
            "message": "Ticket status updated successfully",
            "email_id": email_id,
            "old_ticket": old_ticket,
            "new_ticket": ticket,
            "email": email_doc
        }),
        status_code=200,
        mimetype="application/json",
        headers=get_cors_headers()
    )

  except Exception as e:
    logging.error(f"Error updating email ticket status: {str(e)}")
    return func.HttpResponse(
        json.dumps({
            "error": "Failed to update email ticket status",
            "details": str(e)
        }),
        status_code=500,
        mimetype="application/json",
        headers=get_cors_headers()
    )
