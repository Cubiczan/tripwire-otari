# Demo video script (3–5 minutes) and shot list

**You have to record this.** The official rules say the demo video and any feedback video cannot use AI. It must be a screen recording with your voice, showing the project.

Record against a **live** Otari.ai run (`OTARI_MODE=live python scripts/demo.py`, then the dashboard at http://127.0.0.1:8000). The 10 Nov 2026 live log is in `docs/demo_run_live.txt`. If you have since enabled search, guardrails, or a routing policy in the Otari dashboard, rerun first and narrate whatever actually changed.

Target length: about 4 minutes. Stay inside 3–5 minutes.

Suggested filename once you export: `tripwire-otari-demo.mp4`. Upload to YouTube (unlisted is fine if the link works without a sign-in) and paste the URL into SUBMISSION.md.

## Shot list

| Time | Shot | What to show | What to say |
|---|---|---|---|
| 0:00–0:25 | Title + live banner | Local dashboard with the **LIVE** banner, or the demo header | "I'm Sam Desigan. This is Tripwire, a guardrail layer for AI-agent actions. Every model call goes through hosted Otari.ai. Tripwire then allows, holds, or denies the action before money can move. No payment rail is connected; approvals record intent only." |
| 0:25–0:50 | Two models | Demo output or Otari Overview showing `xiaomi/mimo-v2.6-flash` and `z-ai/glm-5.3-flash` | "I use two open-weight models in different roles. Xiaomi MiMo V2.6 Flash is the invoice analyst. Z.ai GLM-5.3-Flash is a tighten-only verifier. Selectors came from Otari's /models list." |
| 0:50–1:15 | Otari Overview + spend | Otari.ai Overview / Requests and Spend, or the usage block in `docs/demo_run_live.txt` | "Here is the same traffic on Otari's Overview. Code execution is the main cost, at one cent a call, so the demo only runs it on the routine invoice. Chat tokens were a fraction of a cent. All of this is well under the welcome credit." |
| 1:15–1:40 | Routine ALLOW + code execution | `allow_routine`: both models recommend allow; show the code-execution total if the dashboard or log shows it | "A $185 carton invoice from an allowlisted vendor. The books tools find a matching open bill. Otari code execution re-sums the lines. Analyst and verifier both allow it." |
| 1:40–2:00 | HOLD over threshold | `hold_over_threshold` | "A $2,400 fixture invoice is over the review threshold, so it is held. The verifier keeps that hold. I'll approve it here. That records intent only — nothing is paid." |
| 2:00–2:20 | DENY country and cap | `deny_country`, `deny_over_max` | "A blocked-country payee is denied by the policy gate, and a $12,000 invoice is over the hard cap. Those two do not spend additional model calls." |
| 2:20–2:45 | Mismatch and unknown vendor | `line_total_mismatch`, `unknown_vendor` | "When the line items don't add up, both the books check and the two models hold it. A vendor that isn't in the books is held the same way." |
| 2:45–3:15 | Fallback, and the honest gaps | `fallback_routing` (fallback=True), then the two soft rows | "For failover I first request a routing policy named tripwire-analyst. That policy isn't in the dashboard yet, so the client retries on the analyst model and Otari still serves the call. Two other scenarios stay soft until I turn on a per-key budget and a guardrails service in the Otari dashboard. Web search and fetch are also still disabled on the workspace." |
| 3:15–3:45 | Audit chain + close | Audit OK line, repo URL if public | "Every decision is in a hash-chained audit log, and the chain verifies. Repo: github.com/Cubiczan/tripwire-otari, branch devs-wilding. Thanks." |

If you are running long, keep the two-model intro, the routine allow with code execution, one hold, one deny, and the fallback plus gaps. Those are the Otari-specific points.

## Recording notes

- Say that sample vendors are invented, and that ALLOW does not move money.
- If a later live run differs from this script, say what actually happened. Do not pretend a mock result is live, and do not claim search, guardrails, or an Otari routing policy unless you have enabled them and rerun.
- Do not display the `otk_` token. Keep `.env` and the Otari "copy key" dialog off screen.
- A separate 3–5 minute feedback recording, if you make one, is in FEEDBACK_DRAFT.md. It can be a second file.
