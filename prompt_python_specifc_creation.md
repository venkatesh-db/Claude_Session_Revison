# Ticket: RxFlowOpsMcp — Real Azure DevOps Ops MCP Server (Python port)

Hand this whole file to whoever (or whatever agent) is building this
project. It's self-contained: context, exact requirements, gotchas already
hit once (in the original C#/.NET build of this same server), and the
acceptance bar. Following it should reproduce the project end to end in
**Python** without re-discovering the same mistakes.

## Context

This is a **Python port** of an existing, already-verified C#/.NET 8 MCP
server: [`RxFlowOpsMcp-Azure`](.) in this same workspace. That version
works — build clean, 9/9 tests, live-verified against a real Azure DevOps
org. Don't redesign the behavior; port the same architecture and the same
verified API call shapes to Python. If in doubt about a requirement, read
`RxFlowOpsMcp/*.cs` in this project first rather than guessing.

We want an MCP (Model Context Protocol) server, written in **Python 3.11+**,
that lets an MCP client (Claude, an IDE assistant, etc.) read and act on
**real** Azure Boards work items — not mocked data — while every mutating
action passes through an explicit **permission gate**, and every tool call
(read or write) is observable through **hooks** (pre-call / post-call), so
there's an audit trail and a single choke point for rate limiting,
logging, or approval prompts later.

## Goal

Build a real MCP server (`rxflow_ops_mcp`, stdio transport) exposing 8
tools across two backends — same tool names/signatures as the .NET
version, so either implementation is a drop-in replacement for the other
in an MCP client config.

### Azure DevOps–backed tools (real Azure DevOps REST API v7.1, no mocking)

| Tool | Mutating? | Behavior |
|---|---|---|
| `get_ticket(work_item_id: int)` | No | Fetch one work item by numeric id |
| `search_incidents(wiql: str, max_results: int = 25)` | No | WIQL query, hydrated via the batch endpoint |
| `list_valid_states(work_item_type: str)` | No | Valid `System.State` values for a work item type |
| `create_change_request(project: str, title: str, description: str, work_item_type: str = "Change Request")` | **Yes** | Creates a work item |
| `update_ticket_status(work_item_id: int, new_state: str, comment: str \| None = None)` | **Yes** | Sets `System.State` via JSON Patch, optionally appends a comment via `System.History` |

### Ops-catalog tools (internal service metadata — real HTTP client, with a mock fallback)

| Tool | Mutating? | Behavior |
|---|---|---|
| `get_service_owner(service_name: str)` | No | Owning team + on-call contact |
| `get_runbook(service_name: str)` | No | Operational runbook for a service |
| `get_lab_health(lab_name: str)` | No | Current health status of a lab environment |

These three have no public API spec. Build them against a configurable
`OPS_CATALOG_BASE_URL` with a reasonable REST convention
(`GET /services/{id}/owner`, `/services/{id}/runbook`,
`GET /labs/{id}/health`). Also add an explicit opt-in mock mode
(`OPS_CATALOG_MOCK=true`) that returns canned-but-realistic data with zero
HTTP calls, so the Azure DevOps tools aren't blocked on a second backend
existing. Mock mode must be opt-in, never a silent fallback.

## Requirements

1. **Real system connection** — Azure DevOps tools call the actual
   `https://dev.azure.com/{organization}/{project}/_apis/wit/...` API v7.1
   using PAT Basic auth (empty username, PAT as password: base64 of
   `f":{pat}"`), not a mock.
2. **Permissions** — `create_change_request` and `update_ticket_status`
   require an explicit project allow-list check *before* the HTTP call is
   made. Config-driven allow-list (env var or a small YAML/JSON config,
   e.g. `AZDO_WRITABLE_PROJECTS=RxFlow,OtherProject`). Rejecting a
   mutating call against a project not on the allow-list must make **zero**
   HTTP calls.
3. **Human approval before any external write** — the allow-list is the
   server-side half; the MCP client asking the human to confirm before
   invoking either mutating tool is the client-side half. Document this
   split in the README.
4. **Hooks** — every tool call (read or write) goes through a shared
   async wrapper: logs a pre-call line, runs the permission check if
   mutating, runs the actual work, logs a post-call line (elapsed time,
   success/failure) — win or lose. Implement as one function every tool
   routes through (e.g. a decorator or a `run_tool(...)` helper), not
   copy-pasted per tool.
5. **Config, not hardcoding** — `AZDO_ORG`, `AZDO_PROJECT`, `AZDO_PAT` env
   vars; writable-project allow-list via env/config; `OPS_CATALOG_BASE_URL`
   / `OPS_CATALOG_TOKEN` / `OPS_CATALOG_MOCK` env vars. Never hardcode
   secrets. Fail fast (clear exception) at first use of a client whose
   required env var is missing — don't crash the whole process at import
   time, so `tools/list` still works before credentials are configured.
6. **stdout is reserved for the MCP protocol channel** — configure Python
   `logging` to write exclusively to **stderr** (`StreamHandler(sys.stderr)`),
   never `print()` anywhere in the server.
7. **Async throughout** — use `httpx.AsyncClient` for all HTTP calls and
   `async def` tool handlers; the MCP Python SDK's stdio server is async.

## Non-goals

- No auth/session management beyond a single PAT from the environment.
- No web UI — this is a stdio MCP server for use from an MCP client config.
- No pagination beyond the first page of WIQL search results.
- No silent mocking of Azure DevOps itself — only the ops-catalog piece
  gets an opt-in mock; the ticket system is always real.

## Build steps (in order)

1. **Check Python and package versions before writing any client code —
   don't guess from memorized patterns.** Use `pip index versions mcp` /
   check PyPI for the current `mcp` (Model Context Protocol Python SDK)
   package version, and read its docs
   (`https://github.com/modelcontextprotocol/python-sdk`) for the current
   `FastMCP` or low-level `Server` API shape before scaffolding — the SDK
   API has changed across versions; don't extrapolate from an older
   tutorial.
2. **Read the current Azure DevOps REST API docs before writing the
   client** (same endpoints the .NET version already validated against a
   real org — reuse these shapes, don't rediscover them from scratch):
   - Auth: PAT over Basic auth with an **empty username** —
     `Authorization: Basic base64(":" + pat)`.
   - Work item read: `GET /{project}/_apis/wit/workitems/{id}?api-version=7.1`.
   - Search: no free-text search endpoint — use WIQL:
     `POST /{project}/_apis/wit/wiql?api-version=7.1` with `{"query": "..."}`,
     returning only `{id, url}` pairs, then hydrate via
     `POST /_apis/wit/workitemsbatch?api-version=7.1` — **this batch
     endpoint is org-level, not project-scoped**; calling it as
     `/{project}/_apis/wit/workitemsbatch` 404s.
   - Create: `POST /{project}/_apis/wit/workitems/${type}?api-version=7.1`
     with `Content-Type: application/json-patch+json` and a JSON Patch body
     (`[{"op": "add", "path": "/fields/System.Title", "value": ...}, ...]`).
   - Update: `PATCH /{project}/_apis/wit/workitems/{id}?api-version=7.1`,
     same JSON Patch content type, patching `/fields/System.State` (and
     optionally `/fields/System.History` for a comment).
   - Valid states for a type: `GET /{project}/_apis/wit/workitemtypes/{type}/states?api-version=7.1`.
3. **Scaffold the project** with `uv` or `pip` + `pyproject.toml`:
   ```toml
   [project]
   name = "rxflow-ops-mcp"
   requires-python = ">=3.11"
   dependencies = ["mcp>=1.0.0", "httpx>=0.27", "pydantic>=2.0"]

   [project.optional-dependencies]
   dev = ["pytest>=8.0", "pytest-asyncio>=0.24", "pytest-httpx>=0.30"]
   ```
4. **Structure** (one module per concern, mirrors the .NET file layout):
   - `rxflow_ops_mcp/server.py` — entrypoint: configures logging to
     stderr, builds the `FastMCP` (or low-level `Server`) instance,
     registers tools, runs the stdio transport.
   - `rxflow_ops_mcp/permission_gate.py` — `PermissionGate` class,
     config-driven allow-list, raises `PermissionDeniedError` if the
     project isn't listed.
   - `rxflow_ops_mcp/tool_call_hooks.py` — `run_tool(tool_name, *,
     is_mutating, permission_check, work)` async wrapper: logs pre/post,
     runs the permission check before work only when mutating, re-raises
     any exception from `work` after logging it.
   - `rxflow_ops_mcp/azure_devops_client.py` — `AzureDevOpsClient` using
     `httpx.AsyncClient`, PAT Basic auth from env vars, methods for
     get/search(WIQL+batch)/create/update/list-states. Expose the
     configured project as a `default_project` attribute so
     `update_ticket_status` (which takes no explicit project param) can
     still run the permission check.
   - `rxflow_ops_mcp/ops_catalog_client.py` — `OpsCatalogClient` with real
     HTTP calls plus an `OPS_CATALOG_MOCK` opt-in path returning canned
     `ServiceOwner`/`Runbook`/`LabHealth` Pydantic models.
   - `rxflow_ops_mcp/models.py` — Pydantic models for
     `ServiceOwner`/`Runbook`/`LabHealth` and any Azure DevOps response
     shapes you want typed rather than raw dicts.
   - `rxflow_ops_mcp/tools.py` — the 8 `@mcp.tool()`-decorated (or
     equivalent) functions, each routing through `run_tool`.
5. **Write tests** mirroring the .NET test suite: `pytest` +
   `pytest-asyncio`, a `tests/test_permission_gate.py` (allows
   allow-listed, case-insensitive, blocks non-listed, blocks everything
   when empty) and `tests/test_tool_call_hooks.py` (runs permission check
   before work, skips it for reads, propagates exceptions, returns work
   result). Use `pytest-httpx` (or `respx`) to mock HTTP in any client
   unit tests that aren't hitting the real API.

## Gotchas already hit once (in the .NET build of this same server) — don't repeat these

1. **Azure DevOps and the Azure Portal are different products with
   different signup flows.** Signing into `portal.azure.com` does **not**
   give you an Azure DevOps organization. Go to `https://dev.azure.com`
   directly — if that redirects to a marketing page, use
   `https://aex.dev.azure.com/` to reach the actual "Create new
   organization" screen. This is an operational/setup gotcha, not a code
   one, but it'll block manual verification if you hit it.
2. **Creating an Azure DevOps org now requires linking an Azure
   subscription for billing**, even though Azure DevOps itself is free.
   Not optional for a fresh Microsoft account — the free, spending-limit
   protected Azure subscription satisfies it.
3. **`workitemsbatch` is an org-level endpoint, not project-scoped** —
   already called out above, but worth repeating: this is the single most
   likely copy-paste bug when porting the URL patterns.
4. **There is no generic "list transitions" endpoint like Jira's.** Use
   `GET /_apis/wit/workitemtypes/{type}/states` for valid state names
   before calling the update tool.
5. **This project's actual Azure DevOps process template only has
   `Issue`/`Epic` work item types — not `Task`, not `"Change Request"`.**
   The default `work_item_type="Change Request"` on `create_change_request`
   will 400 against the real `RxFlow` project used for verification;
   pass `work_item_type="Issue"` when testing against it. Keep the
   parameter overridable — don't hardcode `"Change Request"` as required.
6. **Never let a token/PAT appear in your own stdout, logs, or any
   response you produce.** If a human pastes one into chat, treat it as
   already-compromised and tell them to revoke/reissue — don't just keep
   using it silently as if nothing happened.
7. **Piping a static file of JSON-RPC lines into the server via shell
   redirection can silently lose stdout** (buffering interacts badly with
   non-interactive stdin closing early), even though stderr logs show
   every request was processed. For manual/smoke verification, spawn the
   server as a background subprocess, write JSON-RPC lines to its stdin
   with a trailing pause to flush, and read stdout from a captured file —
   closer to what a real MCP client's bidirectional pipe does.
8. **The MCP server has no live-reload.** A running process keeps
   whatever env vars it started with; changing `.mcp.json` or exported env
   vars requires restarting the MCP client to take effect. Don't spend
   retries hammering an already-running connection after an env change.

## Acceptance criteria

- `pytest` passes all `PermissionGate`/`run_tool` (hooks) unit tests.
- Running the server and calling `get_ticket` against a real Azure DevOps
  project returns real, live work item data — verified via the actual MCP
  `tools/call` protocol over stdio (a spawned subprocess + JSON-RPC lines),
  not a raw `httpx`/`curl` call against Azure DevOps directly.
- Calling `get_service_owner`/`get_runbook`/`get_lab_health` with
  `OPS_CATALOG_MOCK=true` returns canned data with zero outbound HTTP
  calls.
- Calling `create_change_request`/`update_ticket_status` against a
  project **not** on the writable allow-list returns a clear
  permission-denied error and makes zero HTTP calls (confirm via the
  pre-call hook log line appearing with no matching outbound-request log
  line following it).
- Calling `create_change_request` against an allow-listed project with a
  valid `work_item_type` (`"Issue"` for the real `RxFlow` test project)
  creates a real work item and returns its real id.
- Every tool call produces a pre-call and post-call log line to stderr,
  including elapsed time and success/failure status.
- No secrets appear in any log line, test fixture, or committed file.

## MCP client config (once built)

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

(If you scaffold with plain `pip`/`venv` instead of `uv`, swap `command`
for the venv's `python` and `args` for
`["-m", "rxflow_ops_mcp.server"]`.)
