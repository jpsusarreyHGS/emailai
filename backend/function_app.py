import datetime
import json
import logging

import azure.functions as func
from functions.ocr import ocr_attachments       
from functions.categorize import categorize_emails
from functions.emails import get_emails_by_status

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
    """Endpoint to get emails, optionally filtered by status."""
    return get_emails_by_status(req)


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
