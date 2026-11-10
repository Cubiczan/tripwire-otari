#!/usr/bin/env python3
"""Minimal stdio MCP server for Tripwire books tools.

Register this command in the Otari dashboard as an MCP server once a hosted
account and a reachable runtime are available. It speaks a small JSON-RPC
subset: initialize, tools/list, tools/call, ping.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tripwire.mcp_server import handle  # noqa: E402


def main() -> int:
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            req = json.loads(raw)
        except json.JSONDecodeError:
            continue
        reply = handle(req)
        if reply:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
