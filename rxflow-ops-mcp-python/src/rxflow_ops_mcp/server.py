"""Entrypoint: configures logging to stderr, builds the FastMCP server,
registers tools, and runs the stdio transport.

stdout is reserved for the MCP protocol channel - never print() here, and
logging must be configured to write exclusively to stderr.
"""
from __future__ import annotations

import logging
import sys

from mcp.server.fastmcp import FastMCP

from rxflow_ops_mcp.azure_devops_client import AzureDevOpsClient
from rxflow_ops_mcp.ops_catalog_client import OpsCatalogClient
from rxflow_ops_mcp.permission_gate import PermissionGate
from rxflow_ops_mcp.tools import register_tools


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def build_server() -> FastMCP:
    mcp = FastMCP("rxflow-ops-mcp")
    azdo = AzureDevOpsClient()
    ops = OpsCatalogClient()
    gate = PermissionGate()
    register_tools(mcp, azdo, ops, gate)
    return mcp


def main() -> None:
    configure_logging()
    mcp = build_server()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
