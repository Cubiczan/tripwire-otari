#!/usr/bin/env python3
"""Run the sample-data demo and print a labeled feature table."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tripwire.agent import run_all  # noqa: E402
from tripwire.otari import load_settings  # noqa: E402

OUT = ROOT / "docs" / "demo_run.txt"

FEATURE_LABELS = [
    ("open_weight_analyst", "Open-weight analyst model"),
    ("open_weight_verifier", "Open-weight verifier model"),
    ("multiple_models", "Multiple models, distinct roles"),
    ("routing_fallback", "Model routing / fallback"),
    ("mcp", "MCP books tools"),
    ("web_search", "Web search"),
    ("web_fetch", "Web fetch"),
    ("code_execution", "Code execution"),
    ("budgets", "Budgets and spending limits"),
    ("per_user_budgets", "Per-user budgets"),
    ("guardrails", "Guardrails"),
]


def main() -> int:
    settings = load_settings()
    gate, results = run_all()
    ok, bad = gate.audit.verify()
    lines: list[str] = []

    def p(msg: str = "") -> None:
        print(msg)
        lines.append(msg)

    p("Tripwire for Otari — sample-data demo")
    p(f"Otari mode: {settings['mode'].upper()}")
    if settings["mode"] != "live":
        p("This run is MOCK. It did not call hosted otari.ai.")
        p("Set OTARI_API_KEY (otk_…) and OTARI_MODE=live to use the hosted gateway.")
    else:
        p(f"Hosted endpoint: {settings['base_url']}")
        p("Workspace token is set and is not printed.")
    p(f"Analyst model:  {settings['model_analyst']}")
    p(f"Verifier model: {settings['model_verifier']}")
    p(f"Routing policy: {settings['model_route']}")
    p("")
    header = f"{'Scenario':<24} {'Decision':<8} {'Expect':<8} {'Match':<6} Reasons"
    p(header)
    p("-" * len(header))
    all_match = True
    used: set[str] = set()
    for r in results:
        match = "yes" if r.matched_expected else ("n/a" if r.matched_expected is None else "NO")
        if r.matched_expected is False:
            all_match = False
        p(f"{r.scenario_id:<24} {r.decision:<8} {(r.expected or '-'):<8} {match:<6} {', '.join(r.reasons)}")
        used.update(r.features)
    p("")
    p(f"Audit chain: {'OK' if ok else f'BROKEN at {bad}'} ({len(gate.audit.entries())} events)")
    p("")
    p("Otari features exercised in this run:")
    for key, label in FEATURE_LABELS:
        mark = "yes" if key in used else "no"
        p(f"  [{mark:>3}] {label}")
    p("")
    p("Honesty notes:")
    p("- No payment rail is connected. ALLOW records intent; it does not move money.")
    p("- Sample vendors, bills, and search hits are invented for the demo.")
    if settings["mode"] != "live":
        p("- MOCK mode implements the documented Otari request shapes locally.")
        p("  Prize eligibility requires a live Otari.ai run and a public repo.")
    p("")
    p(f"Finished at {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")
    print(f"\nWrote {OUT}")
    return 0 if ok and all_match else 1


if __name__ == "__main__":
    raise SystemExit(main())
