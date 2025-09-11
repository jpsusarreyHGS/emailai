import base64
import json
import logging
import mimetypes
import os
import random

import azure.functions as func
from utils.graph import (create_message_in_inbox, ensure_token_or_auth_url,
                         get_default_scopes, list_inbox_messages)


def read_inbox(req: func.HttpRequest) -> func.HttpResponse:
  """
  Read messages from the shared mailbox Inbox via Microsoft Graph.

  - If no cached token exists, returns 401 with an authorization URL in the response
  - If token exists, fetches messages and returns JSON list
  """
  try:
    access_token, auth_url = ensure_token_or_auth_url(scopes=get_default_scopes())
    if auth_url and not access_token:
      return func.HttpResponse(
          json.dumps({"error": "unauthenticated", "authUrl": auth_url}),
          status_code=401,
          mimetype="application/json"
      )

    # Optional query parameter unread=true to only fetch unread messages
    unread_param = req.params.get('unread')
    unread = None
    if isinstance(unread_param, str):
      if unread_param.lower() in ('true', '1', 'yes'):
        unread = True
      elif unread_param.lower() in ('false', '0', 'no'):
        unread = False

    messages = list_inbox_messages(access_token=access_token, unread=unread)
    items = messages.get('value', [])
    return func.HttpResponse(
        json.dumps({"emails": items}),
        status_code=200,
        mimetype="application/json"
    )

  except Exception as e:
    logging.exception("Failed to read inbox")
    return func.HttpResponse(
        json.dumps({"error": "failed_to_read_inbox", "details": str(e)}),
        status_code=500,
        mimetype="application/json"
    )


def _is_local_host() -> bool:
  """Determine if we are running locally (not on Azure)."""
  # In Azure, WEBSITE_SITE_NAME is set. Locally it is not.
  return os.getenv('WEBSITE_SITE_NAME') is None


def seed_inbox_from_file(req: func.HttpRequest) -> func.HttpResponse:
  """
  POST-only endpoint to create messages in the Inbox from a local JSON file.

  Only allowed when running locally. The file path is read from env var
  SEED_EMAILS_JSON_PATH. The JSON must be an array of message objects compatible
  with Microsoft Graph create message API.
  """
  try:
    if req.method != 'POST':
      return func.HttpResponse(
          json.dumps({"error": "method_not_allowed"}),
          status_code=405,
          mimetype="application/json"
      )

    # Restrict to local environment
    if not _is_local_host():
      return func.HttpResponse(
          json.dumps({"error": "forbidden", "message": "Seeding is allowed only in local environment"}),
          status_code=403,
          mimetype="application/json"
      )

    access_token, auth_url = ensure_token_or_auth_url(scopes=get_default_scopes())
    if auth_url and not access_token:
      return func.HttpResponse(
          json.dumps({"error": "unauthenticated", "authUrl": auth_url}),
          status_code=401,
          mimetype="application/json"
      )

    # Determine JSON file path from env
    json_path = os.getenv('SEED_EMAILS_JSON_PATH')
    if not json_path:
      return func.HttpResponse(
          json.dumps({"error": "missing_env", "message": "SEED_EMAILS_JSON_PATH is not set"}),
          status_code=400,
          mimetype="application/json"
      )

    # Load and validate JSON
    try:
      with open(json_path, 'r', encoding='utf-8') as f:
        emails = json.load(f)
      if not isinstance(emails, list):
        raise ValueError('JSON must be an array of message objects')
    except Exception as ex:
      return func.HttpResponse(
          json.dumps({"error": "invalid_json", "details": str(ex), "path": json_path}),
          status_code=400,
          mimetype="application/json"
      )

    random.shuffle(emails)

    created = []
    failures = []

    # Resolve images directory relative to the JSON file path: ../images from the emails directory
    # Example: if json_path is resources/emails/receiptemails.json, images_dir becomes resources/images
    emails_dir = os.path.dirname(json_path)
    resources_dir = os.path.dirname(emails_dir)
    images_dir = os.path.join(resources_dir, 'images')

    for idx, msg in enumerate(emails):
      # Ensure minimal required fields for Graph message create API
      if not isinstance(msg, dict):
        failures.append({"index": idx, "error": "item_not_object"})
        continue

      # Default content type and body if missing
      body = msg.get('body') or {"contentType": "text", "content": ""}
      if not isinstance(body, dict):
        body = {"contentType": "text", "content": str(body)}

      message_payload = {
        "subject": msg.get('subject', ''),
        "body": {
          "contentType": body.get('contentType', 'text'),
          "content": body.get('content', '')
        },
        "from": msg.get('from', []),
        "toRecipients": msg.get('toRecipients', [])
      }

      # Add file attachments if requested
      try:
        if msg.get('hasAttachments'):
          raw_attachments = msg.get('attachments') or []
          # Normalize to list of filenames
          filenames = []
          if isinstance(raw_attachments, list):
            for item in raw_attachments:
              if isinstance(item, str):
                filenames.append(item)
              elif isinstance(item, dict):
                name = item.get('filename') or item.get('name')
                if name:
                  filenames.append(name)
          attachments_payload = []
          for filename in filenames:
            file_path = os.path.join(images_dir, filename)
            if not os.path.exists(file_path):
              raise FileNotFoundError(f"Attachment file not found: {file_path}")
            with open(file_path, 'rb') as af:
              encoded = base64.b64encode(af.read()).decode('utf-8')
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
              content_type = 'application/octet-stream'
            attachments_payload.append({
              "@odata.type": "#microsoft.graph.fileAttachment",
              "name": filename,
              "contentType": content_type,
              "contentBytes": encoded
            })
          if attachments_payload:
            message_payload["attachments"] = attachments_payload
      except Exception as ex:
        failures.append({"index": idx, "error": f"attachment_error: {str(ex)}"})
        continue

      # Mark as unread via extended property if requested or default
      # For this seeding, always create as unread to simulate new items
      message_payload["singleValueExtendedProperties"] = [
        {
          "id": "Integer 0x0E07",
          "value": "4"
        }
      ]

      # Attempt to create message
      try:
        result = create_message_in_inbox(access_token=access_token, message=message_payload)
        created.append({"id": result.get('id'), "subject": result.get('subject')})
      except Exception as ex:
        failures.append({"index": idx, "error": str(ex)})

    status = 200 if not failures else 207  # Multi-status if partial failures
    return func.HttpResponse(
        json.dumps({"created": created, "failed": failures, "total": len(emails)}),
        status_code=status,
        mimetype="application/json"
    )

  except Exception as e:
    logging.exception("Failed to seed inbox from file")
    return func.HttpResponse(
        json.dumps({"error": "failed_to_seed_inbox", "details": str(e)}),
        status_code=500,
        mimetype="application/json"
    )
