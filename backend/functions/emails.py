import base64
import json
import logging

import azure.functions as func
from utils.blob_storage import BlobService
from utils.db import bulk_upsert_items, process_html_content, query_container
from utils.graph import (ensure_token_or_auth_url, get_default_scopes,
                         get_message_attachment_content, list_inbox_messages,
                         list_message_attachments)


def get_emails_by_status(req: func.HttpRequest) -> func.HttpResponse:
  """
  Get emails from emails-content based on their status.

  This function will:
  1. Get status parameter from request (query param or body)
  2. If status provided: Query emails-status container for items with that status
  3. If no status provided: Get all emails from emails-content
  4. Extract email IDs and query emails-content for matching emails
  5. Return the email content as JSON

  Parameters:
  - status (optional): Filter emails by this status. Currently supports 'new'. 
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

      # Validate status parameter (currently only 'new' is supported)
      valid_statuses = ['new']
      if status not in valid_statuses:
        return func.HttpResponse(
            json.dumps({"error": f"Invalid status. Supported statuses: {', '.join(valid_statuses)}"}),
            status_code=400,
            mimetype="application/json"
        )

      # Step 1: Query emails-status for records with the specified status
      status_query = "SELECT c.id FROM c WHERE c.status = @status"
      parameters = [{"name": "@status", "value": status}]
      status_records = query_container('emails-status', status_query, parameters)

      logging.info(f'Found {len(status_records)} emails with status: {status}')

      # If no emails with the specified status, return empty array
      if not status_records:
        return func.HttpResponse(
            json.dumps({"emails": [], "status_filter": status}),
            status_code=200,
            mimetype="application/json"
        )

      # Step 2: Extract email IDs from status records
      email_ids = [record['id'] for record in status_records]

      # Step 3: Query emails-content for emails with matching IDs
      id_placeholders = ', '.join([f'@id{i}' for i in range(len(email_ids))])
      content_query = f"SELECT c.id, c.subject, c.receivedDateTime, c.sender, c.toRecipients, c.body FROM c WHERE c.id IN ({id_placeholders})"

      # Create parameters for the query
      content_parameters = [{"name": f"@id{i}", "value": email_id}
                            for i, email_id in enumerate(email_ids)]

      # Execute the query
      email_contents = query_container('emails-content', content_query, content_parameters)

      logging.info(f'Retrieved {len(email_contents)} email contents')

      # Return filtered results
      return func.HttpResponse(
          json.dumps({"emails": email_contents, "status_filter": status}),
          status_code=200,
          mimetype="application/json"
      )

    else:
      logging.info('Getting all emails (no status filter)')

      # No status filter - get all emails from emails-content
      content_query = "SELECT c.id, c.subject, c.receivedDateTime, c.sender, c.toRecipients, c.body FROM c"
      email_contents = query_container('emails-content', content_query)

      logging.info(f'Retrieved {len(email_contents)} total emails')

      # Return all emails
      return func.HttpResponse(
          json.dumps({"emails": email_contents, "status_filter": None}),
          status_code=200,
          mimetype="application/json"
      )

  except Exception as e:
    logging.error(f"Error retrieving emails: {str(e)}")
    return func.HttpResponse(
        json.dumps({"error": "Failed to retrieve emails"}),
        status_code=500,
        mimetype="application/json"
    )


def ingest_emails(req: func.HttpRequest) -> func.HttpResponse:
  """
  Ingest unread emails from Outlook inbox via Microsoft Graph.

  This function will:
  1. Authenticate with Microsoft Graph using cached token
  2. Fetch all unread emails from the shared mailbox inbox
  3. Return the emails as a list for further processing

  Returns:
  - 200: JSON with list of unread emails
  - 401: Authentication required (returns auth URL)
  - 500: Server error
  """
  try:
    # Handle authentication
    access_token, auth_url = ensure_token_or_auth_url(scopes=get_default_scopes())
    if auth_url and not access_token:
      return func.HttpResponse(
          json.dumps({"error": "unauthenticated", "authUrl": auth_url}),
          status_code=401,
          mimetype="application/json"
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
        mimetype="application/json"
    )

  except Exception as e:
    logging.exception("Failed to ingest emails from inbox")
    return func.HttpResponse(
        json.dumps({"error": "failed_to_ingest_emails", "details": str(e)}),
        status_code=500,
        mimetype="application/json"
    )
