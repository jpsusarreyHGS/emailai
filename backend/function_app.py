# backend\function_app.py
import datetime
import json
import logging

import azure.functions as func
from functions.categorize import categorize_emails
from functions.draft import generate_draft
from functions.emails import (fetch_email_by_id, get_emails_by_assigned_agent,
                              get_emails_by_status, ingest_emails,
                              save_email_edits, update_email_ticket)
from functions.graph import graph_connect
from functions.inbox import read_inbox, seed_inbox_from_file
from functions.ocr import ocr_attachments
from utils.blob_storage import BlobService

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
  """Endpoint to get emails, optionally filtered by id, assigned_agent, or status."""

  # Check for assigned_agent parameter (from query string or body)
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


@app.route(route="emails/{email_id}/draft", methods=["POST"])
def EmailsDraft(req: func.HttpRequest) -> func.HttpResponse:
  return generate_draft(req)


@app.route(route="emails/{email_id}/fetch", auth_level=func.AuthLevel.ANONYMOUS)
def EmailsFetchById(req: func.HttpRequest) -> func.HttpResponse:
  return fetch_email_by_id(req)


@app.route(route="emails/save-edits", methods=["POST", "OPTIONS"])
def EmailsSaveEdits(req: func.HttpRequest) -> func.HttpResponse:
  # Handle CORS preflight
  if req.method == "OPTIONS":
    return func.HttpResponse(
        "",
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )
  return save_email_edits(req)


@app.route(route="emails/{email_id}/ticket", auth_level=func.AuthLevel.FUNCTION, methods=["POST", "OPTIONS"])
def EmailsUpdateTicket(req: func.HttpRequest) -> func.HttpResponse:
  """Endpoint to update the ticket status of a specific email."""
  # Handle CORS preflight
  if req.method == "OPTIONS":
    return func.HttpResponse(
        "",
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )
  return update_email_ticket(req)


@app.function_name("health")
@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
  return func.HttpResponse("ok")


@app.route(route="attachments/{container}/{*blob_path}", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def AttachmentProxy(req: func.HttpRequest) -> func.HttpResponse:
  try:
    container = req.route_params.get("container")
    blob_path = req.route_params.get("blob_path")
    if not container or not blob_path:
      return func.HttpResponse("Missing path", status_code=400)

    svc = BlobService()
    data = svc.download_bytes(f"{container}/{blob_path}")
    return func.HttpResponse(
      body=data,
      status_code=200,
      mimetype="application/octet-stream",
      headers={
        "Access-Control-Allow-Origin": "*",
        "Cache-Control": "no-cache"
      }
    )
  except Exception as e:
    return func.HttpResponse(str(e), status_code=500)
