"""
Database utilities for CosmosDB access.

Required environment variables:
- COSMOS_CONNECTION_STRING: CosmosDB connection string
- COSMOS_DATABASE_NAME: Name of the CosmosDB database (e.g., 'emails')

Environment configurations:

1. Local development (scripts):
   - Set variables in a .env file in the project root

2. Local Azure Functions CLI (func start):
   - Set variables in local.settings.json Values section, OR
   - Set variables in .env file (both are supported)

3. Deployed Azure Functions:
   - Set variables as Application Settings in the Azure portal

The utilities automatically detect the environment and load configuration appropriately.
"""

import os

from azure.cosmos import CosmosClient


# Detect if we're running in different environments
def _is_deployed_azure_functions():
  """Check if we're running in deployed Azure Functions (not local CLI)."""
  return (
      os.getenv('WEBSITE_SITE_NAME') is not None or
      os.getenv('AZURE_FUNCTIONS_ENVIRONMENT') is not None
  )


def _is_local_functions_cli():
  """Check if we're running locally with Azure Functions Core Tools."""
  return (
      os.getenv('FUNCTIONS_WORKER_RUNTIME') is not None and
      not _is_deployed_azure_functions()
  )


# Load .env file for local development (both scripts and Functions CLI)
if not _is_deployed_azure_functions():
  try:
    from dotenv import load_dotenv
    load_dotenv()
  except ImportError:
    # dotenv not available, which is fine in deployed Azure Functions
    pass


def get_cosmos_client():
  """Get a CosmosDB client using connection string from environment."""
  connection_string = os.getenv('COSMOS_CONNECTION_STRING')
  if not connection_string:
    if _is_deployed_azure_functions():
      env_context = "Azure Functions Application Settings"
    elif _is_local_functions_cli():
      env_context = "local.settings.json Values section or .env file"
    else:
      env_context = "local .env file"
    raise ValueError(f"COSMOS_CONNECTION_STRING environment variable not set. "
                     f"Please configure it in {env_context}")
  return CosmosClient.from_connection_string(connection_string)


def get_database():
  """Get the database specified in environment."""
  client = get_cosmos_client()
  database_name = os.getenv('COSMOS_DATABASE_NAME')
  if not database_name:
    if _is_deployed_azure_functions():
      env_context = "Azure Functions Application Settings"
    elif _is_local_functions_cli():
      env_context = "local.settings.json Values section or .env file"
    else:
      env_context = "local .env file"
    raise ValueError(f"COSMOS_DATABASE_NAME environment variable not set. "
                     f"Please configure it in {env_context}")
  return client.get_database_client(database_name)


def get_containers():
  """Get all containers in the database."""
  database = get_database()
  return list(database.list_containers())


def query_container(container_name, query, parameters=None):
  """Run a query on the specified container."""
  database = get_database()
  container = database.get_container_client(container_name)

  # Execute the query
  items = container.query_items(
    query=query,
    parameters=parameters,
    enable_cross_partition_query=True
  )

  return list(items)


def create_item(container_name, item):
  """Create a new item in the specified container with automatic ID generation."""
  database = get_database()
  container = database.get_container_client(container_name)
  return container.create_item(item, enable_automatic_id_generation=True)


def upsert_item(container_name, item):
  """Insert or update an item in the specified container."""
  database = get_database()
  container = database.get_container_client(container_name)
  return container.upsert_item(item)


def bulk_create_items(container_name, items):
  """Create multiple new items in the specified container with automatic ID generation."""
  if not items:
    return []

  database = get_database()
  container = database.get_container_client(container_name)

  results = []
  failed_items = []

  # Create items individually (batch operations require same partition key)
  for item in items:
    try:
      result = container.create_item(item, enable_automatic_id_generation=True)
      results.append(result)
    except Exception as e:
      failed_items.append({"item": item, "error": str(e)})

  if failed_items:
    import logging
    logging.warning(f"Failed to create {len(failed_items)} items")
    for failed in failed_items:
      logging.error(f"  - Error for item {failed['item'].get('id', 'unknown')}: {failed['error']}")

  return results


def bulk_upsert_items(container_name, items):
  """Insert or update multiple items in the specified container."""
  if not items:
    return []

  database = get_database()
  container = database.get_container_client(container_name)

  results = []
  failed_items = []

  # Upsert items individually (batch operations require same partition key)
  for item in items:
    try:
      result = container.upsert_item(item)
      results.append(result)
    except Exception as e:
      failed_items.append({"item": item, "error": str(e)})

  if failed_items:
    import logging
    logging.warning(f"Failed to upsert {len(failed_items)} items")
    for failed in failed_items:
      logging.error(f"  - Error for item {failed['item'].get('id', 'unknown')}: {failed['error']}")

  return results


def test_connection():
  """Test if the connection to CosmosDB is working."""
  import logging

  if _is_deployed_azure_functions():
    env_type = "Deployed Azure Functions"
  elif _is_local_functions_cli():
    env_type = "Local Azure Functions CLI"
  else:
    env_type = "Local Development"

  logging.info(f"Testing CosmosDB connection in {env_type} environment")

  try:
    database = get_database()
    # Simple test - get database properties
    database.read()
    logging.info("CosmosDB connection test successful")
    return True
  except Exception as e:
    logging.error(f"CosmosDB connection failed: {e}")
    return False
