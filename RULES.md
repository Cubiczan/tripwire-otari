# Mozilla Otari Hackathon (Developers Wilding: Online) — rules notes

Captured 10 Nov 2026 from the official pages. This file does not replace those pages. Recheck them before submitting.

## Official sources

- DoraHacks event: https://dorahacks.io/hackathon/mozilla-devs-wilding/detail
- Organizer page: https://otari.ai/devs-wilding
- Judging rubric: https://docs.google.com/document/d/1-spnCZ3f2SSki8cb6FnochjchdyttUsjjxfoE6aBnF4/edit
- Otari product / docs: https://github.com/mozilla-ai/otari, https://github.com/mozilla-ai/otari/blob/main/docs/quickstart.md
- Organizer announcement: https://github.com/mozilla-ai/llamafile/discussions/1074

The DoraHacks listing is titled **Mozilla Otari Hackathon - Devs Wilding Online!** Organizer: Mozilla. About 140 registered hackers were shown on the event page when this was captured.

## Deadline

- DoraHacks timeline (UTC-5): submissions opened 28 Oct 2026 12:00, deadline **11 Nov 2026 17:59** (5:59 PM America/New_York).
- The otari.ai and DoraHacks writeups also say **November 11, 11:59 PM** without spelling out a zone. 11:59 PM in Spain (CET, UTC+1, where MozFest is running) is the same 5:59 PM ET clock time. Treat **5:59 PM ET on Wednesday 11 Nov 2026** as the cutoff, and do not cut it close.

## Requirement that matters most

You must use **hosted Otari.ai** as the AI gateway. Self-hosting after the fact is allowed; it does not replace hosted use for this hackathon. A feature scores only when the application actually uses it, not when it is merely switched on in the dashboard.

Creating an Otari.ai account alone does not enter you in the hackathon.

## How to register

Two official writeups exist. Do both if any step is still outstanding.

DoraHacks page:

1. Sign up on DoraHacks with your name or pseudonym, the email you will use on Otari.ai, and one sentence about the project.
2. Create an account on hosted Otari.ai (https://otari.ai/dashboard/#/signup). The first 200 people to sign up receive $20 in tokens.
3. Join the Mozilla OSAI Discord and grant yourself the `devs-wilding` role.
4. Star https://github.com/mozilla-ai/otari
5. Start a **new branch** in the project and build with Otari.ai.

otari.ai/devs-wilding (and Marcus's llamafile post) also ask you to email [marcus+wilding@mozilla.org](mailto:marcus+wilding@mozilla.org) with the same three facts (name, Otari.ai email, one-sentence project). The page says submission is a **reply on that sign-up thread**.

Shyam is already registered on DoraHacks as Sam Desigan. Confirm whether the Marcus email was also sent.

## What a submission must include

If any of these is missing, the project is not eligible for prizes.

1. Project name, the email used to sign up at Otari.ai, and one line on what the project does.
2. A **public** GitHub (or GitLab / Bitbucket) repository link **and** the hackathon branch name.
3. You must use Otari.ai. **Link to the first commit on that branch where Otari came in.**
4. The Otari features used (see the rubric).
5. Any PRs or issues opened on the Otari repo.
6. A link to a **3 to 5 minute** project demo video, showing the progress made with Otari.
7. Feedback: a screen-recording, written answers, or both.

### Video rules (strict)

The rubric and the DoraHacks page both say: **video demonstration and video feedback cannot use AI.** It must be a screen recording with audio of the hackathon participant demonstrating the project.

### Feedback screen recording (3 to 5 minutes)

Talk through, on screen:

1. What did you build with Otari, and which features did you use? Walk through it.
2. What worked well? What you liked, what surprised you.
3. What didn't work? Bugs, friction, anything that cost you time. Reproduction steps if you can.
4. What's missing, and what would you change?

### Written feedback

1. When were you most tempted to skip Otari and call the provider directly? What happened?
2. What did you end up building yourself that Otari should've done for you?
3. If the rules hadn't required Otari, would you have continued using Otari? Why or why not?

## Judging rubric (100 points)

| Area | Points | How it is scored |
|---|---|---|
| Open-weight models | 30 | 20 for meaningfully using at least one open-weight model; 10 more for two or more open-weight models in different roles |
| Otari features | 60 | 10 each, up to the cap, only when actually used: model routing and fallbacks; MCP integrations; web search or web fetch; code execution; budgets and spending limits; multiple models serving distinct roles; guardrails; per-user budgets |
| Project and demo | 10 | 5 if the application works and shows a real use case; 5 if the video clearly explains the Otari integration and shows the claimed capabilities |

## How Otari is integrated (API)

- Hosted OpenAI-compatible base URL: `https://api.otari.ai/api/v1` (EU accounts: `https://eu.api.otari.ai/api/v1`).
- Workspace API tokens are created in the dashboard, start with `otk_`, and are shown once.
- Chat: `POST /api/v1/chat/completions`, plus `/messages` and `/responses`.
- Built-in tools on a chat request: `{"type":"otari_web_search"}`, `{"type":"otari_web_fetch"}`, `{"type":"otari_code_execution"}`. MCP servers can be declared on the same request (`mcp_servers` / `mcp_server_ids`).
- Direct code run: `POST /api/v1/code/execute`.
- Guardrails can be mandated in the dashboard and tightened per request with a top-level `guardrails` field. A block is `403` / `guardrail_violation`.
- Budgets are created under Spend & budgets, then applied as a spend ceiling, or attached to a single API key. Per-user budgets limit each attached user. The `user` field on a chat request is how usage lands on a user. Key budget/usage routes documented around `/api/v1/key/budget` and `/api/v1/key/usage/*`.
- A routing policy is created in the dashboard and sent as the `model` name. `Otari-Model` and `Otari-Fallback` response headers show what served the call.
- An account (and a workspace token) is required for a live run. This repo ships a labeled **MOCK** of that same interface when no token is present.

## Prizes

- 1st: $1,000 + 3 hours with Mozilla.ai engineers
- 2nd: $200 + 2 hours with Mozilla.ai engineers
- 3rd: 1 hour with Mozilla.ai engineers
