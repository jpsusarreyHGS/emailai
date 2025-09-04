import sys

from utils.db import bulk_upsert_items, query_container


def create_email_status():
  """Create status items for all emails in the content container."""
  print("Fetching all items from 'emails-content' container...")

  try:
    # Get all items from emails-content
    content_items = query_container("emails-content", "SELECT * FROM c")
    print(f"Found {len(content_items)} items in 'emails-content' container")

    if not content_items:
      print("No items found. Nothing to process.")
      return

    print("Checking existing items in 'emails-status' container...")

    # Get existing status items to avoid duplicates
    try:
      existing_status_items = query_container("emails-status", "SELECT c.id FROM c")
      existing_ids = {item["id"] for item in existing_status_items}
      print(f"Found {len(existing_ids)} existing status items")
    except Exception as e:
      print(f"Warning: Could not query emails-status container (might not exist yet): {e}")
      existing_ids = set()

    print(f"Preparing new status items...")

    # Collect all items that need status creation
    items_to_create = []
    skipped_count = 0

    for item in content_items:
      item_id = item["id"]

      # Skip if status already exists
      if item_id in existing_ids:
        skipped_count += 1
        continue

      # Create status item with same id and processed: false
      status_item = {
          "id": item_id,
          "status": "new"
      }

      items_to_create.append(status_item)

    if items_to_create:
      print(f"Creating {len(items_to_create)} status items...")
      try:
        results = bulk_upsert_items("emails-status", items_to_create)
        success_count = len(results)
        print(f"✅ Successfully created {success_count} new status items")
      except Exception as e:
        print(f"❌ Failed to create status items: {e}")
        return
    else:
      print("No new status items to create")
      success_count = 0

    print(f"⏭️  Skipped {skipped_count} items that already have status")

  except Exception as e:
    print(f"❌ Failed to process email status creation: {e}")
    sys.exit(1)


if __name__ == "__main__":
  create_email_status()
