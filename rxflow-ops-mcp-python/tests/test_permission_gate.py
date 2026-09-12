import pytest

from rxflow_ops_mcp.permission_gate import PermissionDeniedError, PermissionGate


def test_allows_allow_listed_project():
    gate = PermissionGate(["RxFlow", "OtherProject"])
    assert gate.is_writable("RxFlow")
    gate.check("RxFlow")


def test_is_case_insensitive():
    gate = PermissionGate(["RxFlow"])
    assert gate.is_writable("rxflow")
    assert gate.is_writable("RXFLOW")
    gate.check("rxflow")


def test_blocks_non_listed_project():
    gate = PermissionGate(["RxFlow"])
    assert not gate.is_writable("SomeOtherProject")
    with pytest.raises(PermissionDeniedError):
        gate.check("SomeOtherProject")


def test_blocks_everything_when_empty():
    gate = PermissionGate([])
    assert not gate.is_writable("RxFlow")
    with pytest.raises(PermissionDeniedError):
        gate.check("RxFlow")


def test_reads_allow_list_from_env(monkeypatch):
    monkeypatch.setenv("AZDO_WRITABLE_PROJECTS", "RxFlow, OtherProject")
    gate = PermissionGate()
    assert gate.is_writable("RxFlow")
    assert gate.is_writable("OtherProject")
    assert not gate.is_writable("NotListed")
