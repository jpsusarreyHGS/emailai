import sys

from utils.db import get_containers, query_container, test_connection

if __name__ == "__main__":
  print("Testing CosmosDB connection...")
  if test_connection():
    print("✅ Connection successful!")

    print("\nListing containers...")
    try:
      containers = get_containers()
      if containers:
        print(f"Found {len(containers)} container(s):")
        for container in containers:
          print(f"  - {container['id']}")
      else:
        print("No containers found in the database.")
    except Exception as e:
      print(f"❌ Failed to list containers: {e}")
      sys.exit(1)

    print("\nQuerying 'emails-content' container...")
    try:
      items = query_container("emails-content", "SELECT * FROM c")
      print(f"Found {len(items)} item(s) in 'emails-content' container")
    except Exception as e:
      print(f"❌ Failed to query 'emails-content' container: {e}")
      sys.exit(1)
  else:
    print("❌ Connection failed!")
    sys.exit(1)
