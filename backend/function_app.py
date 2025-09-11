import datetime
import json
import logging

import azure.functions as func
from functions.categorize import categorize_emails
from functions.emails import get_emails_by_status
from functions.graph import graph_connect
from functions.inbox import read_inbox, seed_inbox_from_file

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
        "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
        status_code=200
    )


@app.route(route="emails", auth_level=func.AuthLevel.FUNCTION, methods=["GET"])
def Emails(req: func.HttpRequest) -> func.HttpResponse:
  """Endpoint to get emails, optionally filtered by status."""
  return get_emails_by_status(req)


@app.route(route="emails/categorize", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def EmailsCategorize(req: func.HttpRequest) -> func.HttpResponse:
  """Endpoint to categorize emails using LLM and update their status."""
  return categorize_emails(req)


@app.route(route="inbox", auth_level=func.AuthLevel.FUNCTION, methods=["GET"])
def Inbox(req: func.HttpRequest) -> func.HttpResponse:
  """Endpoint to list emails in the shared mailbox Inbox via Graph."""
  return read_inbox(req)


@app.route(route="inbox", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
def InboxSeed(req: func.HttpRequest) -> func.HttpResponse:
  """Endpoint to seed emails in the shared mailbox Inbox from a local JSON file (local only)."""
  return seed_inbox_from_file(req)


@app.route(route="graph-connect", auth_level=func.AuthLevel.FUNCTION, methods=["GET"])
def GraphConnect(req: func.HttpRequest) -> func.HttpResponse:
  """Endpoint to initiate/complete Graph delegated OAuth flow."""
  return graph_connect(req)
