#!/usr/bin/env python3
"""Run the sample-data demo and print a labeled feature table."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

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
    ("routing_policy", "Otari routing policy (tripwire-analyst)"),
    ("routing_fallback", "Otari-Fallback header (backup model served)"),
    ("app_fallback", "App-level fallback (client backstop)"),
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
    "budget_exhausted": "The tripwire-otari key has a $1.00 monthly ceiling that is not exhausted, and no second (west) key budget is attached.",
    "guardrail_block": "Otari catalog guardrails need an outside vendor key. Tripwire's own policy gate is the guardrail layer.",
}

ET = ZoneInfo("America/New_York")


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


def _format_reset(resets_at: str) -> str:
    if not resets_at:
        return ""
    try:
        dt = datetime.fromisoformat(resets_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(ET).strftime("%Y-%m-%d %H:%M %Z")
    except ValueError:
        return resets_at


def _format_budget(snap) -> str:
    if snap is None:
        return "n/a"
    reset_et = _format_reset(snap.resets_at or "")
    reset_bit = ""
    if snap.resets_at:
        reset_bit = f"  resets_at={snap.resets_at}"
        if reset_et:
            reset_bit += f" ({reset_et} America/New_York)"
    return (
        f"limit=${snap.limit_usd:.2f}  used=${snap.spent_usd:.6f}  "
        f"remaining=${snap.remaining_usd:.6f}  exhausted={snap.exhausted}  "
        f"source={snap.source}{reset_bit}"
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
        budget_after = gate.client.budget("ap-agent-east")
        p(f"Key budget (GET /key/budget): {_format_budget(budget_after)}")
        if budget_after.limits:
            p("  limits: " + json.dumps(budget_after.limits))
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
                "  models: analyst={a} requested={req} verifier={v} fallback={f} "
                "analyst_rec={ar} verifier_rec={vr}".format(
                    a=models.get("analyst"),
                    req=models.get("analyst_requested") or "-",
                    v=models.get("verifier"),
                    f=models.get("fallback"),
                    ar=rec_a.get("recommendation") or (r.analyst or {}).get("error_type") or "-",
                    vr=rec_v.get("recommendation") or (r.verifier or {}).get("error_type") or "-",
                )
            )
        fetch = (r.books or {}).get("otari_web_fetch")
        if fetch:
            p(
                "  ofac_fetch: ok={ok} mentions_north_korea={nk} url={url}".format(
                    ok=fetch.get("ok"),
                    nk=fetch.get("mentions_north_korea"),
                    url=fetch.get("url"),
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
        p("- Live calls used the hosted gateway at api.otari.ai. Costs come from /key/usage/summary and /key/budget.")
        p("- Analyst chats used the tripwire-analyst Fallback policy (xiaomi/mimo-v2.6-flash primary, z-ai/glm-5.3-flash backup). The client still retries on the named analyst model if the policy request fails.")
        p("- Web fetch was used once on deny_country against https://ofac.treasury.gov/ to corroborate the North Korea sanctions program. Page content was treated as untrusted evidence and did not change a policy allow to a deny on its own.")
        p("- Direct POST /search still returns 400: no search tool/provider is configured on Tools & Guardrails, even though GET /tools lists otari_web_search as available. This run did not loop the model on search tools.")
        p("- Otari catalog guardrails were skipped: every dashboard option needs an outside vendor key (Lakera, Azure Prompt Shields, Alinia, Patronus, watsonx, Bedrock, or OpenAI Moderation). Tripwire's own policy gate is the guardrail layer.")
        p("- The tripwire-otari key has a $1.00 USD monthly limit (api_token scope). There is no second/west key budget, so budget_exhausted is still a documented soft gap.")
        p("- MCP books tools ran in-process. No Otari MCP server URL is registered.")
        p("- Code execution and web fetch are each billed by Otari; each was used once in this run to limit spend.")
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

    dump = os.environ.get("TRIPWIRE_DUMP_JSON")
    if dump:
        payload = {
            "results": [r.to_public_dict() for r in results],
            "holds": [h.__dict__ for h in gate.holds.values()],
            "audit_ok": ok,
            "audit_entries": len(gate.audit.entries()),
        }
        dump_text = _scrub(json.dumps(payload, indent=2, default=str))
        Path(dump).parent.mkdir(parents=True, exist_ok=True)
        Path(dump).write_text(dump_text + "\n")
        print(f"Wrote {dump}")

    return 0 if ok and not hard_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
