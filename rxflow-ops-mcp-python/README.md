# RxFlowOpsMcp (Python)

An MCP (Model Context Protocol) server, stdio transport, that lets an MCP
client read and act on **real** Azure Boards work items while every
mutating action passes through an explicit permission gate, and every tool
call is observable through pre-/post-call hooks.

Python port of the verified `RxFlowOpsMcp-Azure` (.NET) server — same tool
names and signatures, so either implementation is a drop-in replacement
for the other in an MCP client config.

## Tools

Azure DevOps–backed (real REST API v7.1, no mocking):

- `get_ticket(work_item_id)`
- `search_incidents(wiql, max_results=25)`
- `list_valid_states(work_item_type)`
- `create_change_request(project, title, description, work_item_type="Change Request")` — **mutating**
- `update_ticket_status(work_item_id, new_state, comment=None)` — **mutating**

Ops-catalog–backed (real HTTP, or `OPS_CATALOG_MOCK=true` for canned data):

- `get_service_owner(service_name)`
- `get_runbook(service_name)`
- `get_lab_health(lab_name)`

## Configuration

| Env var | Required for | Notes |
|---|---|---|
| `AZDO_ORG` | all Azure DevOps tools | organization name in `dev.azure.com/{org}` |
| `AZDO_PROJECT` | all Azure DevOps tools | default project (used by `update_ticket_status`) |
| `AZDO_PAT` | all Azure DevOps tools | Personal Access Token, Basic auth with empty username |
| `AZDO_WRITABLE_PROJECTS` | mutating tools | comma-separated allow-list, case-insensitive |
| `OPS_CATALOG_BASE_URL` | ops-catalog tools (real mode) | e.g. `https://ops.example.com` |
| `OPS_CATALOG_TOKEN` | ops-catalog tools (real mode) | optional bearer token |
| `OPS_CATALOG_MOCK` | — | `true` opts into canned data, zero HTTP calls |

Missing env vars raise a clear error at first use of the relevant client,
not at import time — `tools/list` works before credentials are configured.

## Two-sided write safety

Every external write goes through **two** independent gates:

1. **Server-side (this code):** `PermissionGate` checks the target project
   against `AZDO_WRITABLE_PROJECTS` *before* any HTTP call. A project not
   on the list is rejected with zero outbound requests — verifiable in the
   stderr log as a `tool_call.start` line for a mutating tool followed
   directly by a `tool_call.end status=failure` line, with no HTTP request
   logged in between.
2. **Client-side (the MCP client, e.g. Claude):** the client is expected to
   ask a human to confirm before invoking `create_change_request` or
   `update_ticket_status` at all. This server does not and cannot enforce
   that half — it's a property of how the MCP client is configured to
   handle mutating tools.

Both halves must hold for this to be safe in practice: the allow-list
limits *where* writes can land even if a client skips confirmation, and
the confirmation step lets a human veto a write to an allow-listed project
before it happens.

## Development

```bash
uv sync --extra dev
uv run pytest -q
```

Manual/live smoke test (spawns the server as a subprocess and speaks real
JSON-RPC over stdio — avoid piping a static file into stdin via shell
redirection, which can silently swallow stdout):

```bash
uv run python scripts/smoke_test.py
```

## MCP client config

```json
{
  "mcpServers": {
    "rxflow-ops-azure-python": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--project", "/absolute/path/to/rxflow-ops-mcp-python", "rxflow-ops-mcp"],
      "env": {
        "AZDO_ORG": "your-azdo-org",
        "AZDO_PROJECT": "RxFlow",
        "AZDO_PAT": "your_personal_access_token",
        "AZDO_WRITABLE_PROJECTS": "RxFlow",
        "OPS_CATALOG_MOCK": "true"
      }
    }
  }
}
```

## Gotchas (carried over from the .NET build)

- Azure DevOps and the Azure Portal are different products — sign in at
  `https://dev.azure.com` directly (or `https://aex.dev.azure.com/` if
  that redirects to a marketing page), not `portal.azure.com`.
- Creating a new Azure DevOps org requires linking an Azure subscription
  for billing, even though Azure DevOps itself is free.
- `workitemsbatch` is an **org-level** endpoint, not project-scoped.
- There's no generic "list transitions" endpoint — use
  `GET /_apis/wit/workitemtypes/{type}/states` for valid state names.
- A real process template may only offer `Issue`/`Epic` work item types,
  not `Task` or `"Change Request"` — pass `work_item_type="Issue"`
  explicitly against such a project; don't rely on the default.
- Never let a PAT appear in stdout, logs, or a response. If one is pasted
  into chat, treat it as compromised and tell the user to revoke/reissue.
- The server has no live-reload — restart the MCP client after changing
  env vars or `.mcp.json`.
