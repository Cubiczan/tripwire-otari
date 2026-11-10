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
DEFAULT_ANALYST = "xiaomi/mimo-v2.6-flash"
DEFAULT_VERIFIER = "z-ai/glm-5.3-flash"
DEFAULT_ROUTE = "tripwire-analyst"
DEFAULT_GUARDRAIL = "prompt-injection"
DEFAULT_MAX_TOKENS = 256

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
    resets_at: str = ""
    limits: list = field(default_factory=list)

    def to_public_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "limit_usd": self.limit_usd,
            "spent_usd": self.spent_usd,
            "remaining_usd": self.remaining_usd,
            "exhausted": self.exhausted,
            "mock": self.mock,
            "source": self.source,
            "detail": self.detail,
            "resets_at": self.resets_at,
            "limits": list(self.limits or []),
        }


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
            "parsed": self.parsed,
            "content_preview": (self.content or "")[:400],
        }


def parse_budget_payload(data: dict, *, agent_id: str, mock: bool, source: str) -> BudgetSnapshot:
    """Parse GET /key/budget, including the hosted `limits` array."""
    raw_limits = data.get("limits") if isinstance(data.get("limits"), list) else []
    limits: list[dict] = []
    for lim in raw_limits:
        if not isinstance(lim, dict):
            continue
        limits.append(
            {
                "scope": lim.get("scope"),
                "limit_usd": lim.get("limit_usd"),
                "used_usd": lim.get("used_usd"),
                "remaining_usd": lim.get("remaining_usd"),
                "resets_at": lim.get("resets_at"),
            }
        )
    usd = [item for item in limits if item.get("limit_usd") is not None]
    if usd:
        tight = min(usd, key=lambda item: float(item["remaining_usd"] if item.get("remaining_usd") is not None else 0))
        limit = float(tight.get("limit_usd") or 0)
        spent = float(tight.get("used_usd") or 0)
        remaining = float(tight["remaining_usd"] if tight.get("remaining_usd") is not None else max(limit - spent, 0))
        resets_at = str(tight.get("resets_at") or "")
    else:
        limit = float(data.get("max_budget") or data.get("limit") or data.get("limit_usd") or 0)
        spent = float(data.get("spend") or data.get("spent") or data.get("spent_usd") or data.get("used_usd") or 0)
        remaining = float(data.get("remaining") or data.get("remaining_usd") or (limit - spent if limit else 0))
        resets_at = str(data.get("resets_at") or "")
    exhausted = bool(data.get("exhausted")) or (limit > 0 and remaining <= 0)
    return BudgetSnapshot(
        agent_id=agent_id,
        limit_usd=limit,
        spent_usd=spent,
        remaining_usd=remaining,
        exhausted=exhausted,
        mock=mock,
        source=source,
        resets_at=resets_at,
        limits=limits,
    )


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
        "max_tokens": int(os.environ.get("OTARI_MAX_TOKENS") or DEFAULT_MAX_TOKENS),
        # Only send `user` when it matches the key owner; a mismatch is a 403.
        "user_field": (os.environ.get("OTARI_USER") or "").strip(),
        "mcp_server_url": (os.environ.get("OTARI_MCP_SERVER_URL") or "").strip(),
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
            "ap-agent-west": (os.environ.get("OTARI_API_KEY_WEST") or "").strip(),
            "ap-agent-east": (os.environ.get("OTARI_API_KEY") or "").strip(),
        }
        if not self._keys["ap-agent-west"]:
            self._keys["ap-agent-west"] = self._keys["default"]
        self._tools_cache: list[dict] | None = None
        self._guardrails_configured: bool | None = None

    def close(self) -> None:
        if self._owns_http and self._http is not None:
            self._http.close()
            self._http = None

    def _client(self) -> httpx.Client:
        if self._http is None:
            self._http = httpx.Client(timeout=60.0)
            self._owns_http = True
        return self._http

    def _key_for(self, agent_id: str | None) -> str:
        if agent_id and self._keys.get(agent_id):
            return self._keys[agent_id]
        return self._keys.get("default") or ""

    def tools_payload(self) -> list[dict]:
        if self.mode == "mock":
            return [
                {"type": "otari_web_search"},
                {"type": "otari_web_fetch"},
                {"type": "otari_code_execution"},
            ]
        return [{"type": t["id"]} for t in self.list_tools() if t.get("available") and t.get("id")]

    def guardrails_configured(self) -> bool:
        if self.mode == "mock":
            return True
        if self._guardrails_configured is not None:
            return self._guardrails_configured
        try:
            resp = self._client().get(
                f"{self.base_url}/tool-settings/guardrails/profiles",
                headers=self._headers(self._key_for(None)),
            )
            data = _safe_json(resp)
            self._guardrails_configured = bool(data.get("available") and data.get("profiles"))
        except httpx.HTTPError:
            self._guardrails_configured = False
        return self._guardrails_configured

    def guardrails_payload(self) -> list[dict]:
        if self.mode == "live" and not self.guardrails_configured():
            return []
        return [{"profile": self.settings["guardrail_profile"], "mode": "block"}]

    def mcp_declaration(self) -> list[dict]:
        # Mock: declare the in-process books tools. Live: only when a gateway-
        # reachable MCP URL is configured (Otari requires name + url).
        if self.mode == "live":
            url = self.settings.get("mcp_server_url") or ""
            if not url:
                return []
            return [{"name": "tripwire-books", "url": url, "allowed_tools": ["list_vendors", "get_vendor", "list_open_bills"]}]
        return [
            {
                "name": "tripwire-books",
                "tools": ["list_vendors", "get_vendor", "list_open_bills"],
            }
        ]

    def list_tools(self) -> list[dict]:
        if self.mode == "mock":
            return [
                {"id": "otari_web_search", "available": True, "reason": None},
                {"id": "otari_web_fetch", "available": True, "reason": None},
                {"id": "otari_code_execution", "available": True, "reason": None},
            ]
        if self._tools_cache is not None:
            return self._tools_cache
        try:
            resp = self._client().get(f"{self.base_url}/tools", headers=self._headers(self._key_for(None)))
            data = _safe_json(resp)
            items = data.get("data") if isinstance(data, dict) else []
            self._tools_cache = [t for t in items if isinstance(t, dict)]
        except httpx.HTTPError:
            self._tools_cache = []
        return self._tools_cache

    def usage_summary(self) -> dict:
        """Key usage totals. Never includes the token."""
        if self.mode == "mock":
            return {"mock": True, "cost": 0, "request_count": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "error_count": 0, "by_model": [], "by_tool": []}
        try:
            resp = self._client().get(f"{self.base_url}/key/usage/summary", headers=self._headers(self._key_for(None)))
        except httpx.HTTPError as exc:
            return {"ok": False, "error": type(exc).__name__}
        data = _safe_json(resp)
        totals = data.get("totals") or {}
        return {
            "ok": resp.status_code < 400,
            "status_code": resp.status_code,
            "cost": totals.get("cost"),
            "prompt_tokens": totals.get("prompt_tokens"),
            "completion_tokens": totals.get("completion_tokens"),
            "total_tokens": totals.get("total_tokens"),
            "request_count": totals.get("request_count"),
            "error_count": totals.get("error_count"),
            "unpriced_requests": totals.get("unpriced_requests"),
            "by_model": data.get("by_model") or [],
            "by_tool": data.get("by_tool") or [],
        }

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
        max_tokens: int | None = None,
        fallback_model: str | None = None,
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
            max_tokens=max_tokens if max_tokens is not None else int(self.settings.get("max_tokens") or DEFAULT_MAX_TOKENS),
            fallback_model=fallback_model,
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

    def web_fetch(self, url: str, agent_id: str) -> OtariResult:
        if self.mode == "mock":
            return OtariResult(
                ok=True,
                content="MOCK fetch of a sample official page.",
                tool_events=[{"tool": "otari_web_fetch", "url": url, "result": {"note": "MOCK"}}],
                features=["web_fetch"],
                mock=True,
                parsed={"url": url, "mock": True},
            )
        key = self._key_for(agent_id)
        try:
            resp = self._client().post(
                f"{self.base_url}/fetch",
                headers=self._headers(key),
                json={"url": url},
            )
        except httpx.HTTPError as exc:
            return OtariResult(
                ok=False,
                status_code=0,
                error_type="otari_unreachable",
                error_detail=type(exc).__name__,
                features=["web_fetch"],
                mock=False,
            )
        error_type, error_detail = _classify_error(resp)
        data = _safe_json(resp)
        text = str(data.get("text") or data.get("content") or "")
        return OtariResult(
            ok=resp.status_code < 400 and error_type is None,
            content=text,
            tool_events=[{"tool": "otari_web_fetch", "url": data.get("final_url") or url, "fetch_tool": data.get("fetch_tool")}],
            features=["web_fetch"],
            status_code=resp.status_code,
            error_type=error_type,
            error_detail=error_detail,
            mock=False,
            parsed={
                "url": data.get("final_url") or url,
                "fetch_tool": data.get("fetch_tool"),
                "content_type": data.get("content_type"),
                "title": data.get("title"),
            },
        )

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
        return parse_budget_payload(data, agent_id=agent_id, mock=False, source="key/budget")

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
        fallback_model: str | None = None,
    ) -> OtariResult:
        result = self._post_chat(
            model=model,
            messages=messages,
            agent_id=agent_id,
            tools=tools,
            guardrails=guardrails,
            mcp_servers=mcp_servers,
            max_tokens=max_tokens,
        )
        if (
            not result.ok
            and fallback_model
            and fallback_model != model
            and result.error_type in {"http_error", "otari_unreachable", "guardrails_not_configured"}
        ):
            retry = self._post_chat(
                model=fallback_model,
                messages=messages,
                agent_id=agent_id,
                tools=tools,
                guardrails=guardrails,
                mcp_servers=mcp_servers,
                max_tokens=max_tokens,
            )
            retry.fallback = True
            retry.model_requested = model
            if "app_fallback" not in retry.features:
                retry.features.append("app_fallback")
            retry.features.append("routing_fallback")
            return retry
        return result

    def _post_chat(
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
            "response_format": {"type": "json_object"},
        }
        # Only send `user` when explicitly configured to the key's owner.
        user_field = self.settings.get("user_field") or ""
        if user_field:
            body["user"] = user_field
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
        usage_blob = json.dumps(data)
        if "otari_web_search" in usage_blob:
            features.append("web_search")
        if "otari_web_fetch" in usage_blob:
            features.append("web_fetch")
        if "otari_code_execution" in usage_blob or "code_execution" in (usage or {}):
            features.append("code_execution")
        model_used = headers.get("Otari-Model") or headers.get("otari-model") or data.get("model") or model
        fallback = str(headers.get("Otari-Fallback") or headers.get("otari-fallback") or "").lower() == "true"
        if fallback:
            features.append("routing_fallback")
        if resp.status_code < 400 and model and "/" not in model and ":" not in model:
            # Policy names are not provider/model selectors (e.g. tripwire-analyst).
            features.append("routing_policy")
        cost = None
        if isinstance(usage, dict):
            raw_cost = usage.get("cost_usd") if usage.get("cost_usd") is not None else usage.get("estimated_cost")
            try:
                cost = float(raw_cost) if raw_cost is not None else None
            except (TypeError, ValueError):
                cost = None
        result = OtariResult(
            ok=resp.status_code < 400 and error_type is None,
            content=content if isinstance(content, str) else json.dumps(content),
            model_requested=model,
            model_used=str(model_used),
            fallback=fallback,
            usage=usage if isinstance(usage, dict) else {},
            cost_usd=cost,
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
    if "does not match the authenticated API key's user" in message:
        return "user_mismatch", message
    if "no guardrails service is configured" in lowered or "guardrail profile" in lowered and "not" in lowered:
        return "guardrails_not_configured", message or "No Otari guardrails service is configured."
    if "web_access_disabled" in lowered or "web search is not enabled" in lowered or "web access is not enabled" in lowered:
        return "web_access_disabled", message
    if resp.status_code == 403 and ("guardrail" in lowered or code == "guardrail_violation"):
        return "guardrail_violation", message or "Otari guardrail blocked the request."
    if resp.status_code in (402, 429) or "budget" in lowered:
        return "budget_exhausted", message or "Otari budget refused the request."
    if resp.status_code in (401, 403):
        return "auth_error", message or f"HTTP {resp.status_code}"
    return "http_error", message or f"HTTP {resp.status_code}"
