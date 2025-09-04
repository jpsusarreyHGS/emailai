import json
import logging

import azure.functions as func
from utils.db import query_container


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
