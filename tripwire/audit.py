"""Hash-chained tamper-evident audit log (SQLite)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys

GENESIS = "0" * 64


class AuditLog:
    def __init__(self, path: str = ":memory:"):
        self.path = path
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, payload TEXT, prev TEXT, hash TEXT)"
        )
        self.db.commit()

    @staticmethod
    def _h(prev: str, payload: str) -> str:
        return hashlib.sha256((prev + payload).encode()).hexdigest()

    def append(self, record: dict) -> str:
        row = self.db.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
        prev = row[0] if row else GENESIS
        payload = json.dumps(record, sort_keys=True, default=str)
        h = self._h(prev, payload)
        self.db.execute("INSERT INTO audit(payload,prev,hash) VALUES(?,?,?)", (payload, prev, h))
        self.db.commit()
        return h

    def entries(self) -> list[dict]:
        rows = self.db.execute("SELECT id, payload, prev, hash FROM audit ORDER BY id").fetchall()
        out = []
        for i, payload, prev, h in rows:
            item = json.loads(payload)
            item["_id"] = i
            item["_prev"] = prev
            item["_hash"] = h
            out.append(item)
        return out

    def verify(self) -> tuple[bool, int | None]:
        prev = GENESIS
        for i, payload, p, h in self.db.execute("SELECT id,payload,prev,hash FROM audit ORDER BY id"):
            if p != prev or self._h(prev, payload) != h:
                return False, i
            prev = h
        return True, None


if __name__ == "__main__":
    ok, bad = AuditLog(sys.argv[2] if len(sys.argv) > 2 else "tripwire.db").verify()
    print("chain OK" if ok else f"chain BROKEN at row {bad}")
    sys.exit(0 if ok else 1)
