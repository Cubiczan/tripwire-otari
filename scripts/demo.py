#!/usr/bin/env python3
"""Run the sample-data demo and print a labeled feature table."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from tripwire.agent import run_all  # noqa: E402
from tripwire.otari import load_settings  # noqa: E402

OUT_MOCK = ROOT / "docs" / "demo_run.txt"
OUT_LIVE = ROOT / "docs" / "demo_run_live.txt"

FEATURE_LABELS = [
    ("open_weight_analyst", "Open-weight analyst model"),
    ("open_weight_verifier", "Open-weight verifier model"),
    ("multiple_models", "Multiple models, distinct roles"),
    ("routing_fallback", "Model routing / fallback"),
    ("app_fallback", "App-level fallback (no Otari routing policy configured)"),
    ("mcp", "MCP books tools (in-process)"),
    ("web_search", "Web search"),
    ("web_fetch", "Web fetch"),
    ("code_execution", "Code execution"),
    ("budgets", "Budgets and spending limits"),
    ("per_user_budgets", "Per-user budgets"),
    ("guardrails", "Guardrails"),
]

# Live gaps that need dashboard setup; do not fail the demo script on these.
LIVE_SOFT = {
    "budget_exhausted": "No second key budget is attached, so Otari cannot refuse this agent for spend.",
    "guardrail_block": "No Otari guardrails service is configured on this workspace.",
}


def _scrub(text: str) -> str:
    # Only strip credentials, not ordinary long strings.
    text = re.sub(r"otk_[A-Za-z0-9_\-]+", "otk_REDACTED", text)
    text = re.sub(r"tk-[A-Za-z0-9_\-]+", "tk-REDACTED", text)
    text = re.sub(r"Bearer\s+\S+", "Bearer REDACTED", text)
    return text


def _usage_line(summary: dict) -> str:
    if not summary or summary.get("mock"):
        return "n/a (mock)"
    return (
        f"cost=${summary.get('cost')}  "
        f"requests={summary.get('request_count')}  "
        f"errors={summary.get('error_count')}  "
        f"tokens={summary.get('total_tokens')} "
        f"(prompt={summary.get('prompt_tokens')}, completion={summary.get('completion_tokens')})"
    )


def main() -> int:
    settings = load_settings()
    gate, results = run_all()
    ok, bad = gate.audit.verify()
    usage_after = gate.client.usage_summary() if settings["mode"] == "live" else {"mock": True}
    lines: list[str] = []

    def p(msg: str = "") -> None:
        print(msg)
        lines.append(msg)

    p("Tripwire for Otari — sample-data demo")
    p(f"Otari mode: {settings['mode'].upper()}")
    if settings["mode"] != "live":
        p("This run is MOCK. It did not call hosted otari.ai.")
        p("Set OTARI_API_KEY in .env and run: OTARI_MODE=live python scripts/demo.py")
    else:
        p(f"Hosted endpoint: {settings['base_url']}")
        p("Workspace token is set and is not printed.")
        p(f"Usage after this run: {_usage_line(usage_after)}")
    p(f"Analyst model:  {settings['model_analyst']}")
    p(f"Verifier model: {settings['model_verifier']}")
    p(f"Routing policy: {settings['model_route']}")
    p("")
    header = f"{'Scenario':<24} {'Decision':<8} {'Expect':<8} {'Match':<6} Reasons"
    p(header)
    p("-" * len(header))
    hard_fail = False
    used: set[str] = set()
    for r in results:
        soft = settings["mode"] == "live" and r.scenario_id in LIVE_SOFT and r.matched_expected is False
        if r.matched_expected is False and not soft:
            hard_fail = True
        if soft:
            match = "soft"
        elif r.matched_expected is True:
            match = "yes"
        elif r.matched_expected is None:
            match = "n/a"
        else:
            match = "NO"
        p(f"{r.scenario_id:<24} {r.decision:<8} {(r.expected or '-'):<8} {match:<6} {', '.join(r.reasons)}")
        if soft:
            p(f"  note: {LIVE_SOFT[r.scenario_id]}")
        models = r.models or {}
        rec_a = (r.analyst or {}).get("parsed") or {}
        rec_v = (r.verifier or {}).get("parsed") or {}
        if r.analyst or r.verifier:
            p(
                "  models: analyst={a} verifier={v} fallback={f} "
                "analyst_rec={ar} verifier_rec={vr}".format(
                    a=models.get("analyst"),
                    v=models.get("verifier"),
                    f=models.get("fallback"),
                    ar=rec_a.get("recommendation") or (r.analyst or {}).get("error_type") or "-",
                    vr=rec_v.get("recommendation") or (r.verifier or {}).get("error_type") or "-",
                )
            )
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
    else:
        p("- Live calls used the hosted gateway at api.otari.ai. Costs come from /key/usage/summary.")
        p("- Web search and web fetch are workspace-disabled on this account.")
        p("- Otari guardrails are not configured (no guardrails service / profiles).")
        p("- Routing policies cannot be created with a workspace key; fallback_routing uses an app-level retry.")
        p("- Per-user / second-key budgets are not attached; budget_exhausted cannot be refused by Otari yet.")
        p("- MCP books tools ran in-process. No Otari MCP server URL is registered.")
        p("- Code execution is billed by Otari and was used once on allow_routine to limit spend.")
    if usage_after and not usage_after.get("mock"):
        p("")
        p("Usage by model (from Otari, redacted):")
        p(_scrub(json.dumps(usage_after.get("by_model") or [], indent=2)))
        p("Usage by tool:")
        p(_scrub(json.dumps(usage_after.get("by_tool") or [], indent=2)))
    p("")
    p(f"Finished at {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}")

    text = _scrub("\n".join(lines) + "\n")
    OUT_MOCK.parent.mkdir(parents=True, exist_ok=True)
    target = OUT_LIVE if settings["mode"] == "live" else OUT_MOCK
    target.write_text(text)
    print(f"\nWrote {target}")
    return 0 if ok and not hard_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
