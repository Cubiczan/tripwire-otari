# Tripwire for Otari

**A guardrail layer that screens and logs every AI-agent action through [Otari](https://otari.ai) before it can spend money or touch live systems.**

Built for the Mozilla Otari Hackathon (Developers Wilding: Online) on DoraHacks. Draft only: nothing in this folder has been published or submitted.

```
agent proposes a payment or write
        │
        ▼
  hosted Otari.ai  ──  open-weight analyst + verifier
        │               routing / fallback
        │               web search, web fetch, code execution
        │               MCP books tools
        │               budgets, per-user key caps, guardrails
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

This checkout runs in **MOCK mode** until a hosted Otari.ai workspace token is provided. The mock speaks the documented Otari request shapes (`/api/v1/chat/completions`, built-in tools, guardrails, key budgets, fallback headers) and labels every result `mock: true`. The dashboard banner says so. The sample-data demo and the tests pass without a network call.

Prize eligibility requires a **live** run against Otari.ai, a **public** repository, a **hackathon branch**, a link to the **first commit where Otari came in**, and a **3–5 minute participant-narrated screen recording** (no AI video or voice). See [RULES.md](RULES.md), [SUBMISSION.md](SUBMISSION.md), and [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md).

Intended public GitHub owner, when you approve a publish: **Cubiczan**, repo name `tripwire-otari`, branch `devs-wilding`. This folder does not create that repository and does not push.

## What the demo shows

Sample data is a small wholesale / distribution AP desk (packaging, wholesale, freight, fixtures). The vendors and bills are invented.

| Scenario | Decision | Why |
|---|---|---|
| Routine $185 carton invoice | ALLOW | Allowlisted vendor, matching open bill, totals agree |
| $2,400 fixture invoice | HOLD | Over the $1,000 review threshold |
| Payee in a blocked country | DENY | Country policy |
| $12,000 freight prepay | DENY | Over the $5,000 hard cap |
| Invoice total does not match lines | HOLD | Books + Otari code execution |
| Vendor missing from the books | HOLD | MCP books lookup |
| West-coast agent has no Otari budget left | DENY | Per-user key budget |
| Prompt-injection memo | DENY | Otari guardrail, before a provider is called |
| Analyst routing policy | ALLOW | Fallback path is used and recorded |

A person can approve or deny a HOLD. That records intent only. **No payment rail is connected.**

## Otari features the app is written to use

These map to the official rubric. In MOCK mode they are exercised against the documented interface. After a live key is configured, rerun the demo and confirm the same traces on the Otari Overview.

| Rubric item | How Tripwire uses it |
|---|---|
| Open-weight models (two roles) | Analyst (default `deepseek/deepseek-v4-pro-0813`) and a tighten-only verifier (default `mistral/mistral-large-4`). Confirm exact selectors in the Otari Models page. |
| Model routing and fallbacks | Optional request uses the `tripwire-analyst` routing policy as the model name. The demo includes a fallback scenario. |
| MCP integrations | Books tools `list_vendors`, `get_vendor`, `list_open_bills`. The agent uses them in-process every run. `scripts/mcp_books_server.py` is a stdio MCP server you can register in the Otari dashboard once you have a reachable host. |
| Web search or web fetch | Analyst requests include `otari_web_search` and `otari_web_fetch` (header `Otari-Web-Search: otari`). |
| Code execution | Analyst requests include `otari_code_execution` to re-sum invoice lines. |
| Budgets and spending limits | Budget is checked before a model call; a refusal fails closed. |
| Per-user budgets | Two agents (`ap-agent-east`, `ap-agent-west`) with separate key budgets. The `user` field on each chat request is the agent id. |
| Guardrails | Each chat request tightens the `prompt-injection` profile in `block` mode. An injected memo is denied. |
| Multiple models, distinct roles | Analyst proposes; verifier may only tighten. |

## Run the sample demo

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q          # 13 passed
python scripts/demo.py       # prints the decision table; writes docs/demo_run.txt
uvicorn tripwire.app:app --port 8000
```

Open http://127.0.0.1:8000 for the dashboard. The header will say **MOCK MODE** until a live token is set.

## Run against hosted Otari.ai

1. Create an account at [otari.ai](https://otari.ai/dashboard/#/signup) if you do not already have one.
2. In the default workspace, create a workspace API key (it starts with `otk_` and is shown once). Optionally create a second key for `ap-agent-west`.
3. Confirm model selectors on the Models page. Create a Fallback routing policy named `tripwire-analyst`. Attach budgets / ceilings (including a spent-down cap on the west key). Mandate a prompt-injection guardrail in block mode. Enable web search, web fetch, and code execution for the workspace. Optionally register `scripts/mcp_books_server.py` as an MCP server.
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
