"""Otari hosted-gateway client.

Live mode calls the documented OpenAI-compatible API at
https://api.otari.ai/api/v1 (or the EU host). When no workspace token is
present, or OTARI_MODE=mock, a clearly labeled mock implements the same
request/response shapes so the demo can run offline.

The workspace token is read from OTARI_API_KEY and is never logged, printed,
or written to the audit log.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import httpx

DEFAULT_BASE = "https://api.otari.ai/api/v1"
DEFAULT_ANALYST = "deepseek/deepseek-v4-pro-0813"
DEFAULT_VERIFIER = "mistral/mistral-large-4"
DEFAULT_ROUTE = "tripwire-analyst"
DEFAULT_GUARDRAIL = "prompt-injection"

# Prefixes that look like a workspace token. Used only to redact, never to print.
_KEY_PREFIXES = ("otk_", "tk-", "sk-")


def redact(value: str | None) -> str:
    if not value:
        return ""
    if any(value.startswith(p) for p in _KEY_PREFIXES) or len(value) > 16:
        return f"{value[:4]}…({len(value)} chars)"
    return "§redacted"


def line_sum(lines: list[dict]) -> float:
    total = 0.0
    for line in lines or []:
        if "ext" in line and line["ext"] is not None:
            total += float(line["ext"])
        else:
            total += float(line.get("qty", 0)) * float(line.get("unit", 0))
    return round(total, 2)


@dataclass
class BudgetSnapshot:
    agent_id: str
    limit_usd: float
    spent_usd: float
    remaining_usd: float
    exhausted: bool
    mock: bool
    source: str
    detail: str = ""


@dataclass
class OtariResult:
    ok: bool
    content: str = ""
    model_requested: str = ""
    model_used: str = ""
    fallback: bool = False
    usage: dict = field(default_factory=dict)
    cost_usd: float | None = None
    tool_events: list[dict] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    status_code: int = 200
    error_type: str | None = None
    error_detail: str = ""
    mock: bool = False
    headers: dict = field(default_factory=dict)
    parsed: dict = field(default_factory=dict)

    def to_public_dict(self) -> dict:
        return {
            "ok": self.ok,
            "content": self.content,
            "model_requested": self.model_requested,
            "model_used": self.model_used,
            "fallback": self.fallback,
            "usage": self.usage,
            "cost_usd": self.cost_usd,
            "tool_events": self.tool_events,
            "features": self.features,
            "status_code": self.status_code,
            "error_type": self.error_type,
            "error_detail": self.error_detail,
            "mock": self.mock,
        }


def load_settings() -> dict:
    mode = (os.environ.get("OTARI_MODE") or "auto").strip().lower()
    key = (os.environ.get("OTARI_API_KEY") or "").strip()
    key_west = (os.environ.get("OTARI_API_KEY_WEST") or "").strip()
    if mode == "live":
        resolved = "live"
    elif mode == "mock":
        resolved = "mock"
    else:
        resolved = "live" if key else "mock"
    return {
        "mode": resolved,
        "requested_mode": mode,
        "has_key": bool(key),
        "has_key_west": bool(key_west),
        "base_url": (os.environ.get("OTARI_BASE_URL") or DEFAULT_BASE).rstrip("/"),
        "model_analyst": os.environ.get("OTARI_MODEL_ANALYST") or DEFAULT_ANALYST,
        "model_verifier": os.environ.get("OTARI_MODEL_VERIFIER") or DEFAULT_VERIFIER,
        "model_route": os.environ.get("OTARI_MODEL_ROUTE") or DEFAULT_ROUTE,
        "guardrail_profile": os.environ.get("OTARI_GUARDRAIL_PROFILE") or DEFAULT_GUARDRAIL,
    }


class OtariError(Exception):
    def __init__(self, result: OtariResult):
        self.result = result
        super().__init__(result.error_detail or result.error_type or "otari_error")


class OtariClient:
    def __init__(self, settings: dict | None = None, http: httpx.Client | None = None):
        self.settings = settings or load_settings()
        self.mode = self.settings["mode"]
        self.base_url = self.settings["base_url"]
        self._http = http
        self._owns_http = False
        # Keys stay on the instance and are never included in logs or results.
        self._keys = {
            "default": (os.environ.get("OTARI_API_KEY") or "").strip(),
            "ap-agent-west": (os.environ.get("OTARI_API_KEY_WEST") or os.environ.get("OTARI_API_KEY") or "").strip(),
            "ap-agent-east": (os.environ.get("OTARI_API_KEY") or "").strip(),
        }

    def close(self) -> None:
        if self._owns_http and self._http is not None:
            self._http.close()
            self._http = None

    def _client(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(timeout=45.0)
            self._owns_http = True
        return self._http

    def _key_for(self, agent_id: str | None) -> str:
        if agent_id and self._keys.get(agent_id):
            return self._keys[agent_id]
        return self._keys.get("default") or ""

    def tools_payload(self) -> list[dict]:
        return [
            {"type": "otari_web_search"},
            {"type": "otari_web_fetch"},
            {"type": "otari_code_execution"},
        ]

    def guardrails_payload(self) -> list[dict]:
        return [{"profile": self.settings["guardrail_profile"], "mode": "block"}]

    def mcp_declaration(self) -> list[dict]:
        # Declaration matches Otari's request field (`mcp_servers`). The local
        # demo runs the same tools in-process; a hosted account still has to
        # register a reachable MCP server in the Otari dashboard.
        return [
            {
                "name": "tripwire-books",
                "tools": ["list_vendors", "get_vendor", "list_open_bills"],
            }
        ]

    def budget(self, agent_id: str) -> BudgetSnapshot:
        if self.mode == "mock":
            return self._mock_budget(agent_id)
        return self._live_budget(agent_id)

    def chat(
        self,
        *,
        model: str,
        messages: list[dict],
        agent_id: str,
        tools: list[dict] | None = None,
        guardrails: list[dict] | None = None,
        mcp_servers: list[dict] | None = None,
        max_tokens: int = 512,
        scenario_id: str | None = None,
        invoice: dict | None = None,
        use_tools: bool = False,
    ) -> OtariResult:
        if self.mode == "mock":
            return self._mock_chat(
                model=model,
                messages=messages,
                agent_id=agent_id,
                tools=tools or [],
                guardrails=guardrails or [],
                scenario_id=scenario_id,
                invoice=invoice or {},
                use_tools=use_tools,
            )
        return self._live_chat(
            model=model,
            messages=messages,
            agent_id=agent_id,
            tools=tools,
            guardrails=guardrails,
            mcp_servers=mcp_servers,
            max_tokens=max_tokens,
        )

    def code_execute(self, code: str, agent_id: str, lines: list[dict] | None = None) -> OtariResult:
        if self.mode == "mock":
            # The mock still computes the line total in-process and labels it.
            computed = line_sum(lines or [])
            return OtariResult(
                ok=True,
                content=json.dumps({"line_total": computed}),
                model_requested="",
                model_used="",
                tool_events=[{"tool": "otari_code_execution", "result": {"line_total": computed}}],
                features=["code_execution"],
                mock=True,
                parsed={"line_total": computed},
            )
        key = self._key_for(agent_id)
        try:
            resp = self._client().post(
                f"{self.base_url}/code/execute",
                headers=self._headers(key),
                json={"code": code, "container": "auto"},
            )
        except httpx.HTTPError as exc:
            return OtariResult(
                ok=False,
                status_code=0,
                error_type="otari_unreachable",
                error_detail=type(exc).__name__,
                features=["code_execution"],
                mock=False,
            )
        return self._parse_code_response(resp)

    # --- live ---

    def _headers(self, key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Otari-Web-Search": "otari",
        }

    def _live_budget(self, agent_id: str) -> BudgetSnapshot:
        key = self._key_for(agent_id)
        if not key:
            return BudgetSnapshot(
                agent_id=agent_id,
                limit_usd=0,
                spent_usd=0,
                remaining_usd=0,
                exhausted=True,
                mock=False,
                source="missing_key",
                detail="No workspace token for this agent.",
            )
        try:
            resp = self._client().get(f"{self.base_url}/key/budget", headers=self._headers(key))
        except httpx.HTTPError as exc:
            return BudgetSnapshot(
                agent_id=agent_id,
                limit_usd=0,
                spent_usd=0,
                remaining_usd=0,
                exhausted=False,
                mock=False,
                source="unreachable",
                detail=type(exc).__name__,
            )
        if resp.status_code >= 400:
            return BudgetSnapshot(
                agent_id=agent_id,
                limit_usd=0,
                spent_usd=0,
                remaining_usd=0,
                exhausted=False,
                mock=False,
                source=f"http_{resp.status_code}",
                detail="Budget endpoint was not readable; Tripwire will still fail closed on a budget refusal from chat.",
            )
        data = _safe_json(resp)
        limit = float(data.get("max_budget") or data.get("limit") or data.get("limit_usd") or 0)
        spent = float(data.get("spend") or data.get("spent") or data.get("spent_usd") or 0)
        remaining = float(data.get("remaining") or data.get("remaining_usd") or (limit - spent if limit else 0))
        exhausted = bool(data.get("exhausted")) or (limit > 0 and remaining <= 0)
        return BudgetSnapshot(
            agent_id=agent_id,
            limit_usd=limit,
            spent_usd=spent,
            remaining_usd=remaining,
            exhausted=exhausted,
            mock=False,
            source="key/budget",
        )

    def _live_chat(
        self,
        *,
        model: str,
        messages: list[dict],
        agent_id: str,
        tools: list[dict] | None,
        guardrails: list[dict] | None,
        mcp_servers: list[dict] | None,
        max_tokens: int,
    ) -> OtariResult:
        key = self._key_for(agent_id)
        if not key:
            return OtariResult(
                ok=False,
                model_requested=model,
                status_code=0,
                error_type="missing_key",
                error_detail="OTARI_API_KEY is not set.",
                mock=False,
            )
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "user": agent_id,
        }
        if tools:
            body["tools"] = tools
        if guardrails:
            body["guardrails"] = guardrails
        if mcp_servers:
            body["mcp_servers"] = mcp_servers
        try:
            resp = self._client().post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(key),
                json=body,
            )
        except httpx.HTTPError as exc:
            return OtariResult(
                ok=False,
                model_requested=model,
                status_code=0,
                error_type="otari_unreachable",
                error_detail=type(exc).__name__,
                mock=False,
            )
        return self._parse_chat_response(resp, model)

    def _parse_chat_response(self, resp: httpx.Response, model: str) -> OtariResult:
        headers = {k: v for k, v in resp.headers.items() if k.lower().startswith("otari-") or k.lower() in {"x-request-id"}}
        error_type, error_detail = _classify_error(resp)
        data = _safe_json(resp)
        content = ""
        usage = data.get("usage") or {}
        if resp.status_code < 400:
            choices = data.get("choices") or []
            if choices:
                message = choices[0].get("message") or {}
                content = message.get("content") or ""
                if isinstance(content, list):
                    content = "".join(
                        part.get("text", "") if isinstance(part, dict) else str(part) for part in content
                    )
        parsed = _extract_json(content)
        features = []
        if "tools" in (data.get("usage") or {}) or "otari_web_search" in json.dumps(data):
            features.append("web_search")
        model_used = headers.get("Otari-Model") or headers.get("otari-model") or data.get("model") or model
        fallback = str(headers.get("Otari-Fallback") or headers.get("otari-fallback") or "").lower() == "true"
        if fallback:
            features.append("routing_fallback")
        result = OtariResult(
            ok=resp.status_code < 400 and error_type is None,
            content=content if isinstance(content, str) else json.dumps(content),
            model_requested=model,
            model_used=str(model_used),
            fallback=fallback,
            usage=usage if isinstance(usage, dict) else {},
            status_code=resp.status_code,
            error_type=error_type,
            error_detail=error_detail,
            mock=False,
            headers=headers,
            parsed=parsed,
            features=features,
        )
        return result

    def _parse_code_response(self, resp: httpx.Response) -> OtariResult:
        data = _safe_json(resp)
        error_type, error_detail = _classify_error(resp)
        stdout = data.get("stdout") or data.get("output") or data.get("content") or json.dumps(data)
        return OtariResult(
            ok=resp.status_code < 400 and error_type is None,
            content=stdout if isinstance(stdout, str) else json.dumps(stdout),
            tool_events=[{"tool": "otari_code_execution", "result": data}],
            features=["code_execution"],
            status_code=resp.status_code,
            error_type=error_type,
            error_detail=error_detail,
            mock=False,
            parsed=data if isinstance(data, dict) else {},
        )

    # --- mock ---

    def _mock_budget(self, agent_id: str) -> BudgetSnapshot:
        if agent_id == "ap-agent-west":
            return BudgetSnapshot(
                agent_id=agent_id,
                limit_usd=2.0,
                spent_usd=2.0,
                remaining_usd=0.0,
                exhausted=True,
                mock=True,
                source="mock",
                detail="MOCK: this agent's key budget is exhausted.",
            )
        return BudgetSnapshot(
            agent_id=agent_id,
            limit_usd=5.0,
            spent_usd=1.12,
            remaining_usd=3.88,
            exhausted=False,
            mock=True,
            source="mock",
        )

    def _mock_chat(
        self,
        *,
        model: str,
        messages: list[dict],
        agent_id: str,
        tools: list[dict],
        guardrails: list[dict],
        scenario_id: str | None,
        invoice: dict,
        use_tools: bool,
    ) -> OtariResult:
        blob = " ".join(_message_text(m) for m in messages)
        memo = str(invoice.get("memo") or "")
        if _looks_like_injection(memo) or _looks_like_injection(blob):
            if guardrails:
                return OtariResult(
                    ok=False,
                    model_requested=model,
                    status_code=403,
                    error_type="guardrail_violation",
                    error_detail="MOCK: mandated prompt-injection guardrail blocked the request before a provider was called.",
                    features=["guardrails"],
                    mock=True,
                )
        if agent_id == "ap-agent-west":
            return OtariResult(
                ok=False,
                model_requested=model,
                status_code=429,
                error_type="budget_exhausted",
                error_detail="MOCK: per-user key budget is exhausted.",
                features=["per_user_budgets", "budgets"],
                mock=True,
            )

        fallback = bool(invoice.get("use_route")) or model == self.settings["model_route"]
        model_used = "deepseek/deepseek-v4-flash-mock" if fallback else model
        features = ["budgets", "per_user_budgets"]
        if guardrails:
            features.append("guardrails")
        if fallback:
            features.append("routing_fallback")

        tool_events: list[dict] = []
        if use_tools or any(t.get("type", "").startswith("otari_") for t in tools):
            vendor_name = invoice.get("payee_name") or invoice.get("payee_id") or "vendor"
            tool_events.append(
                {
                    "tool": "otari_web_search",
                    "query": f"{vendor_name} company profile",
                    "result": {
                        "hits": [
                            {
                                "title": f"{vendor_name} — sample directory listing",
                                "url": f"https://example.com/{invoice.get('payee_id') or 'vendor'}",
                                "snippet": f"MOCK search hit for {vendor_name} in wholesale distribution. Not a live web result.",
                            }
                        ]
                    },
                }
            )
            features.append("web_search")
            tool_events.append(
                {
                    "tool": "otari_web_fetch",
                    "url": f"https://example.com/{invoice.get('payee_id') or 'vendor'}",
                    "result": {"status": 200, "note": "MOCK fetch of a sample vendor page."},
                }
            )
            features.append("web_fetch")
            computed = line_sum(invoice.get("lines") or [])
            tool_events.append(
                {"tool": "otari_code_execution", "result": {"line_total": computed, "note": "MOCK in-process total."}}
            )
            features.append("code_execution")
            features.append("mcp")

        recommendation = "allow"
        reasons = ["totals_match"] if abs(line_sum(invoice.get("lines") or []) - float(invoice.get("amount") or 0)) <= 0.01 else ["line_total_mismatch"]
        if "line_total_mismatch" in reasons:
            recommendation = "hold"
        if "verifier" in model or "mistral" in model:
            # Verifier never loosens; it may add a caution on holds already decided upstream.
            parsed = {
                "role": "verifier",
                "recommendation": recommendation,
                "reasons": reasons,
                "notes": "MOCK verifier: tighten-only review of the analyst packet.",
            }
        else:
            parsed = {
                "role": "analyst",
                "recommendation": recommendation,
                "reasons": reasons,
                "line_total": line_sum(invoice.get("lines") or []),
                "search_used": "otari_web_search" in features or "web_search" in features,
            }
        content = json.dumps(parsed)
        return OtariResult(
            ok=True,
            content=content,
            model_requested=model,
            model_used=model_used,
            fallback=fallback,
            usage={"prompt_tokens": 180, "completion_tokens": 90, "total_tokens": 270},
            cost_usd=0.002 if not fallback else 0.0015,
            tool_events=tool_events,
            features=sorted(set(features)),
            mock=True,
            parsed=parsed,
        )


def _message_text(message: dict) -> str:
    content = message.get("content") or ""
    if isinstance(content, list):
        return " ".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
    return str(content)


def _looks_like_injection(text: str) -> bool:
    lower = (text or "").lower()
    needles = (
        "ignore your instructions",
        "ignore previous instructions",
        "reveal your system prompt",
        "override the policy",
    )
    return any(n in lower for n in needles)


def _safe_json(resp: httpx.Response) -> dict:
    try:
        data = resp.json()
        return data if isinstance(data, dict) else {"data": data}
    except ValueError:
        return {"raw": (resp.text or "")[:500]}


def _extract_json(content: str) -> dict:
    if not content or not isinstance(content, str):
        return {}
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}


def _classify_error(resp: httpx.Response) -> tuple[str | None, str]:
    if resp.status_code < 400:
        return None, ""
    data = _safe_json(resp)
    err = data.get("error") if isinstance(data.get("error"), dict) else {}
    code = str(err.get("code") or err.get("type") or data.get("code") or "")
    message = str(err.get("message") or data.get("detail") or data.get("message") or resp.text or "")[:400]
    lowered = (code + " " + message).lower()
    if resp.status_code == 403 and ("guardrail" in lowered or code == "guardrail_violation"):
        return "guardrail_violation", message or "Otari guardrail blocked the request."
    if resp.status_code in (402, 429) or "budget" in lowered:
        return "budget_exhausted", message or "Otari budget refused the request."
    if resp.status_code in (401, 403):
        return "auth_error", message or f"HTTP {resp.status_code}"
    return "http_error", message or f"HTTP {resp.status_code}"
