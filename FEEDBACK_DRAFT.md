# Feedback draft (revise in your own words)

The official form accepts a 3–5 minute feedback screen recording, written answers, or both. The recording, if you make one, must be your screen and your voice — no AI.

These answers are based on the live hosted run on 10 Nov 2026 (US region, Default workspace, `docs/demo_run_live.txt`). Rewrite them in your own words before you send them.

## Feedback video, if you record one (3–5 min)

1. Walk through the live dashboard and the Otari Overview: two open-weight models, code execution, app-level fallback, policy allow/hold/deny.
2. What worked well: one OpenAI-compatible endpoint, cheap flash models, code execution actually ran, usage/summary was readable from the workspace key.
3. What didn't work: the `user` field 403, web search/fetch disabled, no guardrails service, routing policies not writable with this key, code execution at $0.01 a call, early JSON truncation at 128 max tokens.
4. What's missing: a first-class action-approval hook, workspace-key APIs to attach budgets and routing policies, and web tools plus guardrails that can be turned on without a second vendor key if possible.

## Written answers (draft after the live run)

### When were you most tempted to skip Otari and call the provider directly? What happened?

The first live chat failed immediately with 403: `'user' field does not match the authenticated API key's user`. Tripwire had been sending the agent id as `user` so per-user budgets could land correctly. On this workspace key that field is not a free-form label; a mismatch is rejected and never reaches a model. I removed `user` unless `OTARI_USER` is set to the key owner, and the next call (Xiaomi MiMo V2.6 Flash, eight max tokens) returned "pong" for a fraction of a cent.

After that, the temptation was weaker. The same base URL reached a second open-weight model (GLM-5.3-Flash) and `POST /api/v1/code/execute` (`print(1+1)` → `2`) without a provider SDK. What I could not do with this workspace token was turn on the rest of the rubric: web search and fetch are `web_access_disabled`, a request-level `prompt-injection` guardrail returns 502 because no guardrails service is configured, and routing-policy routes want a master key. Those stayed in the dashboard instead of being bypassed with a direct provider call.

### What did you end up building yourself that Otari should've done for you?

Tripwire still owns the action policy (amount caps, payee and country allowlists, velocity, bill match) and the hash-chained ALLOW / HOLD / DENY log. Otari governs model access, traces, and code execution, but it does not decide whether a proposed payment may proceed. A first-class "tool or action approval" hook, with the decision next to the trace, would have removed some of that second layer.

I also had to build an app-level fallback: the demo names a `tripwire-analyst` routing policy, that name is not created yet, and the client retries with `xiaomi/mimo-v2.6-flash`. Creating that policy is a dashboard (or master-key) step, not something the workspace token can do through `/routing/policies`.

Two smaller frictions: early completions with `max_tokens=128` truncated the analyst's JSON, so I raised the cap to 256 and asked for `response_format=json_object`. And the first analyst pass treated a *matching* open bill as a duplicate-payment risk until the prompt said a matching bill supports allow.

### If the rules hadn't required Otari, would you have continued using Otari? Why or why not?

Yes, for this use case, with a caveat. One OpenAI-compatible endpoint, two cheap open-weight models, usage I can read back, and a working code sandbox are enough reason to keep the traffic on Otari instead of a single provider SDK. The caveat is operational: web tools, guardrails, routing policies, and key ceilings all needed dashboard work that this key could not finish, and code execution at $0.01 per call dominated spend even when chat was nearly nothing. I would keep using it if those controls can be finished in the dashboard without more ceremony than a direct provider call.

## Facts to keep in any rewrite

- Models: `xiaomi/mimo-v2.6-flash` (analyst), `z-ai/glm-5.3-flash` (verifier)
- Live demo: 10 Nov 2026, 9:43 AM America/New_York, `docs/demo_run_live.txt`
- Cumulative key usage after that run: $0.041994 of the $2.00 welcome credit (mostly four code-execution calls)
- Do not claim live web search, fetch, mandated guardrails, or an Otari routing policy until those are enabled and rerun
