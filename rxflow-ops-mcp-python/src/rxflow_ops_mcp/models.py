"""Pydantic models for ops-catalog and Azure DevOps response shapes."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ServiceOwner(BaseModel):
    service_name: str
    team: str
    on_call_contact: str


class Runbook(BaseModel):
    service_name: str
    title: str
    steps: list[str]
    url: str | None = None


class LabHealth(BaseModel):
    lab_name: str
    status: str
    details: str | None = None


class WorkItem(BaseModel):
    id: int
    url: str | None = None
    fields: dict[str, Any] = {}
