#!/usr/bin/env python3
"""Write a token-free public JSON dump of the in-memory live demo results.

Used immediately after scripts/demo.py by importing and re-running is NOT
desired. Instead, patch run_all, call demo.main, then dump the stashed gate.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

import scripts.demo as demo  # noqa: E402
import tripwire.agent as agent  # noqa: E402


def _scrub(text: str) -> str:
    text = re.sub(r"otk_[A-Za-z0-9_\-]+", "otk_REDACTED", text)
    text = re.sub(r"tk-[A-Za-z0-9_\-]+", "tk-REDACTED", text)
    text = re.sub(r"Bearer\s+\S+", "Bearer REDACTED", text)
    return text


def main() -> int:
    stash: dict = {}
    real = agent.run_all

    def wrapped(*args, **kwargs):
        gate, results = real(*args, **kwargs)
        stash["gate"] = gate
        stash["results"] = results
        return gate, results

    demo.run_all = wrapped
    code = demo.main()
    gate = stash.get("gate")
    if gate is None:
        raise SystemExit("demo.main() did not stash a gate")
    payload = {
        "results": [r.to_public_dict() for r in gate.results],
        "holds": [h.__dict__ for h in gate.holds.values()],
        "audit_ok": gate.audit.verify()[0],
        "audit_entries": len(gate.audit.entries()),
    }
    text = _scrub(json.dumps(payload, indent=2, default=str))
    if re.search(r"otk_[A-Za-z0-9_\-]{8,}", text) or "Bearer " in text:
        raise SystemExit("dump still looks like it contains a token")
    out = Path(os.environ.get("TRIPWIRE_DUMP_JSON") or ROOT / "video/build/work/results.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text + "\n")
    print(f"Wrote {out}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
