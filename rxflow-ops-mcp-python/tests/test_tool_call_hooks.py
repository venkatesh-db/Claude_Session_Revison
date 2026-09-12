import pytest

from rxflow_ops_mcp.permission_gate import PermissionDeniedError
from rxflow_ops_mcp.tool_call_hooks import run_tool


async def test_returns_work_result_for_reads():
    async def work():
        return {"id": 1}

    result = await run_tool("get_ticket", is_mutating=False, work=work)
    assert result == {"id": 1}


async def test_skips_permission_check_for_reads():
    checked = False

    def permission_check():
        nonlocal checked
        checked = True

    async def work():
        return "ok"

    await run_tool(
        "get_ticket", is_mutating=False, work=work, permission_check=permission_check
    )
    assert checked is False


async def test_runs_permission_check_before_work_for_mutations():
    order: list[str] = []

    def permission_check():
        order.append("check")

    async def work():
        order.append("work")
        return "ok"

    result = await run_tool(
        "create_change_request", is_mutating=True, work=work, permission_check=permission_check
    )
    assert order == ["check", "work"]
    assert result == "ok"


async def test_permission_check_failure_prevents_work():
    work_called = False

    def permission_check():
        raise PermissionDeniedError("nope")

    async def work():
        nonlocal work_called
        work_called = True
        return "ok"

    with pytest.raises(PermissionDeniedError):
        await run_tool(
            "create_change_request", is_mutating=True, work=work, permission_check=permission_check
        )
    assert work_called is False


async def test_propagates_exceptions_from_work():
    async def work():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        await run_tool("get_ticket", is_mutating=False, work=work)
