"""The 8 MCP tools, each routing through the shared run_tool hook wrapper."""
from __future__ import annotations

from functools import partial
from typing import Any

from mcp.server.fastmcp import FastMCP

from rxflow_ops_mcp.azure_devops_client import AzureDevOpsClient
from rxflow_ops_mcp.ops_catalog_client import OpsCatalogClient
from rxflow_ops_mcp.permission_gate import PermissionGate
from rxflow_ops_mcp.tool_call_hooks import run_tool


def register_tools(
    mcp: FastMCP,
    azdo: AzureDevOpsClient,
    ops: OpsCatalogClient,
    gate: PermissionGate,
) -> None:
    @mcp.tool()
    async def get_ticket(work_item_id: int) -> dict[str, Any]:
        """Fetch one Azure Boards work item by numeric id."""
        return await run_tool(
            "get_ticket",
            is_mutating=False,
            work=partial(azdo.get_work_item, work_item_id),
        )

    @mcp.tool()
    async def search_incidents(wiql: str, max_results: int = 25) -> list[dict[str, Any]]:
        """Run a WIQL query against Azure Boards and return hydrated work items."""
        return await run_tool(
            "search_incidents",
            is_mutating=False,
            work=partial(azdo.search_work_items, wiql, max_results),
        )

    @mcp.tool()
    async def list_valid_states(work_item_type: str) -> list[str]:
        """List the valid System.State values for a work item type."""
        return await run_tool(
            "list_valid_states",
            is_mutating=False,
            work=partial(azdo.list_valid_states, work_item_type),
        )

    @mcp.tool()
    async def create_change_request(
        project: str,
        title: str,
        description: str,
        work_item_type: str = "Change Request",
    ) -> dict[str, Any]:
        """Create a work item in the given project. Requires the project to be
        on the writable allow-list; blocked before any HTTP call otherwise."""
        return await run_tool(
            "create_change_request",
            is_mutating=True,
            permission_check=partial(gate.check, project),
            work=partial(azdo.create_work_item, project, title, description, work_item_type),
        )

    @mcp.tool()
    async def update_ticket_status(
        work_item_id: int, new_state: str, comment: str | None = None
    ) -> dict[str, Any]:
        """Set System.State on a work item via JSON Patch, optionally appending
        a comment. Requires the configured default project to be on the
        writable allow-list; blocked before any HTTP call otherwise."""
        return await run_tool(
            "update_ticket_status",
            is_mutating=True,
            permission_check=partial(gate.check, azdo.default_project),
            work=partial(azdo.update_work_item_status, work_item_id, new_state, comment),
        )

    @mcp.tool()
    async def get_service_owner(service_name: str) -> dict[str, Any]:
        """Get the owning team and on-call contact for a service."""
        result = await run_tool(
            "get_service_owner",
            is_mutating=False,
            work=partial(ops.get_service_owner, service_name),
        )
        return result.model_dump()

    @mcp.tool()
    async def get_runbook(service_name: str) -> dict[str, Any]:
        """Get the operational runbook for a service."""
        result = await run_tool(
            "get_runbook",
            is_mutating=False,
            work=partial(ops.get_runbook, service_name),
        )
        return result.model_dump()

    @mcp.tool()
    async def get_lab_health(lab_name: str) -> dict[str, Any]:
        """Get the current health status of a lab environment."""
        result = await run_tool(
            "get_lab_health",
            is_mutating=False,
            work=partial(ops.get_lab_health, lab_name),
        )
        return result.model_dump()
