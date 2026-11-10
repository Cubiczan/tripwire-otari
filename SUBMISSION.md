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

- Hosted gateway at `https://api.otari.ai/api/v1` (OpenAI-compatible `chat/completions`).
- Two open-weight models in distinct roles: analyst (default DeepSeek selector from Otari's quickstart) and verifier (default Mistral Large 4).
- A Fallback routing policy, `tripwire-analyst`, sent as the model name on the failover scenario.
- Built-in tools on the analyst request: `otari_web_search`, `otari_web_fetch`, `otari_code_execution`.
- MCP books tools (`list_vendors`, `get_vendor`, `list_open_bills`), used in the agent loop; a stdio MCP server is included so the same tools can be registered in the Otari dashboard.
- Spend budgets and per-user key caps, with the agent id sent as the chat `user`.
- A `prompt-injection` guardrail in block mode on every chat request.

Live use requires an Otari.ai account and workspace tokens. Until those are set, the repo runs a clearly labeled mock of the same interface so the policy gate, audit log, and sample scenarios can be reviewed offline.

### Otari features used (rubric list)

- Open-weight models (analyst + verifier)
- Model routing and fallbacks
- MCP integrations
- Web search and web fetch
- Code execution
- Budgets and spending limits
- Multiple models serving distinct roles
- Guardrails
- Per-user budgets

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
3. **Workspace setup, then a token.** In the dashboard: confirm two open-weight model selectors; create a Fallback policy named `tripwire-analyst`; attach budgets, including a tight cap on a second key for `ap-agent-west`; mandate a prompt-injection guardrail in block mode; enable web search, web fetch, and code execution. Create workspace API keys (`otk_…`). Put them in `.env` only, never in chat.
4. **Live demo.** Set `OTARI_MODE=live` and rerun `python scripts/demo.py`. Confirm the requests on the Otari Overview. This MOCK run is not enough for prize eligibility.
5. **Approve and publish the repo** under Cubiczan (not icohangar-ops), public, branch `devs-wilding`. After the push, paste the first Otari commit URL into this file. I will not create or push the GitHub repo until you say so.
6. **Record the demo video yourself** (3–5 minutes, your screen, your voice, no AI). Shot list: [VIDEO_SCRIPT.md](VIDEO_SCRIPT.md). Upload it, then paste the link.
7. **Feedback.** Record a second 3–5 minute feedback video and/or finalize [FEEDBACK_DRAFT.md](FEEDBACK_DRAFT.md) in your own words after the live run.
8. **Approve this BUIDL text and the email body**, then submit on DoraHacks and reply to Marcus. I will not submit either one until you approve.
