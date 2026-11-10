"""JSON-RPC handlers for the Tripwire books MCP server."""
from __future__ import annotations

import json

from tripwire.books import MCP_TOOLS, Books

PROTOCOL = "2024-11-05"
_books = Books()


def handle(req: dict, books: Books | None = None) -> dict:
    store = books or _books
    mid = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "protocolVersion": PROTOCOL,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "tripwire-books", "version": "0.1.0"},
            },
        }
    if method in {"notifications/initialized", "initialized"}:
        return {}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": MCP_TOOLS}}
    if method == "tools/call":
        name = params.get("name") or ""
        arguments = params.get("arguments") or {}
        result = store.as_tool_result(name, arguments)
        return {
            "jsonrpc": "2.0",
            "id": mid,
            "result": {
                "content": [{"type": "text", "text": json.dumps(result)}],
                "isError": "error" in result,
            },
        }
    return {
        "jsonrpc": "2.0",
        "id": mid,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }
