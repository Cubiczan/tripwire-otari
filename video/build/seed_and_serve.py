#!/usr/bin/env python3
"""Load a public results dump into the dashboard and serve it. Does not call Otari."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

# Banner should stay LIVE if a key is present; never run scenarios from this process.
os.environ.setdefault("OTARI_MODE", "live")

from tripwire.agent import ActionResult, Hold, Tripwire, load_pack  # noqa: E402
from tripwire.app import app  # noqa: E402
import tripwire.app as appmod  # noqa: E402


def _scrub(obj):
    text = json.dumps(obj)
    if "otk_" in text or "tk-" in text or "Bearer " in text:
        raise SystemExit("refusing to seed a dump that looks like it contains a token")
    return obj


def load_dump(path: Path) -> None:
    data = _scrub(json.loads(path.read_text()))
    policy, scenarios = load_pack()
    gate = Tripwire(policy=policy)
    results = []
    for raw in data.get("results") or []:
        fields = {k: raw[k] for k in ActionResult.__dataclass_fields__ if k in raw}
        results.append(ActionResult(**fields))
    gate.results = results
    max_seq = 0
    for raw in data.get("holds") or []:
        hold = Hold(
            id=raw["id"],
            action=raw.get("action") or {},
            status=raw.get("status") or "open",
            resolved_by=raw.get("resolved_by") or "",
            resolved_at=raw.get("resolved_at") or "",
        )
        gate.holds[hold.id] = hold
        if hold.id.startswith("hold-"):
            try:
                max_seq = max(max_seq, int(hold.id.split("-")[1]))
            except (IndexError, ValueError):
                pass
    if not gate.holds:
        for r in results:
            if r.hold_id and r.decision == "hold":
                gate.holds[r.hold_id] = Hold(
                    id=r.hold_id,
                    action={"scenario_id": r.scenario_id},
                    status="open",
                )
                try:
                    max_seq = max(max_seq, int(r.hold_id.split("-")[1]))
                except (IndexError, ValueError):
                    pass
    gate._hold_seq = max_seq
    for r in results:
        record = r.to_public_dict()
        record.pop("api_key", None)
        gate.audit.append({"kind": "decision", **record})
    appmod._gate = gate
    appmod._scenarios = scenarios


def main() -> None:
    dump = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "video/build/work/results.json")
    load_dump(dump)
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
