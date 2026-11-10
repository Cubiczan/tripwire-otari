"""In-process books tools, also exposed as a minimal MCP server.

Otari can attach MCP servers (`mcp_servers` / `mcp_server_ids`) to a chat
request. This module is the local books surface the agent uses in every demo
run. `scripts/mcp_books_server.py` speaks a small JSON-RPC MCP subset over
stdio so the same tools can be registered in the Otari dashboard once a
hosted account is available.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BOOKS = ROOT / "data" / "books.json"

TOLERANCE = 0.01


@dataclass
class Vendor:
    id: str
    name: str
    country: str
    category: str
    website: str
    status: str


@dataclass
class Bill:
    id: str
    vendor_id: str
    amount: float
    currency: str
    memo: str


class Books:
    def __init__(self, path: Path | str | None = None, data: dict | None = None):
        if data is None:
            path = Path(path or DEFAULT_BOOKS)
            data = json.loads(path.read_text())
        self.vendors = [Vendor(**v) for v in data.get("vendors", [])]
        self.open_bills = [Bill(**b) for b in data.get("open_bills", [])]
        self._by_id = {v.id: v for v in self.vendors}

    def get_vendor(self, vendor_id: str) -> Vendor | None:
        return self._by_id.get(vendor_id)

    def list_vendors(self) -> list[Vendor]:
        return list(self.vendors)

    def open_bills_for(self, vendor_id: str) -> list[Bill]:
        return [b for b in self.open_bills if b.vendor_id == vendor_id]

    def matching_open_bill(self, vendor_id: str, amount: float, currency: str) -> Bill | None:
        for bill in self.open_bills_for(vendor_id):
            if bill.currency == currency and abs(bill.amount - amount) <= TOLERANCE:
                return bill
        return None

    def as_tool_result(self, name: str, arguments: dict) -> dict:
        if name == "list_vendors":
            return {
                "vendors": [
                    {"id": v.id, "name": v.name, "country": v.country, "category": v.category}
                    for v in self.vendors
                ]
            }
        if name == "get_vendor":
            vendor = self.get_vendor(str(arguments.get("vendor_id", "")))
            return {"vendor": vendor.__dict__ if vendor else None}
        if name == "list_open_bills":
            vendor_id = str(arguments.get("vendor_id", ""))
            bills = self.open_bills_for(vendor_id)
            return {"bills": [b.__dict__ for b in bills]}
        return {"error": f"unknown_tool:{name}"}


MCP_TOOLS = [
    {
        "name": "list_vendors",
        "description": "List vendors in the company's AP books.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_vendor",
        "description": "Look up one vendor by id.",
        "inputSchema": {
            "type": "object",
            "properties": {"vendor_id": {"type": "string"}},
            "required": ["vendor_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "list_open_bills",
        "description": "List open bills for a vendor.",
        "inputSchema": {
            "type": "object",
            "properties": {"vendor_id": {"type": "string"}},
            "required": ["vendor_id"],
            "additionalProperties": False,
        },
    },
]
