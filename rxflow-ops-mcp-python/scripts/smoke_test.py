"""Manual/smoke verification: spawn the server as a subprocess and speak
JSON-RPC over its stdio, the way a real MCP client would. Do NOT pipe a
static file into stdin via shell redirection - that can silently lose
stdout output.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time


def send(proc: subprocess.Popen, msg: dict) -> None:
    data = json.dumps(msg) + "\n"
    proc.stdin.write(data.encode())
    proc.stdin.flush()


def read_line(proc: subprocess.Popen, timeout: float = 5.0) -> dict | None:
    start = time.time()
    while time.time() - start < timeout:
        line = proc.stdout.readline()
        if line:
            return json.loads(line)
    return None


def main() -> None:
    env = dict(os.environ)
    env["OPS_CATALOG_MOCK"] = "true"
    env["AZDO_WRITABLE_PROJECTS"] = "RxFlow"
    env.setdefault("AZDO_ORG", "example-org")
    env.setdefault("AZDO_PROJECT", "RxFlow")
    env.setdefault("AZDO_PAT", "fake-pat-for-smoke-test")

    proc = subprocess.Popen(
        [sys.executable, "-m", "rxflow_ops_mcp.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    )

    try:
        send(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "smoke-test", "version": "0.1"},
            },
        })
        print("initialize ->", read_line(proc))
        send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        print("tools/list ->", read_line(proc))

        send(proc, {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "get_service_owner", "arguments": {"service_name": "billing"}},
        })
        print("get_service_owner ->", read_line(proc))

        send(proc, {
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {
                "name": "create_change_request",
                "arguments": {
                    "project": "NotAllowedProject",
                    "title": "t",
                    "description": "d",
                    "work_item_type": "Issue",
                },
            },
        })
        print("create_change_request (denied) ->", read_line(proc))

        time.sleep(0.3)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        stderr = proc.stderr.read().decode(errors="replace")
        print("\n--- stderr (hook log lines) ---")
        print(stderr)


if __name__ == "__main__":
    main()
