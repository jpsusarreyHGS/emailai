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
  2. If status provided: Query emails-content container for items with that status
  3. If no status provided: Get all emails from emails-content
  4. Return the email content as JSON

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
            headers={
              "Access-Control-Allow-Origin": "*",
              "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
              "Access-Control-Allow-Headers": "Content-Type"
                }
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
          headers={
              "Access-Control-Allow-Origin": "*",
              "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
              "Access-Control-Allow-Headers": "Content-Type"
          }
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
          headers={
              "Access-Control-Allow-Origin": "*",
              "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
              "Access-Control-Allow-Headers": "Content-Type"
          }
      )

  except Exception as e:
    logging.error(f"Error retrieving emails: {str(e)}")
    return func.HttpResponse(
        json.dumps({"error": "Failed to retrieve emails"}),
        status_code=500,
        mimetype="application/json",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
          }
    )


def get_emails_by_assigned_agent(req: func.HttpRequest) -> func.HttpResponse:
  """
  Get emails from emails-content based on their assigned_agent.

  This function will:
  1. Get assigned_agent parameter from request (query param or body)
  2. If assigned_agent provided: Query emails-content container for items with that assigned_agent
  3. If no assigned_agent provided: Get all emails from emails-content
  4. Return the email content as JSON

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
          headers={
              "Access-Control-Allow-Origin": "*",
              "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
              "Access-Control-Allow-Headers": "Content-Type"
          }
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
          headers={
              "Access-Control-Allow-Origin": "*",
              "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
              "Access-Control-Allow-Headers": "Content-Type"
          }
      )

  except Exception as e:
    logging.error(f"Error retrieving emails by assigned_agent: {str(e)}")
    return func.HttpResponse(
        json.dumps({"error": "Failed to retrieve emails by assigned_agent"}),
        status_code=500,
        mimetype="application/json",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
          }
    )


def get_emails_by_id(req: func.HttpRequest) -> func.HttpResponse:
  """
  Get a specific email from emails-content based on its id.

  This function will:
  1. Get id parameter from request (query param or body)
  2. Query emails-content container for the item with that id
  3. Return the email content as JSON

  Parameters:
  - id (required): The unique identifier of the email to retrieve.
  """
  try:
    # Get id parameter from query string or request body
    email_id = req.params.get('id')
    if not email_id:
      try:
        req_body = req.get_json()
        if req_body:
          email_id = req_body.get('id')
      except ValueError:
        pass

    if not email_id:
      return func.HttpResponse(
          json.dumps({"error": "id parameter is required"}),
          status_code=400,
          mimetype="application/json",
          headers={
              "Access-Control-Allow-Origin": "*",
              "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
              "Access-Control-Allow-Headers": "Content-Type"
          }
      )

    logging.info(f'Getting email with id: {email_id}')

    # Query emails-content directly for the record with the specified id
    content_query = "SELECT * FROM c WHERE c.id = @id"
    parameters = [{"name": "@id", "value": email_id}]
    email_contents = query_container('emails-content', content_query, parameters)

    if not email_contents:
      logging.info(f'No email found with id: {email_id}')
      return func.HttpResponse(
          json.dumps({"error": f"No email found with id: {email_id}"}),
          status_code=404,
          mimetype="application/json",
          headers={
              "Access-Control-Allow-Origin": "*",
              "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
              "Access-Control-Allow-Headers": "Content-Type"
          }
      )

    # Since id should be unique, return the first (and should be only) result
    email = email_contents[0]
    logging.info(f'Successfully retrieved email with id: {email_id}')

    # Return the single email
    return func.HttpResponse(
        json.dumps({"email": email}),
        status_code=200,
        mimetype="application/json",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )

  except Exception as e:
    logging.error(f"Error retrieving email by id: {str(e)}")
    return func.HttpResponse(
        json.dumps({"error": "Failed to retrieve email by id"}),
        status_code=500,
        mimetype="application/json",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
          }
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
          mimetype="application/json",
          headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
              }
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
        headers={
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type"
            }
    )

  except Exception as e:
    logging.exception("Failed to ingest emails from inbox")
    return func.HttpResponse(
        json.dumps({"error": "failed_to_ingest_emails", "details": str(e)}),
        status_code=500,
        mimetype="application/json",
        headers={
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type"
            }
    )
