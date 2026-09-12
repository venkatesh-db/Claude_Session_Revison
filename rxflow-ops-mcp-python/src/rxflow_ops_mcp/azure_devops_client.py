"""Real Azure DevOps REST API v7.1 client.

Auth: PAT over Basic auth with an empty username -
Authorization: Basic base64(":" + pat).

Notes ported from the verified .NET build of this server:
- The `workitemsbatch` endpoint is org-level, not project-scoped. Calling
  it as `/{project}/_apis/wit/workitemsbatch` 404s.
- There is no generic "list transitions" endpoint; valid states for a work
  item type come from `/_apis/wit/workitemtypes/{type}/states`.
"""
from __future__ import annotations

import base64
import os

import httpx

API_VERSION = "7.1"


class AzureDevOpsConfigError(Exception):
    """Raised when a required Azure DevOps env var is missing at first use."""


class AzureDevOpsClient:
    def __init__(
        self,
        organization: str | None = None,
        project: str | None = None,
        pat: str | None = None,
    ) -> None:
        self._organization = organization
        self._project = project
        self._pat = pat

    @property
    def organization(self) -> str:
        org = self._organization or os.environ.get("AZDO_ORG")
        if not org:
            raise AzureDevOpsConfigError("AZDO_ORG is not set")
        return org

    @property
    def default_project(self) -> str:
        project = self._project or os.environ.get("AZDO_PROJECT")
        if not project:
            raise AzureDevOpsConfigError("AZDO_PROJECT is not set")
        return project

    @property
    def _pat_value(self) -> str:
        pat = self._pat or os.environ.get("AZDO_PAT")
        if not pat:
            raise AzureDevOpsConfigError("AZDO_PAT is not set")
        return pat

    def _headers(self, content_type: str = "application/json") -> dict[str, str]:
        token = base64.b64encode(f":{self._pat_value}".encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": content_type,
        }

    def _base_url(self) -> str:
        return f"https://dev.azure.com/{self.organization}"

    async def get_work_item(self, work_item_id: int) -> dict:
        url = f"{self._base_url()}/{self.default_project}/_apis/wit/workitems/{work_item_id}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url, params={"api-version": API_VERSION}, headers=self._headers()
            )
            resp.raise_for_status()
            return resp.json()

    async def search_work_items(self, wiql: str, max_results: int = 25) -> list[dict]:
        wiql_url = f"{self._base_url()}/{self.default_project}/_apis/wit/wiql"
        async with httpx.AsyncClient() as client:
            wiql_resp = await client.post(
                wiql_url,
                params={"api-version": API_VERSION},
                headers=self._headers(),
                json={"query": wiql},
            )
            wiql_resp.raise_for_status()
            work_items = wiql_resp.json().get("workItems", [])[:max_results]
            ids = [w["id"] for w in work_items]
            if not ids:
                return []

            # Org-level endpoint - NOT project-scoped.
            batch_url = f"{self._base_url()}/_apis/wit/workitemsbatch"
            batch_resp = await client.post(
                batch_url,
                params={"api-version": API_VERSION},
                headers=self._headers(),
                json={"ids": ids},
            )
            batch_resp.raise_for_status()
            return batch_resp.json().get("value", [])

    async def list_valid_states(self, work_item_type: str) -> list[str]:
        url = (
            f"{self._base_url()}/{self.default_project}/_apis/wit/workitemtypes/"
            f"{work_item_type}/states"
        )
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url, params={"api-version": API_VERSION}, headers=self._headers()
            )
            resp.raise_for_status()
            return [s["name"] for s in resp.json().get("value", [])]

    async def create_work_item(
        self, project: str, title: str, description: str, work_item_type: str
    ) -> dict:
        url = f"{self._base_url()}/{project}/_apis/wit/workitems/${work_item_type}"
        patch = [
            {"op": "add", "path": "/fields/System.Title", "value": title},
            {"op": "add", "path": "/fields/System.Description", "value": description},
        ]
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                params={"api-version": API_VERSION},
                headers=self._headers(content_type="application/json-patch+json"),
                json=patch,
            )
            resp.raise_for_status()
            return resp.json()

    async def update_work_item_status(
        self, work_item_id: int, new_state: str, comment: str | None = None
    ) -> dict:
        url = f"{self._base_url()}/{self.default_project}/_apis/wit/workitems/{work_item_id}"
        patch = [{"op": "add", "path": "/fields/System.State", "value": new_state}]
        if comment:
            patch.append({"op": "add", "path": "/fields/System.History", "value": comment})
        async with httpx.AsyncClient() as client:
            resp = await client.patch(
                url,
                params={"api-version": API_VERSION},
                headers=self._headers(content_type="application/json-patch+json"),
                json=patch,
            )
            resp.raise_for_status()
            return resp.json()
