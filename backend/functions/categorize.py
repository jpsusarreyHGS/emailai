import json
import logging
from typing import Any, Dict, Literal

import azure.functions as func
from aihub import LLMInterface
from functions.prompts.categorize import CATEGORIZE_EMAILS_SYSTEM_PROMPT
from pydantic import BaseModel
from utils.db import bulk_upsert_items, query_container

AGENTS = {
    "agent_001": {
        "name": "Coach Gerver",
        "skills": ["insurance.endorsement", "insurance.docRequest"]
    },
    "agent_002": {
        "name": "Alice Thompson",
        "skills": ["insurance.appetite", "insurance.billing"]
    },
    "agent_003": {
        "name": "Bob Hernandez",
        "skills": ["consumer.receipt"]
    },
    "agent_004": {
        "name": "Cara Park",
        "skills": ["insurance.underwriting"]
    }
}


def assign_agent(labels: Dict[str, str]) -> str:
  """
  Assign an agent based on the email labels.

  Args:
    labels: Dictionary with 'industry' and 'category' labels

  Returns:
    Agent ID for the agent that handles this type of email
  """
  # Create the skill string from labels
  skill_needed = f"{labels['industry']}.{labels['category']}"

  # Find the agent with this skill
  for agent_id, agent_data in AGENTS.items():
    if skill_needed in agent_data['skills']:
      return agent_id

  # If no agent found, log warning and return None (should not happen with current setup)
  logging.warning(f'No agent found for skill: {skill_needed}')
  return None


def categorize_emails(req: func.HttpRequest) -> func.HttpResponse:
  """
  Categorize all emails with 'new' status using LLM and assign them to agents.

  This function will:
  1. Get all emails with status 'new' from emails-content container
  2. For each email, use LLM to determine industry and category labels
  3. Assign the email to an agent based on the labels
  4. Update the email status to 'categorized' and add labels and assigned agent in emails-content container
  5. Return the results of the categorization and assignment process
  """
  try:
    logging.info('Starting email categorization and agent assignment process for all new emails')

    # Step 1: Query emails-content for all records with status = 'new'
    content_query = "SELECT * FROM c WHERE c.status = 'new'"
    emails_to_categorize = query_container('emails-content', content_query)

    logging.info(f'Found {len(emails_to_categorize)} emails with new status')

    # If no emails with 'new' status, return early
    if not emails_to_categorize:
      logging.info('No emails with new status found, nothing to categorize')
      return func.HttpResponse(
          json.dumps({
              "message": "No emails with 'new' status found to categorize",
              "emails_processed": 0
          }),
          status_code=200,
          mimetype="application/json"
      )

    # Step 2: For each email, make LLM call to determine labels and update status
    categorization_results = []
    failed_categorizations = []
    emails_to_update = []  # Collect all email updates for bulk upsert

    for email in emails_to_categorize:
      try:
        email_id = email['id']
        logging.info(f'Categorizing email {email_id}')

        # Get labels from LLM
        labels = llm_categorize(email)

        # Assign agent based on labels
        assigned_agent = assign_agent(labels)

        # Update the email record with new status, labels, and assigned agent (preserve all existing fields)
        email_update = email.copy()  # Start with all existing fields
        email_update["status"] = "categorized"  # Update status
        email_update["labels"] = labels  # Add labels
        email_update["assigned_agent"] = assigned_agent  # Add assigned agent

        # Add to bulk update list
        emails_to_update.append(email_update)

        categorization_results.append({
          "email_id": email_id,
          "labels": labels,
          "assigned_agent": assigned_agent,
          "success": True
        })

        logging.info(
          f'Successfully categorized email {email_id}: {labels}, assigned to {assigned_agent}')

      except Exception as e:
        logging.error(f'Failed to categorize email {email.get("id", "unknown")}: {str(e)}')
        failed_categorizations.append({
          "email_id": email.get('id', 'unknown'),
          "error": str(e),
          "success": False
        })

    # Bulk update all categorized emails in the database
    if emails_to_update:
      logging.info(f'Bulk updating {len(emails_to_update)} categorized emails in database')
      bulk_upsert_items('emails-content', emails_to_update)
      logging.info('Bulk update completed successfully')

    # Step 3: Return categorization results
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
  email_str = f'### Email Content\n\nSubject: {email["subject"]}\n\nBody: {email["body"]["content"]}\n\nhasAttachments: {email['hasAttachments']}'

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
