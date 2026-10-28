import os

from google.adk.auth.auth_credential import AuthCredential
from google.adk.auth.auth_tool import AuthConfig
from google.adk.auth.credential_manager import CredentialManager
from google.adk.integrations.agent_identity import (
    GcpAuthProvider,
    GcpAuthProviderScheme,
)
from google.adk.tools.authenticated_function_tool import AuthenticatedFunctionTool

from app.salesforce_client import SalesforceClient

# Full resource name of the 2LO auth provider you created in the auth provider task.
SALESFORCE_AUTH_PROVIDER_URI = os.environ["SALESFORCE_AUTH_PROVIDER_URI"]

# TODO 1: register the Google Cloud auth provider, then build the
# AuthConfig that names the 2LO auth provider. Salesforce's client-credentials
# grant takes no scope. This can be done as:
#     CredentialManager.register_auth_provider(GcpAuthProvider())
#     salesforce_auth_config = AuthConfig(
#         auth_scheme=GcpAuthProviderScheme(name=SALESFORCE_AUTH_PROVIDER_URI)
#     )
CredentialManager.register_auth_provider(GcpAuthProvider())
salesforce_auth_config = AuthConfig(
    auth_scheme=GcpAuthProviderScheme(name=SALESFORCE_AUTH_PROVIDER_URI)
)


def _extract_token(credential: AuthCredential) -> str | None:
    """Pulls the access token out of the credential Auth Manager resolved."""
    if not credential:
        return None
    if credential.oauth2 and credential.oauth2.access_token:
        return credential.oauth2.access_token
    if (
        credential.http
        and credential.http.credentials
        and credential.http.credentials.token
    ):
        return credential.http.credentials.token
    if credential.http and credential.http.additional_headers:
        h = credential.http.additional_headers
        return (
            h.get("X-API-Key")
            or h.get("X-GOOG-API-KEY")
            or h.get("Authorization", "").replace("Bearer ", "")
            or None
        )
    return None


def build_search_salesforce(client: SalesforceClient):
    """Builds the Salesforce search tool bound to a configured client.

    Args:
        client: A credential-free ``SalesforceClient`` (My Domain + API version).

    Returns:
        The ``search_salesforce`` ``AuthenticatedFunctionTool`` for the agent.
    """

    # TODO 2: a function tool receives the resolved credential as an
    # injected argument. Add a `credential: AuthCredential` parameter to this
    # function's signature (alongside query), then replace the
    # `access_token = None` line below with access_token = _extract_token(credential).
    def search_salesforce(query: str, credential: AuthCredential) -> dict:
        """Searches the company's Salesforce document library (Files).

        Runs a SOSL full-text search across every file the application can read;
        the caller does not need to know a file name or folder.

        Args:
            query: The search term or issue description.

        Returns:
            A dict with a 'status' key; on success, 'data' holds matching
            documents (each a {'name', 'url', 'snippet'} dict). On failure,
            'error_message' explains why.
        """
        access_token = _extract_token(credential)
        if not access_token:
            return {
                "status": "error",
                "error_message": "Salesforce auth failed: no token from Auth Manager.",
            }

        try:
            documents = client.search_files(access_token, query)
        except Exception as e:  # surface any search failure to the model
            return {
                "status": "error",
                "error_message": f"Salesforce search failed: {e}",
            }

        return {
            "status": "success",
            "query": query,
            "data": documents,
        }

    # TODO 3: return an AuthenticatedFunctionTool that wraps
    # search_salesforce with salesforce_auth_config, so the ADK resolves the
    # auth provider and injects the credential before each call, e.g.
    #     return AuthenticatedFunctionTool(
    #         func=search_salesforce, auth_config=salesforce_auth_config
    #     )
    return AuthenticatedFunctionTool(
        func=search_salesforce, auth_config=salesforce_auth_config
    )
