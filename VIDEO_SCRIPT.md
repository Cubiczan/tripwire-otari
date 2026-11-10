# Demo video script (3–5 minutes) and shot list

A silent 1080p screen-and-caption cut is ready at [video/tripwire-otari-demo.mp4](video/tripwire-otari-demo.mp4) (3:33, no AI voice or imagery) for you to add your own voiceover and upload.

**You have to record this.** The official rules say the demo video and any feedback video cannot use AI. It must be a screen recording with your voice, showing the project.

Record against a **live** Otari.ai run (`OTARI_MODE=live python scripts/demo.py`, then the dashboard at http://127.0.0.1:8000). The latest live log is `docs/demo_run_live.txt` (10 Nov 2026, 9:53 AM America/New_York). If you change the Otari dashboard again, rerun first and narrate whatever actually changed.

Target length: about 4 minutes. Stay inside 3–5 minutes.

Suggested filename once you export: `tripwire-otari-demo.mp4`. Upload to YouTube (unlisted is fine if the link works without a sign-in) and paste the URL into SUBMISSION.md.

## Shot list

| Time | Shot | What to show | What to say |
|---|---|---|---|
| 0:00–0:25 | Title + live banner | Local dashboard with the **LIVE** banner, or the demo header | "I'm Sam Desigan. This is Tripwire, a guardrail layer for AI-agent actions. Every model call goes through hosted Otari.ai. Tripwire then allows, holds, or denies the action before money can move. No payment rail is connected; approvals record intent only." |
| 0:25–0:50 | Two models + routing policy | Demo lines for analyst `xiaomi/mimo-v2.6-flash`, verifier `z-ai/glm-5.3-flash`, and `requested=tripwire-analyst` | "I use two open-weight models in different roles. Xiaomi MiMo V2.6 Flash is the invoice analyst, reached through an Otari Fallback policy named tripwire-analyst, with GLM-5.3-Flash as the policy backup. GLM-5.3-Flash is also the tighten-only verifier. On this run Otari served the primary model. The client still has a retry if the policy request fails." |
| 0:50–1:15 | Otari Overview + spend + key budget | Otari.ai Overview / Spend, or the usage and `GET /key/budget` block in `docs/demo_run_live.txt` | "Here is the same traffic on Otari. Code execution and web fetch are the main costs, at one cent a call, so the demo only runs each once. Chat tokens were a fraction of a cent. The tripwire-otari key has a one-dollar monthly limit. After this run it had used about three cents of that ceiling, which I read back from /key/budget." |
| 1:15–1:40 | Routine ALLOW + code execution | `allow_routine`: both models recommend allow; show the code-execution total if the dashboard or log shows it | "A $185 carton invoice from an allowlisted vendor. The books tools find a matching open bill. Otari code execution re-sums the lines. Analyst and verifier both allow it." |
| 1:40–2:00 | HOLD over threshold | `hold_over_threshold` | "A $2,400 fixture invoice is over the review threshold, so it is held. On this run the analyst recommended allow, and the verifier tightened that to a hold. I'll approve it here. That records intent only — nothing is paid." |
| 2:00–2:25 | DENY country with OFAC fetch, and cap | `deny_country` (`ofac_fetch` / `ofac_program_corroborated`), `deny_over_max` | "A blocked-country payee is denied by the policy gate. I also fetched the official OFAC page once to corroborate that North Korea is a listed sanctions program. That page is treated as untrusted evidence; it only supports the existing deny. A $12,000 invoice is over the hard cap and is denied without extra model calls." |
| 2:25–2:45 | Mismatch and unknown vendor | `line_total_mismatch`, `unknown_vendor` | "When the line items don't add up, both the books check and the two models hold it. A vendor that isn't in the books is held the same way." |
| 2:45–3:20 | Honest gaps | The two soft rows, and the feature table (`web_search` no, `guardrails` no, `per_user_budgets` no) | "Web search is not in this run: workspace web access is on, but no search provider is configured yet, so I used fetch instead of looping the model on search. Otari catalog guardrails were skipped because every option needs an outside vendor key. Tripwire's own policy gate is the guardrail layer. There is no second key budget, so the west-agent exhausted-budget case stays a documented soft hold." |
| 3:20–3:45 | Audit chain + close | Audit OK line, repo URL if public | "Every decision is in a hash-chained audit log, and the chain verifies. Repo: github.com/Cubiczan/tripwire-otari, branch devs-wilding. Thanks." |

If you are running long, keep the two-model intro with the routing policy, the routine allow with code execution, the OFAC fetch on the country deny, one hold, and the honest gaps. Those are the Otari-specific points.

## Recording notes

- Say that sample vendors are invented, and that ALLOW does not move money.
- If a later live run differs from this script, say what actually happened. Do not pretend a mock result is live. Do not claim web search, Otari catalog guardrails, a fired `Otari-Fallback` header, or a per-user budget refusal unless you have enabled them and rerun.
- Do not display the `otk_` token. Keep `.env` and the Otari "copy key" dialog off screen.
- A separate 3–5 minute feedback recording, if you make one, is in FEEDBACK_DRAFT.md. It can be a second file.
