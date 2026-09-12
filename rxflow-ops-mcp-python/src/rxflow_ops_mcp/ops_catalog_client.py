"""Client for internal ops-catalog service metadata.

No public API spec exists for this backend, so it's built against a
configurable OPS_CATALOG_BASE_URL with a reasonable REST convention:
  GET /services/{id}/owner
  GET /services/{id}/runbook
  GET /labs/{id}/health

OPS_CATALOG_MOCK=true is an explicit opt-in mock mode that returns
canned-but-realistic data with zero HTTP calls. Mock mode is never a
silent fallback - if it's not real and not mocked, it fails loudly.
"""
from __future__ import annotations

import os

import httpx

from rxflow_ops_mcp.models import LabHealth, Runbook, ServiceOwner


class OpsCatalogConfigError(Exception):
    """Raised when a required ops-catalog env var is missing at first use."""


def _mock_enabled() -> bool:
    return os.environ.get("OPS_CATALOG_MOCK", "").strip().lower() in {"1", "true", "yes"}


class OpsCatalogClient:
    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self._base_url = base_url
        self._token = token

    @property
    def base_url(self) -> str:
        if _mock_enabled():
            return ""
        url = self._base_url or os.environ.get("OPS_CATALOG_BASE_URL")
        if not url:
            raise OpsCatalogConfigError(
                "OPS_CATALOG_BASE_URL is not set (and OPS_CATALOG_MOCK is not enabled)"
            )
        return url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        token = self._token or os.environ.get("OPS_CATALOG_TOKEN")
        return {"Authorization": f"Bearer {token}"} if token else {}

    async def get_service_owner(self, service_name: str) -> ServiceOwner:
        if _mock_enabled():
            return ServiceOwner(
                service_name=service_name,
                team=f"{service_name}-platform-team",
                on_call_contact=f"oncall-{service_name}@example.com",
            )
        url = f"{self.base_url}/services/{service_name}/owner"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            return ServiceOwner.model_validate(resp.json())

    async def get_runbook(self, service_name: str) -> Runbook:
        if _mock_enabled():
            return Runbook(
                service_name=service_name,
                title=f"{service_name} Operational Runbook",
                steps=[
                    "Check service health dashboard",
                    "Review recent deployments",
                    "Escalate to on-call if unresolved after 15 minutes",
                ],
                url=f"https://runbooks.example.com/{service_name}",
            )
        url = f"{self.base_url}/services/{service_name}/runbook"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            return Runbook.model_validate(resp.json())

    async def get_lab_health(self, lab_name: str) -> LabHealth:
        if _mock_enabled():
            return LabHealth(
                lab_name=lab_name,
                status="healthy",
                details=f"All checks passing for {lab_name}",
            )
        url = f"{self.base_url}/labs/{lab_name}/health"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers())
            resp.raise_for_status()
            return LabHealth.model_validate(resp.json())
