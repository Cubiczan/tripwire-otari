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

Every model call goes to hosted Otari.ai. An open-weight analyst reviews the invoice, using Otari web search, web fetch, and code execution, plus a books MCP for vendors and open bills. A second open-weight model acts as a tighten-only verifier. Otari budgets and per-user key caps stop an agent that has run out of allowance. Otari guardrails block a prompt-injected memo before a provider is called. A routing policy is used for failover, and the `Otari-Fallback` path is part of the demo.

After Otari returns, a deterministic policy gate (amount caps, payee and country allowlists, velocity, bill match, line totals) issues ALLOW, HOLD, or DENY. The verifier and the books checks can only tighten that decision. Every step is written to a hash-chained audit log. A person can approve a HOLD; that records intent only. This build does not connect a payment rail.

The sample desk is a small wholesale distributor: packaging, grocery wholesale, freight, and store fixtures. The vendors and amounts are invented for the demo.

### How Otari is used

- Hosted gateway at `https://api.otari.ai/api/v1` (OpenAI-compatible `chat/completions`, US region).
- Two open-weight models in distinct roles, selectors confirmed with `GET /api/v1/models`:
  - Analyst / screener: `xiaomi/mimo-v2.6-flash` (catalog $0.14 / $0.28 per million tokens, tools supported). Served by DeepInfra as `XiaomiMiMo/MiMo-V2.6-Flash`.
  - Tighten-only verifier: `z-ai/glm-5.3-flash` (catalog $0.15 / $0.50 per million, tools supported). Served as `zai-org/GLM-5.3-Flash`.
- Code execution via `POST /api/v1/code/execute` to re-sum the routine invoice lines (live, billed at $0.01 per call).
- The failover scenario names the `tripwire-analyst` routing policy first. That policy is not in the dashboard yet, so the client retries with the analyst model and records an app-level fallback (`fallback=True` on the successful live run).
- Books tools (`list_vendors`, `get_vendor`, `list_open_bills`) run in-process on every scenario. They are not yet registered as an Otari MCP server.

### Otari features used (rubric list, honest)

Used live on 10 Nov 2026:

- Open-weight models (analyst + verifier)
- Multiple models serving distinct roles
- Code execution
- App-level fallback after an unconfigured routing-policy name (not an Otari dashboard policy yet)

Wired in the client, but not yet live on this workspace (dashboard steps below):

- Model routing and fallbacks as an Otari policy
- MCP integrations inside Otari (a reachable HTTP MCP URL)
- Web search and web fetch (`workspace_disabled` / `web_access_disabled`)
- Guardrails (no guardrails service configured; sending a profile returns 502)
- Budgets and per-user / per-key spend ceilings (the budget endpoint answers, but `limits` is empty, so Otari does not refuse)

### Live run (10 Nov 2026, 9:43 AM America/New_York)

Log: `docs/demo_run_live.txt`. Tests: 13 passed. Cumulative usage on the `tripwire-otari` key after the successful run: **$0.041994** (45 requests, 10,652 tokens). Almost all of that is four code-execution calls at $0.01; the two chat models together were about $0.002. The $2.00 welcome credit remains almost entirely unused.

Hard scenario expectations all matched: routine allow, hold over threshold, blocked-country deny, over-cap deny, line-total hold, unknown-vendor hold, and the fallback path allow. Two scenarios are marked soft until the dashboard work is done: `budget_exhausted` and `guardrail_block`.

### Dashboard-only steps still needed

The workspace token cannot create routing policies, mandate guardrails, enable web access, or attach spend ceilings (those routes want a master key or a signed-in dashboard session). In the Default workspace (US):

1. **Web search and web fetch.** Tools → turn on `otari_web_search` and `otari_web_fetch`. `otari_code_execution` is already available. If search still returns `web_access_disabled`, add or enable a workspace/organization search key if the Tools page offers one.
2. **Routing policy.** Routing → Policies → Create policy → Fallback → name it exactly `tripwire-analyst` → main model `xiaomi/mimo-v2.6-flash`, backup e.g. `z-ai/glm-5.3-flash` or `deepseek/deepseek-v4.1-flash`. After that, the demo can drop the app-level retry.
3. **Guardrails.** Routing → Guardrails (or Organization → Guardrails) → Configure a catalog guardrail (several vendors ask for their own API key) → Mandate it in **block** mode on the Default workspace. Until a service is configured, a request-level `prompt-injection` profile returns 502 and is not sent.
4. **Budgets.** Spend & budgets → add a USD budget and attach it to the `tripwire-otari` key. For the west-agent scenario, create a second key, cap it low (or spend it down), and put that token in `OTARI_API_KEY_WEST` in `.env` only.
5. **MCP.** Tools → MCP servers → register a Streamable-HTTP URL that Otari can reach (stdio is not enough). Then set `OTARI_MCP_SERVER_URL` in `.env`.

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

3. Otari features used: open-weight analyst and verifier models; routing and fallbacks; MCP books tools; web search and web fetch; code execution; budgets and spending limits; per-user key budgets; guardrails.

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
3. **Finish the dashboard-only setup** listed above if you want the remaining rubric features (search, fetch, Otari routing, guardrails, key budgets, hosted MCP). Tokens stay in `.env` only, never in chat.
4. **Live demo (already run once).** A successful `OTARI_MODE=live python scripts/demo.py` is in `docs/demo_run_live.txt`. After any dashboard changes, rerun it and confirm the new requests on the Otari Overview. For the video, record against a live run, not the mock.
5. **Approve and publish the repo** under Cubiczan (not icohangar-ops), public, branch `devs-wilding`. After the push, paste the first Otari commit URL into this file. I will not create or push the GitHub repo until you say so.
6. **Record the demo video yourself** (3–5 minutes, your screen, your voice, no AI). Shot list: [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md). Upload it, then paste the link.
7. **Feedback.** Record a second 3–5 minute feedback video and/or finalize [FEEDBACK_DRAFT.md](FEEDBACK_DRAFT.md) in your own words after the live run.
8. **Approve this BUIDL text and the email body**, then submit on DoraHacks and reply to Marcus. I will not submit either one until you approve.
