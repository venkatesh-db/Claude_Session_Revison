"""Shared async wrapper every tool routes through.

Every tool call - read or write - logs a pre-call line, runs the permission
check first when mutating, runs the actual work, and logs a post-call line
with elapsed time and success/failure, win or lose.
"""
from __future__ import annotations

import logging
import time
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger("rxflow_ops_mcp.tool_call")

T = TypeVar("T")


async def run_tool(
    tool_name: str,
    *,
    is_mutating: bool,
    work: Callable[[], Awaitable[T]],
    permission_check: Callable[[], None] | None = None,
) -> T:
    logger.info("tool_call.start name=%s mutating=%s", tool_name, is_mutating)
    start = time.monotonic()
    try:
        if is_mutating and permission_check is not None:
            permission_check()
        result = await work()
    except Exception as exc:
        elapsed = time.monotonic() - start
        logger.info(
            "tool_call.end name=%s mutating=%s status=failure elapsed_s=%.3f error=%s",
            tool_name, is_mutating, elapsed, exc,
        )
        raise
    else:
        elapsed = time.monotonic() - start
        logger.info(
            "tool_call.end name=%s mutating=%s status=success elapsed_s=%.3f",
            tool_name, is_mutating, elapsed,
        )
        return result
