#backend\functions\draft.py
import json
import logging
import azure.functions as func
from aihub import LLMInterface
from functions.prompts.draft import DRAFT_EMAIL_RESPONSE_PROMPT
from utils.db import query_container, upsert_item


def generate_draft(req: func.HttpRequest) -> func.HttpResponse:
    try:
        email_id = req.route_params.get("email_id")
        if not email_id:
            return func.HttpResponse(
                "Missing email_id",
                status_code=400,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type"
                }
            )

        # Step 1: Get email content doc
        query = "SELECT * FROM c WHERE c.id = @id"
        params = [{"name": "@id", "value": email_id}]
        items = query_container("emails-content", query, params)

        if not items:
            return func.HttpResponse(
                json.dumps({"error": f"Email {email_id} not found"}),
                status_code=404,
                mimetype="application/json",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type"
                }
            )

        email_doc = items[0]
        body = email_doc.get("body", {}).get("content", "")

        # Step 2: Create LLM instance
        llm = LLMInterface.create(
            provider_name="azure-openai",
            system_prompt=DRAFT_EMAIL_RESPONSE_PROMPT
        )

        # Step 3: Generate draft from LLM
        response = llm.generate(prompt=f"Customer email:\n\n{body}")

        # Handle both string and object outputs
        if hasattr(response, "content"):
            draft_text = response.content
        else:
            draft_text = str(response)

        # Step 4: Save draft back into Cosmos DB
        email_doc["draft_reply"] = {"body": draft_text}
        upsert_item("emails-content", email_doc)

        return func.HttpResponse(
            json.dumps({"draft": draft_text}),
            status_code=200,
            mimetype="application/json",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        )
    except Exception as e:
        logging.error(f"Error generating draft: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        )