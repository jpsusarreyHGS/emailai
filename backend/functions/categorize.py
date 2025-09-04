import json
import logging
from typing import Any, Dict, Literal

import azure.functions as func
from aihub import LLMInterface
from functions.prompts.categorize import CATEGORIZE_EMAILS_SYSTEM_PROMPT
from pydantic import BaseModel
from utils.db import query_container, upsert_item


def categorize_emails(req: func.HttpRequest) -> func.HttpResponse:
  """
  Categorize all emails with 'new' status using LLM and update their status and labels.

  This function will:
  1. Get all emails with status 'new'
  2. For each email, use LLM to determine industry and category labels
  3. Update the email status to 'categorized' in emails-status container
  4. Add a 'labels' field with industry and category to the status record
  5. Return the results of the categorization process
  """
  try:
    logging.info('Starting email categorization process for all new emails')

    # Step 1: Query emails-status for all records with status = 'new'
    status_query = "SELECT c.id FROM c WHERE c.status = 'new'"
    new_status_records = query_container('emails-status', status_query)

    logging.info(f'Found {len(new_status_records)} emails with new status')

    # If no emails with 'new' status, return early
    if not new_status_records:
      logging.info('No emails with new status found, nothing to categorize')
      return func.HttpResponse(
          json.dumps({
              "message": "No emails with 'new' status found to categorize",
              "emails_processed": 0
          }),
          status_code=200,
          mimetype="application/json"
      )

    # Step 2: Extract email IDs from status records
    email_ids = [record['id'] for record in new_status_records]

    # Step 3: Query emails-content for corresponding emails
    # Create a parameterized query to avoid SQL injection
    id_placeholders = ', '.join([f'@id{i}' for i in range(len(email_ids))])
    content_query = f"SELECT c.id, c.subject, c.body FROM c WHERE c.id IN ({id_placeholders})"

    # Create parameters for the query
    parameters = [{"name": f"@id{i}", "value": email_id} for i, email_id in enumerate(email_ids)]

    # Execute the query
    emails_to_categorize = query_container('emails-content', content_query, parameters)

    logging.info(f'Retrieved {len(emails_to_categorize)} email contents for categorization')

    # Step 4: For each email, make LLM call to determine labels and update status
    categorization_results = []
    failed_categorizations = []

    for email in emails_to_categorize:
      try:
        email_id = email['id']
        logging.info(f'Categorizing email {email_id}')

        # Get labels from LLM
        labels = llm_categorize(email)

        # Update the status record with new status and labels
        status_update = {
          "id": email_id,
          "status": "categorized",
          "labels": labels
        }

        # Update the status in the database
        upsert_item('emails-status', status_update)

        categorization_results.append({
          "email_id": email_id,
          "labels": labels,
          "success": True
        })

        logging.info(f'Successfully categorized email {email_id}: {labels}')

      except Exception as e:
        logging.error(f'Failed to categorize email {email.get("id", "unknown")}: {str(e)}')
        failed_categorizations.append({
          "email_id": email.get('id', 'unknown'),
          "error": str(e),
          "success": False
        })

    # Step 5: Return categorization results
    total_processed = len(categorization_results) + len(failed_categorizations)

    logging.info(
      f'Categorization complete: {len(categorization_results)} successful, {len(failed_categorizations)} failed')

    return func.HttpResponse(
        json.dumps({
            "message": "Email categorization completed",
            "total_emails": total_processed,
            "successful_categorizations": len(categorization_results),
            "failed_categorizations": len(failed_categorizations),
            "results": categorization_results,
            "failures": failed_categorizations
        }),
        status_code=200,
        mimetype="application/json"
    )

  except Exception as e:
    logging.error(f"Error categorizing emails: {str(e)}")
    return func.HttpResponse(
        json.dumps({"error": "Failed to categorize emails"}),
        status_code=500,
        mimetype="application/json"
    )


def llm_categorize(email: Dict[str, Any]) -> Dict[str, str]:
  """
  Categorize an email using LLM to determine industry and category labels.

  Args:
    email: Email data with 'subject' and 'body' fields

  Returns:
    Dictionary with 'industry' and 'category' labels
  """
  email_str = f'### Email Content\n\nSubject: {email["subject"]}\n\nBody: {email["body"]["content"]}'

  class CategoryOutput(BaseModel):
    industry: Literal['insurance', 'consumer']
    category: Literal['appetite', 'billing', 'docRequest', 'endorsement', 'underwriting', 'receipt']

  llm = LLMInterface.create(provider_name='azure-openai',
                            output_format=CategoryOutput, system_prompt=CATEGORIZE_EMAILS_SYSTEM_PROMPT)

  response = llm.generate(prompt=email_str)

  return {
    "industry": response.industry,
    "category": response.category
  }
