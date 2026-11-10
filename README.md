# Tripwire for Otari

**A guardrail layer that screens and logs every AI-agent action through [Otari](https://otari.ai) before it can spend money or touch live systems.**

Built for the Mozilla Otari Hackathon (Developers Wilding: Online) on DoraHacks. Draft only: nothing in this folder has been published or submitted.

```
agent proposes a payment or write
        │
        ▼
  hosted Otari.ai  ──  open-weight analyst + verifier
        │               routing / fallback
        │               routing policy, web fetch, code execution
        │               MCP books tools (in-process)
        │               key budget read-back
        │               Tripwire policy gate as the guardrail layer
        ▼
  Tripwire policy gate  ──  ALLOW / HOLD / DENY (tighten-only)
        ▼
  hash-chained audit log
        ▼
  ALLOW records intent only (no payment rail is connected)
  HOLD waits for a person
  DENY stops the action
```

This is the Otari edition of [Tripwire](https://github.com/Cubiczan/tripwire). The deterministic policy gate and audit chain are reused. Every model call is supposed to go through hosted Otari.ai, not straight to a provider.

## Status, honestly

A live run against hosted Otari.ai succeeded on 10 Nov 2026, 10:01 AM America/New_York (see [docs/demo_run_live.txt](docs/demo_run_live.txt)). Analyst chats go through the `tripwire-analyst` Fallback policy (primary `xiaomi/mimo-v2.6-flash`, backup `z-ai/glm-5.3-flash`). The verifier is `z-ai/glm-5.3-flash`. The demo also made one official-page web fetch (`https://ofac.treasury.gov/` on the blocked-country invoice) and one code-execution call, and it printed the `tripwire-otari` key's $1.00 monthly budget from `GET /key/budget`. Cumulative usage after that run was **$0.092858**; the monthly ceiling showed **$0.050864 used / $1.00**. Chat tokens were a small fraction of a cent. The $2.00 welcome credit was not close to being used up.

Without `OTARI_API_KEY`, or with `OTARI_MODE=mock`, the app still runs a clearly labeled mock of the same request shapes. The dashboard banner says MOCK MODE in that case.

Not every rubric feature is live. Web search still needs a search tool/provider on Tools & Guardrails (`POST /search` returns 400 even though `GET /tools` lists it). Otari catalog guardrails were skipped because every option needs an outside vendor key; Tripwire's own policy gate is the guardrail layer. There is no second/west key budget and no hosted MCP server. Those gaps are listed in [SUBMISSION.md](SUBMISSION.md).

Prize eligibility requires a **live** run against Otari.ai, a **public** repository, a **hackathon branch**, a link to the **first commit where Otari came in**, and a **3–5 minute participant-narrated screen recording** (no AI video or voice). See [RULES.md](RULES.md), [SUBMISSION.md](SUBMISSION.md), and [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md).

Intended public GitHub owner, when you approve a publish: **Cubiczan**, repo name `tripwire-otari`, branch `devs-wilding`. This folder does not create that repository and does not push.

## What the demo shows

Sample data is a small wholesale / distribution AP desk (packaging, wholesale, freight, fixtures). The vendors and bills are invented.

| Scenario | Decision | Why |
|---|---|---|
| Routine $185 carton invoice | ALLOW | Allowlisted vendor, matching open bill, totals agree |
| $2,400 fixture invoice | HOLD | Over the $1,000 review threshold |
| Payee in a blocked country | DENY | Country policy, corroborated by one OFAC web fetch |
| $12,000 freight prepay | DENY | Over the $5,000 hard cap |
| Invoice total does not match lines | HOLD | Books + Otari code execution |
| Vendor missing from the books | HOLD | MCP books lookup |
| West-coast agent has no Otari budget left | DENY in mock; soft HOLD live | No second/west key is attached; the $1.00 ceiling is on `tripwire-otari` and is not exhausted |
| Prompt-injection memo | DENY in mock; soft HOLD live | Otari catalog guardrails need an outside vendor key; Tripwire's policy gate is the guardrail layer |
| Analyst routing policy | ALLOW | Live calls use `tripwire-analyst`; Otari served the primary model |

A person can approve or deny a HOLD. That records intent only. **No payment rail is connected.**

## Otari features the app is written to use

These map to the official rubric. In MOCK mode they are exercised against the documented interface. After a live key is configured, rerun the demo and confirm the same traces on the Otari Overview.

| Rubric item | How Tripwire uses it |
|---|---|
| Open-weight models (two roles) | Analyst `xiaomi/mimo-v2.6-flash` (screener) and tighten-only verifier `z-ai/glm-5.3-flash`. Selectors confirmed via `GET /api/v1/models`. |
| Model routing and fallbacks | Live analyst chats use the `tripwire-analyst` Fallback policy (Xiaomi primary, GLM-5.3-Flash backup). The client still retries on the named analyst model if the policy request fails. On the latest live run, Otari served the primary (`Otari-Fallback: false`). |
| MCP integrations | Books tools `list_vendors`, `get_vendor`, `list_open_bills` run in-process every run. `scripts/mcp_books_server.py` is a stdio server. Otari itself requires a Streamable-HTTP URL registered under Tools → MCP servers. |
| Web search or web fetch | Live: one `POST /api/v1/fetch` of `https://ofac.treasury.gov/` on `deny_country` (billed at $0.01). Direct search still returns 400 until a search tool/provider is added on Tools & Guardrails. |
| Code execution | Live: `POST /api/v1/code/execute` on the routine invoice (one call, billed at $0.01). |
| Budgets and spending limits | The client reads `GET /api/v1/key/budget` and `/key/usage/summary`. The `tripwire-otari` key has a $1.00 monthly `api_token` ceiling, which the demo prints (limit, used, remaining, reset). It was not exhausted, so Otari did not refuse. |
| Per-user budgets | Two agent ids exist. A mismatched `user` field is a 403 on this key, so the client omits `user` unless `OTARI_USER` matches the key owner. The $1.00 ceiling is on the single `tripwire-otari` key, not a west-agent key. |
| Guardrails | Otari catalog guardrails were skipped: every option needs an outside vendor key. Tripwire's own policy gate is the guardrail layer. A request-level profile is not sent. |
| Multiple models, distinct roles | Analyst proposes; verifier may only tighten. Confirmed live. |

## Run the sample demo

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q          # 14 passed
python scripts/demo.py       # prints the decision table; writes docs/demo_run.txt
uvicorn tripwire.app:app --port 8000
```

Open http://127.0.0.1:8000 for the dashboard. The header will say **MOCK MODE** until a live token is set.

## Run against hosted Otari.ai

1. Create an account at [otari.ai](https://otari.ai/dashboard/#/signup) if you do not already have one.
2. In the default workspace, create a workspace API key (it starts with `otk_` and is shown once). Optionally create a second key for `ap-agent-west`.
3. Confirm model selectors on the Models page. A Fallback routing policy named `tripwire-analyst`, workspace web access, and a $1.00 monthly limit on the `tripwire-otari` key are already in place for this checkout. Optional leftovers: add a search tool/provider, a second/west key budget, a hosted MCP URL, or (only if you accept an outside vendor key) a catalog guardrail.
4. Copy `.env.example` to `.env` and set `OTARI_API_KEY` (and `OTARI_API_KEY_WEST` if you created one). Do not paste tokens into chat or commit `.env`.
5. `export $(grep -v '^#' .env | xargs)` then `OTARI_MODE=live python scripts/demo.py`.

The client calls `https://api.otari.ai/api/v1` (set `OTARI_BASE_URL=https://eu.api.otari.ai/api/v1` for an EU account). Tokens are never written to the audit log or the dashboard payload.

## Project layout

```
tripwire/          policy gate, audit log, Otari client, agent, dashboard API, MCP handler
dashboard/         local UI
data/              sample books and scenarios
scripts/demo.py    sample-data run
scripts/mcp_books_server.py
tests/             policy, mock, live-client redaction, scenario expectations
docs/              checked-in mock demo log
```

## License

MIT. See [LICENSE](LICENSE).
