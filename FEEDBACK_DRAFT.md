# Feedback draft (revise in your own words)

The official form accepts a 3–5 minute feedback screen recording, written answers, or both. The recording, if you make one, must be your screen and your voice — no AI.

These answers are based on the live hosted runs on 10 Nov 2026 (US region, Default workspace, latest log `docs/demo_run_live.txt` at 10:01 AM America/New_York). Rewrite them in your own words before you send them.

## Feedback video, if you record one (3–5 min)

1. Walk through the live dashboard and the Otari Overview: two open-weight models, the `tripwire-analyst` Fallback policy, one code-execution call, one OFAC web fetch, the $1.00 key budget read back from `/key/budget`, and policy allow/hold/deny.
2. What worked well: one OpenAI-compatible endpoint, cheap flash models, a named routing policy that actually served the primary model, code execution and fetch both ran, usage and the key budget were readable from the workspace key.
3. What didn't work: the `user` field 403; `GET /tools` saying web search is available while `POST /search` returns 400 until a search provider is added; every catalog guardrail needing an outside vendor key; routing policies and search-tool setup not writable with a workspace key; code execution and fetch at $0.01 a call; early JSON truncation at 128 max tokens.
4. What's missing: a first-class action-approval hook; workspace-key APIs to attach budgets, routing policies, and search tools; a built-in guardrail that does not require a second vendor; and a cheaper or clearly metered fetch/search path so a demo does not spend most of its budget on two tool calls.

## Written answers (draft after the live run)

### When were you most tempted to skip Otari and call the provider directly? What happened?

The first live chat failed immediately with 403: `'user' field does not match the authenticated API key's user`. Tripwire had been sending the agent id as `user` so per-user budgets could land correctly. On this workspace key that field is not a free-form label; a mismatch is rejected and never reaches a model. I removed `user` unless `OTARI_USER` is set to the key owner, and the next call (Xiaomi MiMo V2.6 Flash, eight max tokens) returned "pong" for a fraction of a cent.

After that, the temptation was weaker. The same base URL reached a second open-weight model (GLM-5.3-Flash), `POST /api/v1/code/execute`, a Fallback policy named `tripwire-analyst`, and `POST /api/v1/fetch` of the official OFAC page, plus a readable `/key/budget`. What still could not be finished with this workspace token, and was not worth leaving Otari for, was the rest of the rubric: `POST /search` still returns 400 until a search tool/provider is added (even though `GET /tools` lists search as available), and every catalog guardrail needs an outside vendor key, so Tripwire's own policy gate stayed the guardrail layer.

### What did you end up building yourself that Otari should've done for you?

Tripwire still owns the action policy (amount caps, payee and country allowlists, velocity, bill match) and the hash-chained ALLOW / HOLD / DENY log. Otari governs model access, traces, routing, fetch, and code execution, but it does not decide whether a proposed payment may proceed. A first-class "tool or action approval" hook, with the decision next to the trace, would have removed some of that second layer.

I also kept a client-side retry behind the `tripwire-analyst` policy. Once the policy existed in the dashboard, Otari served the primary model and the retry was not needed — but creating that policy, attaching the $1.00 key ceiling, and turning on web access were all dashboard (or master-key) steps. The workspace token cannot create `/routing/policies` or `/search-tools`.

Two smaller frictions from the first live pass remain worth reporting: early completions with `max_tokens=128` truncated the analyst's JSON (Xiaomi uses reasoning tokens), so I raised the cap to 256 and asked for `response_format=json_object`. And the first analyst pass treated a *matching* open bill as a duplicate-payment risk until the prompt said a matching bill supports allow.

The search/fetch split is the sharpest new one. Workspace web access made `POST /fetch` work immediately, at the same $0.01 price as code execution. Search still needed a separate provider on Tools & Guardrails. `GET /tools` reporting `otari_web_search` as available was misleading until that provider existed.

### If the rules hadn't required Otari, would you have continued using Otari? Why or why not?

Yes, for this use case, with a caveat. One OpenAI-compatible endpoint, two cheap open-weight models, a working Fallback policy, a code sandbox, a bounded fetch, and usage plus a key ceiling I can read back are enough reason to keep the traffic on Otari instead of a single provider SDK. The caveat is operational: search still needs a provider, catalog guardrails all need a second vendor, routing policies and search-tool setup are not writable with the workspace key, and the $0.01-per-call tools dominate spend even when chat is nearly nothing. I would keep using it if those controls can be finished without more ceremony than a direct provider call, and if a built-in guardrail existed that did not require an outside vendor key.

## Facts to keep in any rewrite

- Models: `xiaomi/mimo-v2.6-flash` (analyst, via `tripwire-analyst`), `z-ai/glm-5.3-flash` (verifier and policy backup)
- Routing: policy used live; primary served (`Otari-Fallback: false`); client retry kept as a backstop
- Web fetch: one live call to `https://ofac.treasury.gov/` on `deny_country` (North Korea program corroborated). Web search is not configured.
- Guardrails: Otari catalog skipped (outside vendor key required). Tripwire's policy gate is the guardrail layer.
- Budget: `tripwire-otari` $1.00 monthly `api_token` limit, read from `/key/budget`. After the 10:01 AM America/New_York run: used $0.050864, remaining $0.949136, resets 2026-12-01T00:00:00Z (2026-11-30 19:00 EST). No second/west key.
- Live demo: 10 Nov 2026, 10:01 AM America/New_York, `docs/demo_run_live.txt`. Tests: 14 passed. Cumulative `/key/usage/summary` cost $0.092858.
- Do not claim live web search, mandated Otari catalog guardrails, a fired `Otari-Fallback` header, or a per-user budget refusal unless those are enabled and rerun.
