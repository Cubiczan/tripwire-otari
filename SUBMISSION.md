# Submission draft — Tripwire for Otari

**Status: not submitted.** This is paste-ready text for Shyam's review. Do not publish the repo, upload a video, or submit on DoraHacks or by email until the checklist at the bottom is approved.

Hackathon: [Mozilla Otari Hackathon - Devs Wilding Online!](https://dorahacks.io/hackathon/mozilla-devs-wilding/detail)  
Deadline: Wednesday 11 Nov 2026, 5:59 PM America/New_York  
Registered on DoraHacks as: Sam Desigan  
Intended public repo: https://github.com/Cubiczan/tripwire-otari  
Hackathon branch: `devs-wilding`

There are two official intake paths. Plan to use both, so prize eligibility is not lost on a technicality.

- DoraHacks BUIDL form (GitHub/GitLab/Bitbucket link required, demo video required).
- Reply to the sign-up thread with marcus+wilding@mozilla.org, with the same items. If that sign-up email was never sent, send it first, then reply with the submission.

---

## DoraHacks BUIDL text

### Title / project name

Tripwire

### Tagline

A guardrail layer that screens and logs every AI-agent action through Otari before it can spend money or touch live systems.

### One line (also used in the email)

Tripwire is a policy-and-audit gate that sends every agent model call through hosted Otari.ai, then allows, holds, or denies the action before money moves or a live system is touched.

### Description

Accounts-payable agents can propose payments, but they should not hold payment keys or talk to a model provider on their own. Tripwire sits in front of those actions.

Every model call goes to hosted Otari.ai. An open-weight analyst reviews the invoice through an Otari Fallback policy, using Otari code execution and, on the blocked-country invoice, a single official-page web fetch, plus a books MCP for vendors and open bills. A second open-weight model acts as a tighten-only verifier. The workspace key has a $1.00 monthly spend ceiling that the demo reads back from `/key/budget`. After Otari returns, a deterministic policy gate (amount caps, payee and country allowlists, velocity, bill match, line totals) issues ALLOW, HOLD, or DENY. The verifier and the books checks can only tighten that decision. That same gate is the guardrail layer: Otari catalog guardrails were not enabled, because every dashboard option needs an outside vendor key. Every step is written to a hash-chained audit log. A person can approve a HOLD; that records intent only. This build does not connect a payment rail.

The sample desk is a small wholesale distributor: packaging, grocery wholesale, freight, and store fixtures. The vendors and amounts are invented for the demo.

### How Otari is used

- Hosted gateway at `https://api.otari.ai/api/v1` (OpenAI-compatible `chat/completions`, US region).
- Two open-weight models in distinct roles, selectors confirmed with `GET /api/v1/models`:
  - Analyst / screener: `xiaomi/mimo-v2.6-flash` (catalog $0.14 / $0.28 per million tokens, tools supported). Served by DeepInfra as `XiaomiMiMo/MiMo-V2.6-Flash`.
  - Tighten-only verifier: `z-ai/glm-5.3-flash` (catalog $0.15 / $0.50 per million, tools supported). Served as `zai-org/GLM-5.3-Flash`.
- Analyst chats go through the dashboard Fallback policy `tripwire-analyst` (main `xiaomi/mimo-v2.6-flash`, backup `z-ai/glm-5.3-flash`). The client still retries on the named analyst model if the policy request fails. On the 10 Nov 2026 9:53 AM America/New_York run, Otari served the primary model (`Otari-Fallback: false`).
- Code execution via `POST /api/v1/code/execute` to re-sum the routine invoice lines (live, billed at $0.01 per call; used once per demo).
- Web fetch via `POST /api/v1/fetch` once on `deny_country`, against `https://ofac.treasury.gov/`, to corroborate that North Korea is an OFAC sanctions program (also billed at $0.01). Page content is treated as untrusted evidence. Direct `POST /search` still returns 400 because no search tool/provider is configured, even though `GET /tools` lists `otari_web_search` as available.
- `GET /api/v1/key/budget` is read and printed in the demo: $1.00 USD monthly `api_token` limit, used and remaining, reset at 2026-12-01T00:00:00Z (2026-11-30 19:00 EST America/New_York).
- Books tools (`list_vendors`, `get_vendor`, `list_open_bills`) run in-process on every scenario. They are not yet registered as an Otari MCP server.

### Otari features used (rubric list, honest)

Used live on 10 Nov 2026, 9:53 AM America/New_York:

- Open-weight models (analyst + verifier)
- Multiple models serving distinct roles
- Model routing: all analyst chats used the `tripwire-analyst` Fallback policy (primary served; backup is configured). A client retry remains as a backstop and was not needed on this run.
- Web fetch (one official OFAC page lookup on `deny_country`)
- Code execution (once, on the routine invoice)
- Budgets: the `tripwire-otari` key's $1.00 monthly ceiling was read from `/key/budget` and shown in the demo (not exhausted, so Otari did not refuse)

Not claimed as live Otari features:

- Web search: workspace web access is on and `GET /tools` lists `otari_web_search` as available, but `POST /search` returns 400 until a search tool/provider is added on Tools & Guardrails (or via `POST /search-tools`, which wants a master key).
- Otari catalog guardrails: skipped. Every catalog option needs an outside vendor key (Lakera, Azure Prompt Shields, Alinia, Patronus, watsonx, Bedrock, or OpenAI Moderation). Tripwire's own policy gate is the guardrail layer.
- MCP inside Otari: books tools still run in-process; no Streamable-HTTP MCP URL is registered.
- Per-user / second-key budgets: the $1.00 ceiling is on the single `tripwire-otari` key (`api_token` scope), not a west-agent key, so `budget_exhausted` stays a documented soft gap.
- `Otari-Fallback: true` was not observed; the policy's primary model served every analyst call.

### Live run (10 Nov 2026, 9:53 AM America/New_York)

Log: `docs/demo_run_live.txt`. Tests: 14 passed. Cumulative usage on the `tripwire-otari` key after this run: **$0.072451** (60 requests, 8 errors, 14,056 tokens). The key's monthly ceiling showed **used $0.030457 / $1.00**, remaining **$0.969543**, reset 2026-12-01T00:00:00Z (2026-11-30 19:00 EST America/New_York). Almost all spend is tool calls at $0.01 each (code execution and web fetch); the two chat models together were a couple of tenths of a cent. This dashboard-wiring demo added about **$0.020** on top of earlier smoke and demo calls. Still well under the $0.25 target and the $2.00 welcome credit.

Hard scenario expectations all matched: routine allow, hold over threshold, blocked-country deny (with OFAC corroboration), over-cap deny, line-total hold, unknown-vendor hold, and the routing-policy path allow. Two scenarios remain soft: `budget_exhausted` (no second/west key budget; the $1.00 ceiling is not exhausted) and `guardrail_block` (no Otari catalog guardrail).

### Dashboard-only steps still needed

The workspace token cannot create routing policies, search-tool providers, mandated guardrails, or a second-key ceiling (those routes want a master key or a signed-in dashboard session). Already done in the dashboard: workspace web access, the `tripwire-analyst` Fallback policy, and the $1.00 monthly limit on `tripwire-otari`. Still open, if you want the remaining rubric points:

1. **Web search provider.** Tools & Guardrails → add a search tool/provider (or `POST /api/v1/search-tools` with a master key). Web access is already on; fetch already works; only search is still unconfigured.
2. **Guardrails.** Left skipped on purpose. Every catalog option needs an outside vendor key. Tripwire's policy gate remains the guardrail layer unless you later add a vendor key and mandate a profile in **block** mode.
3. **Per-user / west-agent budget.** Create a second key, cap it low (or spend it down), and put that token in `OTARI_API_KEY_WEST` in `.env` only. Do not lower the existing $1.00 ceiling just to force a deny in the demo.
4. **MCP.** Tools → MCP servers → register a Streamable-HTTP URL that Otari can reach (stdio is not enough). Then set `OTARI_MCP_SERVER_URL` in `.env`.

Do not paste tokens into chat. Do not commit `.env`.

### Tech stack

Python 3.11+, FastAPI, httpx, SQLite audit log, vanilla HTML dashboard. Otari.ai hosted gateway (OpenAI-compatible API). Optional stdio MCP server for the books tools. pytest for the policy, audit, and scenario suite.

### GitHub

https://github.com/Cubiczan/tripwire-otari (not created yet — see checklist)

Branch: `devs-wilding`

First Otari commit: paste the commit URL after the branch is pushed. In this checkout the opening commit on `devs-wilding` is the Otari integration.

### Demo video

Paste the YouTube (or other public) URL after you record and upload it. Follow [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md). The recording must be your screen and your voice. Do not use an AI voice or an AI-generated video.

### Issues / PRs on mozilla-ai/otari

None opened from this entry yet. Do not file any until you approve the text. Known public issues that already exist and that this build worked around in docs: path confusion between `/v1` and `/api/v1`, and `/api/v1/key` vs `/key/budget`.

---

## Draft email (reply to the sign-up thread)

To: marcus+wilding@mozilla.org  
Subject: Developers Wilding submission — Tripwire

If there is no existing thread, send a short sign-up first (name: Sam Desigan; Otari.ai email: _your Otari.ai email_; one sentence: the "One line" above), then reply with this body.

```
Hi Marcus,

Submitting Tripwire for Developers Wilding: Online.

1. Project: Tripwire
   Otari.ai email: [ADD THE EMAIL USED TO SIGN UP AT OTARI.AI]
   One line: Tripwire is a policy-and-audit gate that sends every agent model call through hosted Otari.ai, then allows, holds, or denies the action before money moves or a live system is touched.

2. Public repo: https://github.com/Cubiczan/tripwire-otari
   Hackathon branch: devs-wilding
   First commit where Otari came in: [ADD COMMIT URL]

3. Otari features used: open-weight analyst and verifier models in distinct roles; the tripwire-analyst Fallback routing policy (client retry kept as a backstop); in-process MCP books tools; web fetch of the official OFAC page on the blocked-country invoice (web search is not configured yet); code execution; the tripwire-otari $1.00 monthly key budget, read back from /key/budget. Otari catalog guardrails were not enabled; Tripwire's own policy gate is the guardrail layer. Per-user / second-key budgets are not attached.

4. PRs or issues opened on mozilla-ai/otari: none from this entry.

5. Demo video (3–5 min): [ADD URL]

6. Written feedback is below. [Optional: feedback screen recording URL]

Written feedback:

When were you most tempted to skip Otari and call the provider directly?
[See FEEDBACK_DRAFT.md — replace with your words after the live run.]

What did you end up building yourself that Otari should've done for you?
[See FEEDBACK_DRAFT.md.]

If the rules hadn't required Otari, would you have continued using Otari? Why or why not?
[See FEEDBACK_DRAFT.md.]

Thanks,
Sam Desigan
```

Do not send this email until you approve the final text. It should go out as a DraftExternalMessage card, not directly from this workspace.

---

## What you need to do or approve

Nothing below has been done for you.

1. **Confirm registration.** You are on DoraHacks as Sam Desigan. If the email to marcus+wilding@mozilla.org was never sent, approve a short sign-up email first.
2. **Otari.ai account.** Sign up at https://otari.ai/dashboard/#/signup if you do not already have an account (first 200 sign-ups receive $20 in tokens, if that offer is still open). Join the Mozilla OSAI Discord and grant the `devs-wilding` role. Star https://github.com/mozilla-ai/otari.
3. **Optional remaining dashboard work** listed above if you want search, a vendor guardrail, a west-agent key budget, or hosted MCP. Do not add a vendor guardrail key unless you are comfortable with that vendor. Tokens stay in `.env` only, never in chat.
4. **Live demo (already rerun after the dashboard changes).** The latest successful `OTARI_MODE=live python scripts/demo.py` is in `docs/demo_run_live.txt` (10 Nov 2026, 9:53 AM America/New_York). For the video, record against a live run, not the mock. Confirm the same requests on the Otari Overview.
5. **Approve and publish the repo** under Cubiczan (not icohangar-ops), public, branch `devs-wilding`. After the push, paste the first Otari commit URL into this file. I will not create or push the GitHub repo until you say so.
6. **Record the demo video yourself** (3–5 minutes, your screen, your voice, no AI). Shot list: [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md). Upload it, then paste the link.
7. **Feedback.** Record a second 3–5 minute feedback video and/or finalize [FEEDBACK_DRAFT.md](FEEDBACK_DRAFT.md) in your own words after the live run.
8. **Approve this BUIDL text and the email body**, then submit on DoraHacks and reply to Marcus. I will not submit either one until you approve.
