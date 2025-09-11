import datetime
import json
import logging

import azure.functions as func
from functions import ocr as ocr_funcs
from functions import categorize as categorize_funcs
from functions import emails as email_funcs

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


@app.function_name("email_attachment_ocr")
@app.route(route="emails/{email_id}/attachments/{filename}/ocr", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def email_attachment_ocr(req: func.HttpRequest) -> func.HttpResponse:
    email_id = req.route_params.get("email_id")
    filename = req.route_params.get("filename")
    if not email_id or not filename:
        return func.HttpResponse("Missing email_id or filename", status_code=400)
    pk = req.params.get("pk") or email_id
    try:
        result = ocr_funcs.ocr_attachment(email_id=email_id, filename=filename, pk=pk)
        return func.HttpResponse(json.dumps(result), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(str(e), status_code=500)

@app.function_name("email_ocr_all")
@app.route(route="emails/{email_id}/ocr", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def email_ocr_all(req: func.HttpRequest) -> func.HttpResponse:
    email_id = req.route_params.get("email_id")
    if not email_id:
        return func.HttpResponse("Missing email_id", status_code=400)
    pk = req.params.get("pk") or email_id
    try:
        result = ocr_funcs.ocr_all_attachments(email_id=email_id, pk=pk)
        return func.HttpResponse(json.dumps(result), mimetype="application/json")
    except Exception as e:
        return func.HttpResponse(str(e), status_code=500)
    
@app.function_name("health")
@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("ok")    
    