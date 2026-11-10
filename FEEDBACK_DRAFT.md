# Feedback draft (revise after the live Otari.ai run)

The official form accepts a 3–5 minute feedback screen recording, written answers, or both. The recording, if you make one, must be your screen and your voice — no AI.

These written answers are a starting point from the MOCK integration and the Otari docs. **Rewrite them in your own words after you have run the app live.** Judges will be able to tell if this is generic.

## Feedback video, if you record one (3–5 min)

1. Walk through the live dashboard and the Otari Overview: what you built, which features you actually used.
2. What worked well, what you liked, what surprised you.
3. What didn't work: bugs, friction, time lost, reproduction steps.
4. What's missing, and what you would change.

## Written answers (draft)

### When were you most tempted to skip Otari and call the provider directly? What happened?

Draft, to revise after the live run:

The temptation is strongest at setup: creating keys, a routing policy, budgets, and guardrails in the dashboard before a first successful `chat/completions` call. Tripwire is deliberately fail-closed, so a missing token, a budget refusal, or a guardrail 403 stops the action instead of falling through to a provider. I kept the client pointed at `https://api.otari.ai/api/v1` and used a labeled mock only when no workspace token was present, so the policy gate could still be reviewed offline. After the live run, add what actually happened — including any 401/404/budget surprises.

### What did you end up building yourself that Otari should've done for you?

Draft, to revise after the live run:

Tripwire still owns the action policy (amount caps, payee and country allowlists, velocity, bill match) and the hash-chained audit log of ALLOW / HOLD / DENY. Otari governs model access, spend, tools, and content guardrails, but it does not, on its own, decide whether a proposed payment may proceed. A first-class "tool/action approval" hook — a way to require a human hold on selected tool calls, with the decision visible next to the trace — would have removed some of that second layer. After the live run, add any dashboard or API gaps you actually hit (for example, reading a key's budget from the workspace token).

### If the rules hadn't required Otari, would you have continued using Otari? Why or why not?

Draft, to revise after the live run:

Yes, for this use case, because the product is a control plane in front of agent spend: one OpenAI-compatible endpoint, open-weight models with a verifier in a second role, budgets on the key, and guardrails that the model cannot decline. I would keep using it if the live run shows traces, fallback, and budget enforcement without more ceremony than a direct provider call. If the live run is painful, say that plainly instead of this paragraph.

## After the live run, replace the drafts with

- Exact model selectors that worked
- Whether fallback, tools, and guardrails showed up on the Overview
- Any bug, including steps to reproduce
- A yes/no you are willing to stand behind on "would you keep using it"
