import json
import os
import sys

import html2text
from utils.db import bulk_create_items, test_connection


def process_html_content(email_data):
  """Convert HTML body content to plain text for emails with HTML content type."""
  h = html2text.HTML2Text()
  h.ignore_links = False
  h.ignore_images = True
  h.body_width = 0  # Don't wrap lines

  html_converted_count = 0

  for email in email_data:
    if (email.get('body') and
        email['body'].get('contentType') == 'html' and
            email['body'].get('content')):
      try:
        # Convert HTML to plain text
        original_content = email['body']['content']
        plain_text_content = h.handle(original_content).strip()
        email['body']['content'] = plain_text_content
        html_converted_count += 1
      except Exception as e:
        print(f"⚠️  Failed to convert HTML to text for email: {e}")
        # Continue with original content if conversion fails

  if html_converted_count > 0:
    print(f"🔄 Converted {html_converted_count} HTML email(s) to plain text")

  return email_data


def create_json_emails(json_file_path):
  """Create all email objects from a JSON file in the emails-content container."""
  print(f"Loading email data from '{json_file_path}'...")

  # Check if file exists
  if not os.path.exists(json_file_path):
    print(f"❌ File not found: {json_file_path}")
    sys.exit(1)

  try:
    # Load and parse JSON file
    with open(json_file_path, 'r', encoding='utf-8') as file:
      email_data = json.load(file)

    if not isinstance(email_data, list):
      print(f"❌ Expected JSON file to contain an array of objects, got {type(email_data).__name__}")
      sys.exit(1)

    print(f"Found {len(email_data)} email(s) in the JSON file")

    if not email_data:
      print("No emails found. Nothing to process.")
      return

    # Process HTML content and convert to plain text
    email_data = process_html_content(email_data)

    print("Testing CosmosDB connection...")
    if not test_connection():
      print("❌ Failed to connect to CosmosDB")
      sys.exit(1)

    print("Creating emails in 'emails-content' container...")
    try:
      results = bulk_create_items("emails-content", email_data)
      success_count = len(results)
      print(f"✅ Successfully created {success_count} email(s)")

      if success_count != len(email_data):
        failed_count = len(email_data) - success_count
        print(f"⚠️  {failed_count} email(s) failed to create (check logs for details)")

    except Exception as e:
      print(f"❌ Failed to create emails: {e}")
      sys.exit(1)

  except json.JSONDecodeError as e:
    print(f"❌ Invalid JSON format in file '{json_file_path}': {e}")
    sys.exit(1)
  except Exception as e:
    print(f"❌ Failed to process file '{json_file_path}': {e}")
    sys.exit(1)


def main():
  """Main function to handle command line arguments."""
  if len(sys.argv) != 2:
    print("Usage: python create_json_emails.py <path_to_json_file>")
    print("Example: python create_json_emails.py ../../resources/emails/appetite.json")
    sys.exit(1)

  json_file_path = sys.argv[1]
  create_json_emails(json_file_path)


if __name__ == "__main__":
  main()
