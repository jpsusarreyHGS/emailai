import datetime
import json
import logging

import azure.functions as func
from functions.categorize import categorize_emails
from functions.emails import (get_emails_by_assigned_agent,
                              get_emails_by_status, ingest_emails)
from functions.graph import graph_connect
from functions.inbox import read_inbox, seed_inbox_from_file
from functions.ocr import ocr_attachments

app = func.FunctionApp()


@app.route(route="MyHttpTrigger", auth_level=func.AuthLevel.FUNCTION)
def MyHttpTrigger(req: func.HttpRequest) -> func.HttpResponse:
  logging.info('Python HTTP trigger function processed a request.')

  name = req.params.get('name')
  if not name:
    try:
      req_body = req.get_json()
    except ValueError:
      pass
    else:
      name = req_body.get('name')

  if name:
    return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
  else:
    return func.HttpResponse(
        "This HTTP triggered function executed successfully. "
        "Pass a name in the query string or in the request body for a personalized response.",
        status_code=200
    )


@app.route(route="emails", auth_level=func.AuthLevel.FUNCTION, methods=["GET"])
def Emails(req: func.HttpRequest) -> func.HttpResponse:
  """Endpoint to get emails, optionally filtered by status or assigned_agent."""

  # Check for assigned_agent parameter first (from query string or body)
  assigned_agent = req.params.get('assigned_agent')
  if not assigned_agent:
    try:
      req_body = req.get_json()
      if req_body:
        assigned_agent = req_body.get('assigned_agent')
    except ValueError:
      pass

  # If assigned_agent parameter is provided, use the assigned_agent function
  if assigned_agent:
    return get_emails_by_assigned_agent(req)

  # Otherwise, use the status function (handles status parameter or returns all emails)
  return get_emails_by_status(req)


@app.route(route="emails/ingest", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def EmailsIngest(req: func.HttpRequest) -> func.HttpResponse:
  """Endpoint to ingest unread emails using from Outlook inbox."""
  return ingest_emails(req)


@app.route(route="emails/categorize", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def EmailsCategorize(req: func.HttpRequest) -> func.HttpResponse:
  """Endpoint to categorize emails using LLM and update their status."""
  return categorize_emails(req)


@app.function_name(name="ocr_attachments")
@app.route(route="emails/{email_id}/attachments/ocr", methods=["POST"])
def run_ocr(req: func.HttpRequest) -> func.HttpResponse:
  return ocr_attachments(req)


@app.function_name("health")
@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
  return func.HttpResponse("ok")
