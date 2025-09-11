import json
import logging

import azure.functions as func
from utils.graph import (build_authorization_url, exchange_code_for_token,
                         get_default_scopes)


def graph_connect(req: func.HttpRequest) -> func.HttpResponse:
  """
  Initiate or complete Microsoft Graph delegated OAuth flow.

  - If "code" is present, exchanges it for tokens and returns a simple JSON success message.
  - If no code, issues a 302 redirect to Microsoft login/consent page.
  """
  try:
    code = req.params.get('code')
    if code:
      token_result = exchange_code_for_token(code=code, scopes=get_default_scopes())
      if 'error' in token_result:
        logging.error(f"Graph token exchange error: {token_result}")
        return func.HttpResponse(
            json.dumps({"error": "token_exchange_failed", "details": token_result}),
            status_code=400,
            mimetype="application/json"
        )
      return func.HttpResponse(
          json.dumps({"message": "Authentication completed. You can now call protected endpoints."}),
          status_code=200,
          mimetype="application/json"
      )

    # No code; redirect to consent/login
    auth_url = build_authorization_url(scopes=get_default_scopes())
    return func.HttpResponse(status_code=302, headers={"Location": auth_url})

  except Exception as e:
    logging.exception("Graph connect failed")
    return func.HttpResponse(
        json.dumps({"error": "graph_connect_failed", "details": str(e)}),
        status_code=500,
        mimetype="application/json"
    )
