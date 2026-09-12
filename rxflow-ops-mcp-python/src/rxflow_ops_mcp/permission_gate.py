"""Server-side permission gate for mutating Azure DevOps tools.

Checks a project name against a config-driven allow-list *before* any HTTP
call is made. This is only the server-side half of the safety story - the
MCP client asking a human to confirm before invoking a mutating tool is the
other half (see README).
"""
from __future__ import annotations

import os


class PermissionDeniedError(Exception):
    """Raised when a mutating action targets a project that isn't allow-listed."""


class PermissionGate:
    def __init__(self, writable_projects: list[str] | None = None) -> None:
        if writable_projects is None:
            raw = os.environ.get("AZDO_WRITABLE_PROJECTS", "")
            writable_projects = [p.strip() for p in raw.split(",") if p.strip()]
        self._writable_projects = {p.lower() for p in writable_projects}

    def is_writable(self, project: str) -> bool:
        return project.strip().lower() in self._writable_projects

    def check(self, project: str) -> None:
        if not self.is_writable(project):
            raise PermissionDeniedError(
                f"Project '{project}' is not on the writable allow-list. "
                "This mutating action was blocked before any HTTP call was made."
            )
