"""
Microsoft Graph authentication and helper utilities (delegated permissions).

Environment variables expected:
- GRAPH_CLIENT_ID: Entra ID application (client) ID
- GRAPH_CLIENT_SECRET: Client secret for the app (required for web app flow)
- GRAPH_TENANT_ID: Directory (tenant) ID
- GRAPH_REDIRECT_URI: Redirect URI configured in the app (e.g., http://localhost:7071/api/graph-connect)
- GRAPH_SHARED_MAILBOX_UPN: UPN or email of the shared mailbox to operate on (e.g., shared@contoso.com)
- GRAPH_SCOPES: Optional space-separated list of scopes (defaults to Mail.ReadWrite.Shared Mail.Send.Shared offline_access openid profile)
- GRAPH_TOKEN_CACHE_PATH: Optional path for an MSAL token cache file (default: .graph_token_cache.bin in backend directory)

These helpers are designed to be reused by multiple Azure Function endpoints.
"""

import json
import os
from typing import List, Optional, Tuple

import msal
import requests


# Load .env locally (consistent with utils.db)
def _is_deployed_azure_functions():
  return (
      os.getenv('WEBSITE_SITE_NAME') is not None or
      os.getenv('AZURE_FUNCTIONS_ENVIRONMENT') is not None
  )


if not _is_deployed_azure_functions():
  try:
    from dotenv import load_dotenv
    load_dotenv()
  except Exception:
    pass


def get_redirect_uri() -> str:
  return os.getenv('GRAPH_REDIRECT_URI') or 'http://localhost:7071/api/graph-connect'


def get_default_scopes() -> List[str]:
  scopes_env = os.getenv('GRAPH_SCOPES')
  if scopes_env:
    # Allow space or comma separated
    parts = [p.strip() for p in scopes_env.replace(',', ' ').split(' ') if p.strip()]
    return parts
  return [
    'https://graph.microsoft.com/Mail.ReadWrite.Shared',
    'https://graph.microsoft.com/Mail.Send.Shared',
    'offline_access',
    'openid',
    'profile'
  ]


def _get_token_cache_path() -> str:
  override = os.getenv('GRAPH_TOKEN_CACHE_PATH')
  if override:
    return override
  # Default to a file under backend directory to keep separate from source root
  backend_dir = os.path.dirname(os.path.dirname(__file__))
  return os.path.join(backend_dir, '.graph_token_cache.bin')


def _load_cache() -> msal.SerializableTokenCache:
  cache = msal.SerializableTokenCache()
  cache_path = _get_token_cache_path()
  if os.path.exists(cache_path):
    try:
      with open(cache_path, 'r', encoding='utf-8') as f:
        cache.deserialize(f.read())
    except Exception:
      # Corrupt cache; start fresh
      pass
  return cache


def _save_cache(cache: msal.SerializableTokenCache) -> None:
  if cache.has_state_changed:
    cache_path = _get_token_cache_path()
    # Ensure directory exists
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, 'w', encoding='utf-8') as f:
      f.write(cache.serialize())


def _get_msal_app(cache: Optional[msal.TokenCache] = None) -> msal.ConfidentialClientApplication:
  client_id = os.getenv('GRAPH_CLIENT_ID')
  client_secret = os.getenv('GRAPH_CLIENT_SECRET')
  tenant_id = os.getenv('GRAPH_TENANT_ID')

  if not client_id or not client_secret or not tenant_id:
    missing = [name for name, val in [('GRAPH_CLIENT_ID', client_id), (
      'GRAPH_CLIENT_SECRET', client_secret), ('GRAPH_TENANT_ID', tenant_id)] if not val]
    raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

  authority = f"https://login.microsoftonline.com/{tenant_id}"
  return msal.ConfidentialClientApplication(
      client_id=client_id,
      client_credential=client_secret,
      authority=authority,
      token_cache=cache,
  )


def build_authorization_url(scopes: Optional[List[str]] = None, redirect_uri: Optional[str] = None, state: Optional[str] = None) -> str:
  cache = _load_cache()
  app = _get_msal_app(cache)
  scopes_to_use = scopes or get_default_scopes()
  redirect_to_use = redirect_uri or get_redirect_uri()
  url = app.get_authorization_request_url(
      scopes=scopes_to_use,
      redirect_uri=redirect_to_use,
      state=state or 'state',
      response_mode='query'
  )
  return url


def exchange_code_for_token(code: str, scopes: Optional[List[str]] = None, redirect_uri: Optional[str] = None) -> dict:
  cache = _load_cache()
  app = _get_msal_app(cache)
  scopes_to_use = scopes or get_default_scopes()
  redirect_to_use = redirect_uri or get_redirect_uri()

  result = app.acquire_token_by_authorization_code(
      code=code,
      scopes=scopes_to_use,
      redirect_uri=redirect_to_use
  )

  _save_cache(cache)
  return result


def get_access_token(scopes: Optional[List[str]] = None) -> Optional[str]:
  cache = _load_cache()
  app = _get_msal_app(cache)
  scopes_to_use = scopes or get_default_scopes()

  accounts = app.get_accounts()
  if not accounts:
    return None

  # Use first account in cache
  result = app.acquire_token_silent(scopes=scopes_to_use, account=accounts[0])
  if not result or 'access_token' not in result:
    return None
  return result['access_token']


def ensure_token_or_auth_url(scopes: Optional[List[str]] = None, redirect_uri: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
  token = get_access_token(scopes)
  if token:
    return token, None
  return None, build_authorization_url(scopes=scopes, redirect_uri=redirect_uri)


def graph_get(url: str, access_token: str, params: Optional[dict] = None) -> requests.Response:
  headers = {
    'Authorization': f'Bearer {access_token}',
    'Accept': 'application/json'
  }
  return requests.get(url, headers=headers, params=params, timeout=30)


def graph_post(url: str, access_token: str, payload: dict) -> requests.Response:
  headers = {
    'Authorization': f'Bearer {access_token}',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
  }
  return requests.post(url, headers=headers, json=payload, timeout=30)


def create_message_in_inbox(access_token: str, message: dict, mailbox_upn: Optional[str] = None) -> dict:
  """
  Create a message directly in the Inbox folder of the mailbox.

  Returns parsed JSON of the created message.
  """
  mailbox = mailbox_upn or os.getenv('GRAPH_SHARED_MAILBOX_UPN')
  if not mailbox:
    raise ValueError('GRAPH_SHARED_MAILBOX_UPN is not set and no mailbox was provided')

  base_url = 'https://graph.microsoft.com/v1.0'
  endpoint = f"{base_url}/users/{mailbox}/mailFolders/Inbox/messages"
  resp = graph_post(endpoint, access_token, payload=message)
  if resp.status_code >= 400:
    try:
      data = resp.json()
    except Exception:
      data = {'error': resp.text}
    raise RuntimeError(json.dumps({'status': resp.status_code, 'error': data}))
  return resp.json()


def list_inbox_messages(access_token: str, mailbox_upn: Optional[str] = None, top: int = 50, unread: Optional[bool] = None) -> dict:
  """
  List messages from the Inbox of the specified mailbox using Graph v1.0.

  Returns parsed JSON from Graph.
  """
  mailbox = mailbox_upn or os.getenv('GRAPH_SHARED_MAILBOX_UPN')
  if not mailbox:
    raise ValueError('GRAPH_SHARED_MAILBOX_UPN is not set and no mailbox was provided')

  base_url = 'https://graph.microsoft.com/v1.0'
  # Use /users/{mailbox}/mailFolders/Inbox/messages for shared mailbox via delegated perms
  endpoint = f"{base_url}/users/{mailbox}/mailFolders/Inbox/messages"

  # Select common fields and order by receivedDateTime desc
  params = {
    '$top': str(top),
    '$orderby': 'receivedDateTime DESC',
    '$select': 'id,subject,receivedDateTime,from,toRecipients,hasAttachments,body'
  }

  if unread is True:
    params['$filter'] = 'isRead eq false'

  resp = graph_get(endpoint, access_token, params=params)
  if resp.status_code >= 400:
    try:
      data = resp.json()
    except Exception:
      data = {'error': resp.text}
    raise RuntimeError(json.dumps({'status': resp.status_code, 'error': data}))

  return resp.json()


def list_message_attachments(access_token: str, message_id: str, mailbox_upn: Optional[str] = None) -> dict:
  """
  List attachments for a specific message using Graph v1.0.

  Returns parsed JSON from Graph containing attachment metadata.
  Note: For file attachments, this returns metadata. To get file content,
  you'd need to make additional calls to get each attachment individually.
  """
  mailbox = mailbox_upn or os.getenv('GRAPH_SHARED_MAILBOX_UPN')
  if not mailbox:
    raise ValueError('GRAPH_SHARED_MAILBOX_UPN is not set and no mailbox was provided')

  base_url = 'https://graph.microsoft.com/v1.0'
  endpoint = f"{base_url}/users/{mailbox}/messages/{message_id}/attachments"

  # Select common attachment fields
  params = {
    '$select': 'id,name,contentType,size,lastModifiedDateTime'
  }

  resp = graph_get(endpoint, access_token, params=params)
  if resp.status_code >= 400:
    try:
      data = resp.json()
    except Exception:
      data = {'error': resp.text}
    raise RuntimeError(json.dumps({'status': resp.status_code, 'error': data}))

  return resp.json()


def get_message_attachment_content(access_token: str, message_id: str, attachment_id: str, mailbox_upn: Optional[str] = None) -> dict:
  """
  Get the content of a specific attachment using Graph v1.0.

  Returns parsed JSON from Graph containing the full attachment data including content.
  For file attachments, this includes the base64-encoded content.
  """
  mailbox = mailbox_upn or os.getenv('GRAPH_SHARED_MAILBOX_UPN')
  if not mailbox:
    raise ValueError('GRAPH_SHARED_MAILBOX_UPN is not set and no mailbox was provided')

  base_url = 'https://graph.microsoft.com/v1.0'
  endpoint = f"{base_url}/users/{mailbox}/messages/{message_id}/attachments/{attachment_id}"

  resp = graph_get(endpoint, access_token)
  if resp.status_code >= 400:
    try:
      data = resp.json()
    except Exception:
      data = {'error': resp.text}
    raise RuntimeError(json.dumps({'status': resp.status_code, 'error': data}))

  return resp.json()
