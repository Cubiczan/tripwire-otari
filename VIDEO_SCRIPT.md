# Demo video script (3–5 minutes) and shot list

**You have to record this.** The official rules say the demo video and any feedback video cannot use AI. It must be a screen recording with your voice, showing the project.

Do not record until a **live** Otari.ai run is working, so the video can show the hosted gateway and the Otari Overview. If you can only record the mock, say so clearly on camera; that is weaker for judging and may not meet "you must use Otari.ai."

Target length: about 4 minutes. Stay inside 3–5 minutes.

Suggested filename once you export: `tripwire-otari-demo.mp4`. Upload to YouTube (unlisted is fine if the link works without a sign-in) and paste the URL into SUBMISSION.md.

## Shot list

| Time | Shot | What to show | What to say |
|---|---|---|---|
| 0:00–0:25 | Title + one diagram | README header, or the dashboard with the **LIVE** banner visible | "I'm Sam Desigan. This is Tripwire, a guardrail layer for AI-agent actions. Every model call goes through hosted Otari.ai. Tripwire then allows, holds, or denies the action before money can move. No payment rail is connected in this demo; approvals record intent only." |
| 0:25–0:50 | Architecture | The flow in the README, or a quick skim of `tripwire/otari.py` calling `api.otari.ai/api/v1` | "The agent never talks to a provider directly. Otari authenticates the workspace key, enforces budgets, runs guardrails, and can search, fetch, and execute code. I use two open-weight models: one analyst, one tighten-only verifier, plus a routing policy for failover." |
| 0:50–1:20 | Dashboard + Otari Overview | Local dashboard at localhost:8000, then the Otari.ai Overview / Requests tab from the live run | "Here is the local decision log, and here is the same traffic on Otari's Overview: model, cost, and status." |
| 1:20–1:50 | Routine ALLOW | `allow_routine` in the dashboard or demo output | "A $185 carton invoice from an allowlisted vendor. The books MCP finds a matching open bill. Otari code execution re-sums the lines. The analyst and verifier agree. Tripwire allows it." |
| 1:50–2:15 | HOLD over threshold | `hold_over_threshold` | "A $2,400 fixture invoice is over the review threshold, so it is held for a person. I'll approve it here. That records intent only — nothing is paid." |
| 2:15–2:40 | DENY country and cap | `deny_country`, `deny_over_max` | "A blocked-country payee is denied. A $12,000 invoice is over the hard cap and is also denied. Denied actions never join the payment history." |
| 2:40–3:10 | Mismatch, unknown vendor | `line_total_mismatch`, `unknown_vendor` | "When the line items don't add up to the invoice total, Otari's code tool and the books check both hold it. A vendor that isn't in the books is held the same way." |
| 3:10–3:40 | Budgets, guardrails, fallback | `budget_exhausted`, `guardrail_block`, `fallback_routing`, plus Otari traces if visible | "The west agent has used up its per-user Otari budget, so the call never goes through. A prompt-injected memo is blocked by Otari's guardrail with a 403. On the last scenario the routing policy falls back, and Otari marks that fallback." |
| 3:40–4:10 | Audit chain + close | `GET /api/audit/verify` or the demo's "Audit chain: OK" line, repo URL if public | "Every decision is in a hash-chained audit log, and the chain verifies. Repo: github.com/Cubiczan/tripwire-otari, branch devs-wilding. Thanks." |

If you are running long, drop the mismatch and unknown-vendor shot and keep budgets, guardrails, and fallback — those are the Otari-specific rubric items.

## Recording notes

- Say that sample vendors are invented, and that ALLOW does not move money.
- If any scenario failed in the live run, say so and show the error. Do not pretend a mock result is live.
- Do not display the `otk_` token. Keep `.env` and the Otari "copy key" dialog off screen.
- Do not mention confidential buyers or any other contest by name unless you want to.
- A separate 3–5 minute feedback recording, if you make one, is in FEEDBACK_DRAFT.md. It can be a second file. Do not try to cram both into one video under three minutes.
