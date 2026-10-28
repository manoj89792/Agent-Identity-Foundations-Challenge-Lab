import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.auth.credential_manager import CredentialManager
from google.adk.integrations.agent_identity import GcpAuthProvider, GcpAuthProviderScheme
from google.adk.models import Gemini
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.genai import types

load_dotenv()

MODEL = os.environ["MODEL"]
GITHUB_MCP_URL = os.getenv("GITHUB_MCP_URL", "https://api.githubcopilot.com/mcp/")
# Full resource name of the API-key auth provider you created in Task 2.
GITHUB_AUTH_PROVIDER_URI = os.environ["GITHUB_AUTH_PROVIDER_URI"]

# Only expose the read tools this agent needs.
GITHUB_TOOL_FILTER = ["search_repositories", "search_issues", "list_issues"]

# TODO 1: register the Google Cloud auth provider so the
# CredentialManager can resolve the auth provider credential using
# the agent's own identity. This runs once at import.
CredentialManager.register_auth_provider(GcpAuthProvider())

# TODO 2: create the auth scheme that names which auth provider the ADK
# should resolve before the tool runs, e.g.
#     github_auth_scheme = GcpAuthProviderScheme(name=GITHUB_AUTH_PROVIDER_URI)
github_auth_scheme = GcpAuthProviderScheme(name=GITHUB_AUTH_PROVIDER_URI)


def github_mcp_toolset() -> McpToolset:
    """MCP toolset for the GitHub server, authenticated via auth manager."""
    toolset = None

    def github_header_provider(readonly_ctx) -> dict[str, str]:
        if not toolset or not toolset.get_auth_config():
            return {}
        auth_config = toolset.get_auth_config()
        cred = None
        if readonly_ctx and hasattr(readonly_ctx, "get_credential"):
            cred = readonly_ctx.get_credential(auth_config.credential_key)
        if not cred:
            cred = auth_config.exchanged_auth_credential
        if not cred or not cred.http:
            return {}
        token = None
        if cred.http.credentials and cred.http.credentials.token:
            token = cred.http.credentials.token
        elif cred.http.additional_headers:
            token = cred.http.additional_headers.get(
                "X-API-Key"
            ) or cred.http.additional_headers.get("X-GOOG-API-KEY")
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    # TODO 3: Build and return the McpToolset as github_mcp_toolset.
    # Pass the connection params
    # (StreamableHTTPConnectionParams(url=GITHUB_MCP_URL)),
    # the github_auth_scheme, the GITHUB_TOOL_FILTER, and the
    # header_provider. No PAT / hardcoded Authorization header.
    toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(url=GITHUB_MCP_URL),
        auth_scheme=github_auth_scheme,
        tool_filter=GITHUB_TOOL_FILTER,
        header_provider=github_header_provider,
    )
    return toolset


root_agent = Agent(
    name="github_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    description=(
        "Specialized assistant for GitHub: searches repositories, issues, and "
        "pull requests via the GitHub MCP server."
    ),
    instruction=(
        "You are a specialized assistant for interacting with GitHub. "
        "Use the provided tools to search for repositories, find issues, and "
        "retrieve pull-request information, then answer with what you find. "
        "Be concise and cite the repository names / issue numbers you used."
    ),
    tools=[github_mcp_toolset()],
)

app = App(root_agent=root_agent, name="app")
