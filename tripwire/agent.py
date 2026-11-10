"""Tripwire agent: every model call goes through Otari; the policy gate decides."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tripwire.audit import AuditLog
from tripwire.books import Books
from tripwire.otari import OtariClient, OtariResult, line_sum, load_settings
from tripwire.policy import Decision, PaymentRequest, Policy, Verdict, evaluate, tighten

ROOT = Path(__file__).resolve().parent.parent
SCENARIOS_PATH = ROOT / "data" / "scenarios.json"

ANALYST_SYSTEM = (
    "Tripwire invoice analyst. Reply with a compact JSON object only: "
    '{"recommendation":"allow|hold|deny","reasons":["..."],"line_total":0,'
    '"notes":"..."}. Keep reasons to short phrases and notes to one sentence. '
    "A matching open bill for the same vendor and amount supports allow; it is "
    "not a duplicate payment. You may tighten, never loosen. Do not invent amounts."
)

VERIFIER_SYSTEM = (
    "Tripwire tighten-only verifier. Reply with a compact JSON object only: "
    '{"recommendation":"allow|hold|deny","reasons":["..."],"notes":"..."}. '
    "Recommend hold or deny only when you can name a concrete books or policy "
    "issue. A matching open bill supports allow. Do not escalate a policy hold "
    "to deny unless the payee country is blocked or the amount is over the hard cap. "
    "If the policy decision is allow and you see no new issue, recommend allow. "
    "You may not loosen a hold or deny."
)


@dataclass
class ActionResult:
    scenario_id: str
    title: str
    agent_id: str
    decision: str
    reasons: list[str]
    expected: str | None
    matched_expected: bool | None
    mock: bool
    otari_mode: str
    features: list[str]
    models: dict
    budget: dict
    books: dict
    analyst: dict
    verifier: dict
    hold_id: str | None = None
    audit_hash: str = ""
    at: str = ""

    def to_public_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "title": self.title,
            "agent_id": self.agent_id,
            "decision": self.decision,
            "reasons": self.reasons,
            "expected": self.expected,
            "matched_expected": self.matched_expected,
            "mock": self.mock,
            "otari_mode": self.otari_mode,
            "features": self.features,
            "models": self.models,
            "budget": self.budget,
            "books": self.books,
            "analyst": self.analyst,
            "verifier": self.verifier,
            "hold_id": self.hold_id,
            "audit_hash": self.audit_hash,
            "at": self.at,
        }


@dataclass
class Hold:
    id: str
    action: dict
    status: str = "open"
    resolved_by: str = ""
    resolved_at: str = ""


class Tripwire:
    def __init__(
        self,
        client: OtariClient | None = None,
        books: Books | None = None,
        audit: AuditLog | None = None,
        policy: Policy | None = None,
        now: datetime | None = None,
    ):
        self.settings = load_settings()
        self.client = client or OtariClient(self.settings)
        self.books = books or Books()
        self.audit = audit or AuditLog()
        self.policy = policy or Policy()
        self._now = now
        self.history: list[PaymentRequest] = []
        self.results: list[ActionResult] = []
        self.holds: dict[str, Hold] = {}
        self._hold_seq = 0

    def now(self) -> datetime:
        return self._now or datetime.now(timezone.utc).astimezone()

    def run_scenario(self, scenario: dict, at: datetime | None = None) -> ActionResult:
        at = at or self.now()
        agent_id = scenario["agent_id"]
        features: list[str] = []
        reasons: list[str] = []
        decision = Decision.ALLOW

        def flag(d: Decision, reason: str) -> None:
            nonlocal decision
            decision = tighten(decision, d)
            if reason not in reasons:
                reasons.append(reason)

        budget = self.client.budget(agent_id)
        features.extend(["budgets", "per_user_budgets"])
        budget_public = {
            "agent_id": budget.agent_id,
            "limit_usd": budget.limit_usd,
            "spent_usd": budget.spent_usd,
            "remaining_usd": budget.remaining_usd,
            "exhausted": budget.exhausted,
            "mock": budget.mock,
            "source": budget.source,
        }

        if budget.exhausted:
            flag(Decision.DENY, "otari_budget_exhausted")
            result = self._finish(
                scenario,
                decision,
                reasons or ["otari_budget_exhausted"],
                features,
                budget_public,
                books_info={"vendor": None, "open_bill": None},
                analyst={},
                verifier={},
                at=at,
            )
            return result

        vendor = self.books.get_vendor(scenario["payee_id"])
        open_bill = self.books.matching_open_bill(
            scenario["payee_id"], float(scenario["amount"]), scenario.get("currency", "USD")
        )
        features.append("mcp")
        books_info = {
            "vendor": vendor.__dict__ if vendor else None,
            "open_bill": open_bill.__dict__ if open_bill else None,
            "open_bill_count": len(self.books.open_bills_for(scenario["payee_id"])),
        }
        if vendor is None:
            flag(Decision.HOLD, "unknown_vendor")
        elif open_bill is None:
            if self.books.open_bills_for(scenario["payee_id"]):
                flag(Decision.HOLD, "bill_amount_mismatch")
            else:
                flag(Decision.HOLD, "no_open_bill")

        computed = line_sum(scenario.get("lines") or [])
        if abs(computed - float(scenario["amount"])) > 0.01:
            flag(Decision.HOLD, "line_total_mismatch")

        req = PaymentRequest(
            agent_id=agent_id,
            kind=scenario.get("kind", "transfer"),
            amount=float(scenario["amount"]),
            currency=scenario.get("currency", "USD"),
            payee_id=scenario["payee_id"],
            payee_country=scenario.get("payee_country", ""),
            at=at,
            memo=scenario.get("memo", ""),
        )
        verdict: Verdict = evaluate(req, self.policy, self.history)
        for reason in verdict.reasons:
            if reason != "ok":
                flag(verdict.decision, reason)
            elif verdict.decision != Decision.ALLOW:
                flag(verdict.decision, reason)

        # Spend control on live: skip model calls when the deterministic gate
        # has already denied, and skip Otari chat when a scored feature is not
        # actually configured (guardrails).
        if self.client.mode == "live" and decision == Decision.DENY:
            return self._finish(
                scenario, decision, reasons, features, budget_public, books_info, {}, {}, at, req,
            )
        if (
            self.client.mode == "live"
            and scenario.get("id") == "guardrail_block"
            and not self.client.guardrails_configured()
        ):
            flag(Decision.HOLD, "otari_guardrails_not_configured")
            return self._finish(
                scenario, decision, reasons, features, budget_public, books_info, {}, {}, at, req,
            )
        if (
            self.client.mode == "live"
            and scenario.get("id") == "budget_exhausted"
            and not budget.exhausted
        ):
            flag(Decision.HOLD, "otari_west_budget_not_configured")
            return self._finish(
                scenario, decision, reasons, features, budget_public, books_info, {}, {}, at, req,
            )

        if self.client.mode == "live" and scenario.get("id") == "allow_routine":
            code = (
                "lines = " + json.dumps(scenario.get("lines") or []) + "\n"
                "total = 0.0\n"
                "for line in lines:\n"
                "    total += float(line['ext']) if line.get('ext') is not None else float(line['qty']) * float(line['unit'])\n"
                "print(round(total, 2))\n"
            )
            executed = self.client.code_execute(code, agent_id, lines=scenario.get("lines") or [])
            features.extend(executed.features or ["code_execution"])
            books_info = dict(books_info)
            books_info["otari_code_execution"] = {
                "ok": executed.ok,
                "content": (executed.content or "")[:200],
                "mock": executed.mock,
                "error_type": executed.error_type,
            }
            if executed.ok:
                try:
                    remote_total = float((executed.content or "").strip().splitlines()[-1])
                    if abs(remote_total - float(scenario["amount"])) > 0.01:
                        flag(Decision.HOLD, "line_total_mismatch")
                except ValueError:
                    pass

        use_route = bool(scenario.get("use_route"))
        analyst_model = self.settings["model_route"] if use_route else self.settings["model_analyst"]
        analyst_messages = [
            {"role": "system", "content": ANALYST_SYSTEM},
            {"role": "user", "content": _analyst_prompt(scenario, books_info, computed)},
        ]
        live = self.client.mode == "live"
        analyst = self.client.chat(
            model=analyst_model,
            messages=analyst_messages,
            agent_id=agent_id,
            tools=[] if live else self.client.tools_payload(),
            guardrails=self.client.guardrails_payload(),
            mcp_servers=self.client.mcp_declaration(),
            max_tokens=int(self.settings.get("max_tokens") or 256),
            fallback_model=self.settings["model_analyst"] if use_route else None,
            scenario_id=scenario.get("id"),
            invoice=scenario,
            use_tools=not live,
        )
        features.extend(analyst.features)
        if analyst.fallback:
            features.append("routing_fallback")
        features.append("open_weight_analyst")
        features.append("multiple_models")

        if not analyst.ok:
            if analyst.error_type == "guardrail_violation":
                flag(Decision.DENY, "otari_guardrail_violation")
            elif analyst.error_type == "budget_exhausted":
                flag(Decision.DENY, "otari_budget_exhausted")
            else:
                flag(Decision.HOLD, f"otari_analyst_{analyst.error_type or 'error'}")
            verifier = OtariResult(ok=False, error_type="skipped", error_detail="Analyst did not succeed.")
            return self._finish(
                scenario,
                decision,
                reasons,
                features,
                budget_public,
                books_info,
                analyst.to_public_dict(),
                verifier.to_public_dict(),
                at,
                req,
            )

        rec = (analyst.parsed or {}).get("recommendation")
        if rec in {"hold", "deny"}:
            flag(Decision(rec), f"analyst_{rec}")
        elif rec not in {"allow", None, ""}:
            flag(Decision.HOLD, "analyst_unparseable")

        if analyst.tool_events:
            for ev in analyst.tool_events:
                if ev.get("tool") == "otari_code_execution":
                    result_obj = ev.get("result") or {}
                    if "line_total" in result_obj and abs(float(result_obj["line_total"]) - float(scenario["amount"])) > 0.01:
                        flag(Decision.HOLD, "line_total_mismatch")

        verifier_model = self.settings["model_verifier"]
        verifier_messages = [
            {"role": "system", "content": VERIFIER_SYSTEM},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "policy_decision": decision.value,
                        "policy_reasons": reasons,
                        "analyst": analyst.parsed or {"content": analyst.content},
                    },
                    default=str,
                ),
            },
        ]
        verifier = self.client.chat(
            model=verifier_model,
            messages=verifier_messages,
            agent_id=agent_id,
            guardrails=self.client.guardrails_payload(),
            max_tokens=int(self.settings.get("max_tokens") or 256),
            scenario_id=scenario.get("id"),
            invoice=scenario,
            use_tools=False,
        )
        features.extend(verifier.features)
        features.append("open_weight_verifier")
        if not verifier.ok:
            if verifier.error_type == "guardrail_violation":
                flag(Decision.DENY, "otari_guardrail_violation")
            elif verifier.error_type == "budget_exhausted":
                flag(Decision.DENY, "otari_budget_exhausted")
            else:
                flag(Decision.HOLD, "otari_verifier_error")
        else:
            rec = (verifier.parsed or {}).get("recommendation")
            if rec in {"hold", "deny"}:
                flag(Decision(rec), f"verifier_{rec}")
            # allow is ignored: tighten-only

        return self._finish(
            scenario,
            decision,
            reasons or ["ok"],
            features,
            budget_public,
            books_info,
            analyst.to_public_dict(),
            verifier.to_public_dict(),
            at,
            req,
        )

    def _finish(
        self,
        scenario: dict,
        decision: Decision,
        reasons: list[str],
        features: list[str],
        budget_public: dict,
        books_info: dict,
        analyst: dict,
        verifier: dict,
        at: datetime,
        req: PaymentRequest | None = None,
    ) -> ActionResult:
        hold_id = None
        if decision == Decision.HOLD:
            self._hold_seq += 1
            hold_id = f"hold-{self._hold_seq:04d}"
            self.holds[hold_id] = Hold(id=hold_id, action={"scenario_id": scenario.get("id"), "amount": scenario.get("amount")}, status="open")
        if req is not None and decision != Decision.DENY:
            # Denied requests do not join velocity history as executed payments.
            if decision == Decision.ALLOW:
                self.history.append(req)

        expected = scenario.get("expected")
        result = ActionResult(
            scenario_id=str(scenario.get("id") or ""),
            title=str(scenario.get("title") or scenario.get("id") or ""),
            agent_id=scenario["agent_id"],
            decision=decision.value,
            reasons=reasons or ["ok"],
            expected=expected,
            matched_expected=(decision.value == expected) if expected else None,
            mock=self.client.mode == "mock",
            otari_mode=self.client.mode,
            features=sorted(set(features)),
            models={
                "analyst": (analyst or {}).get("model_used") or self.settings["model_analyst"],
                "analyst_requested": (analyst or {}).get("model_requested"),
                "verifier": (verifier or {}).get("model_used") or self.settings["model_verifier"],
                "fallback": bool((analyst or {}).get("fallback")),
            },
            budget=budget_public,
            books=books_info,
            analyst=analyst,
            verifier=verifier,
            hold_id=hold_id,
            at=at.isoformat(),
        )
        record = result.to_public_dict()
        # Never persist tokens. Strip any accidental secret-looking fields.
        record.pop("api_key", None)
        result.audit_hash = self.audit.append({"kind": "decision", **record})
        self.results.append(result)
        return result

    def approve(self, hold_id: str, actor: str = "cfo") -> dict:
        hold = self.holds.get(hold_id)
        if not hold:
            return {"ok": False, "error": "unknown_hold"}
        if hold.status != "open":
            return {"ok": False, "error": "already_resolved", "status": hold.status}
        hold.status = "approved"
        hold.resolved_by = actor
        hold.resolved_at = self.now().isoformat()
        self.audit.append({"kind": "hold_resolved", "hold_id": hold_id, "status": "approved", "actor": actor})
        return {"ok": True, "hold": hold.__dict__, "note": "Recorded intent only. No payment rail is connected."}

    def deny_hold(self, hold_id: str, actor: str = "cfo") -> dict:
        hold = self.holds.get(hold_id)
        if not hold:
            return {"ok": False, "error": "unknown_hold"}
        if hold.status != "open":
            return {"ok": False, "error": "already_resolved", "status": hold.status}
        hold.status = "denied"
        hold.resolved_by = actor
        hold.resolved_at = self.now().isoformat()
        self.audit.append({"kind": "hold_resolved", "hold_id": hold_id, "status": "denied", "actor": actor})
        return {"ok": True, "hold": hold.__dict__}


def load_pack(path: Path | str | None = None) -> tuple[Policy, list[dict]]:
    raw = json.loads(Path(path or SCENARIOS_PATH).read_text())
    cfg = raw.get("policy") or {}
    policy = Policy(
        max_single=float(cfg.get("max_single", 5000)),
        hold_above=float(cfg.get("hold_above", 1000)),
        allowed_payees=set(cfg.get("allowed_payees") or []),
        allowed_countries=set(cfg.get("allowed_countries") or ["US", "GB", "AU", "SG", "HK"]),
    )
    return policy, list(raw.get("scenarios") or [])


def run_all(path: Path | str | None = None, client: OtariClient | None = None, now: datetime | None = None) -> tuple[Tripwire, list[ActionResult]]:
    policy, scenarios = load_pack(path)
    gate = Tripwire(client=client, policy=policy, now=now)
    results = [gate.run_scenario(s) for s in scenarios]
    return gate, results


def _analyst_prompt(scenario: dict, books_info: dict, computed: float) -> str:
    payload = {
        "invoice": {
            "id": scenario.get("id"),
            "payee_id": scenario.get("payee_id"),
            "payee_name": scenario.get("payee_name"),
            "payee_country": scenario.get("payee_country"),
            "amount": scenario.get("amount"),
            "currency": scenario.get("currency"),
            "memo": scenario.get("memo"),
            "lines": scenario.get("lines"),
        },
        "computed_line_total": computed,
        "books": books_info,
        "instructions": "Recommend allow, hold, or deny from the invoice and books. JSON only.",
    }
    return json.dumps(payload, default=str)
