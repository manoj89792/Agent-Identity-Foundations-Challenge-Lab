# Enterprise Agents with Google Cloud Agent Identity Auth Manager

This repository contains the refactored enterprise agents (`github-agent` and `salesforce-agent`) built with the **Google Agent Development Kit (ADK)** and integrated with **Google Cloud Agent Identity Auth Manager** (`agentidentity.googleapis.com`).

For the complete step-by-step operational guide, commands, architecture diagrams, and troubleshooting instructions, see **[RUNBOOK.md](./RUNBOOK.md)**.

## Repository Structure

```text
.
├── README.md                  # Repository overview and quick start
├── RUNBOOK.md                 # Complete step-by-step implementation runbook (Tasks 1-5)
├── github-agent/              # GitHub MCP Specialist Agent (Vertex AI Agent Runtime + SPIFFE Identity)
│   ├── .env.example           # Example environment configuration (no secrets)
│   ├── Dockerfile             # Container definition
│   ├── deploy_with_identity.sh# Two-phase Agent Runtime deployment script with AGENT_IDENTITY
│   └── agent/
│       ├── agent.py           # ADK Agent using McpToolset + GcpAuthProviderScheme + header_provider
│       ├── main.py            # FastAPI A2A server using AgentCardBuilder
│       └── requirements.txt   # Python dependencies (google-adk[gcp,agent-identity,a2a,mcp])
└── salesforce-agent/          # Salesforce Files Specialist Agent (Cloud Run + Service Account Identity)
    ├── .env.example           # Example environment configuration (no secrets)
    ├── Dockerfile             # Cloud Run container definition
    ├── agents-cli-manifest.yaml
    ├── pyproject.toml         # Project dependencies (google-adk[gcp,agent-identity])
    ├── uv.lock                # Locked dependencies
    └── app/
        ├── agent.py           # ADK Agent definition (credential-free SalesforceClient)
        ├── salesforce_client.py # SOSL Files search & excerpt client using self.instance_url
        ├── tools.py           # AuthenticatedFunctionTool + GcpAuthProviderScheme + injected AuthCredential
        └── fast_api_app.py    # FastAPI + A2A entrypoint
```

## Highlights of Changes

1. **Zero Hardcoded Secrets in Agent Code or `.env`**:
   - Removed `GITHUB_PERSONAL_ACCESS_TOKEN` from `github-agent`.
   - Removed `SALESFORCE_CLIENT_ID` and `SALESFORCE_CLIENT_SECRET` from `salesforce-agent`.
2. **Centralized Credential Management via Agent Identity Auth Manager**:
   - `github-mcp-auth-provider`: Stores the GitHub token as an API-key Auth Provider and resolves it at tool-call time for `McpToolset` via `header_provider`.
   - `salesforce-2lo-auth-provider`: Stores the Salesforce Connected App consumer key, secret, and token endpoint as a 2-Legged OAuth (2LO) Auth Provider, performing the `client_credentials` token exchange automatically and injecting `AuthCredential` into `AuthenticatedFunctionTool`.
3. **Least-Privilege IAM Access Control**:
   - `github-agent` authenticates to Auth Manager using its Vertex AI Agent Runtime **SPIFFE workload identity** (`principal://agents.global.org-...`).
   - `salesforce-agent` authenticates to Auth Manager using its **Cloud Run service account** (`serviceAccount:...`).
   - Both principals are granted `roles/agentidentity.user` on their respective Auth Provider resource.
