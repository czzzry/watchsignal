# Workflow Map

This file maps likely workflow boundaries without implementing them yet.
It now reflects the founder decisions currently recorded in [decision-register.md](decision-register.md).
This is still a planning artifact, not an implementation artifact.

## Current status

- No production workflows exist yet
- No workflow JSON has been created yet
- No triggers, credentials, or external integrations have been configured

## First vertical slice

The first vertical slice is a complete movie-night flow with real feedback learning.

- Required onboarding for at least one user before solo recommendations
- Both users onboarded before true shared or compromise mode
- Telegram session start
- Shared or solo audience selection
- Shared-session mode selection with visible default and quick override
- Candidate retrieval from TMDb
- Scoring through a separate module called by n8n
- Shortlist delivery with posters and explanation blurbs
- Per-person shortlist reactions using Interested or Maybe or No
- Visible reranked shortlist plus a strong recommended pick and a pick-for-us option
- Outcome capture on the next interaction
- Post-watch feedback using Loved or Fine or No
- Session artifacts, watched history, and metrics written to Google Sheets

## Candidate workflow boundaries

| Workflow area | Purpose | Depends on decisions |
|---|---|---|
| Onboarding | Capture seed titles, watched history, and a few hard constraints | Feedback mechanism, storage layer |
| Intake | Start a movie-night session and capture who is watching and the session mode | Interface platform, recommendation method |
| Clarification | Ask only the minimum session questions needed for a credible shortlist | Interface platform, LLM role |
| Candidate fetch | Retrieve candidate titles and artwork from TMDb | Movie data source, deployment model |
| Scoring | Produce per-user and session-mode-aware shortlist ranking | Recommendation method, couple consensus rule, n8n vs code boundary |
| Shortlist reactions | Capture Interested or Maybe or No, skips, and already-seen corrections | Interface platform, feedback mechanism |
| Recommendation handoff | Show reranked shortlist, strong recommended pick, and pick-for-us action | Interface platform, couple consensus rule |
| Outcome capture | Ask what was actually watched or whether nothing was watched | Feedback mechanism, storage layer |
| Post-watch feedback | Record per-person Loved or Fine or No and optional free-text | Feedback mechanism, LLM role |
| Taste updates | Update watched history, profile signals, and metrics | Storage layer, recommendation method |
| History and profile | Show lightweight recent history and later profile snapshots | Repo/public portfolio strategy, privacy model |

## Interaction notes

- When implementation begins, keep orchestration boundaries small and inspectable
- Optimize separate-device use first, but keep pass-the-phone working in MVP
- Defaults should be remembered, visible, and easy to override
- Keep most session artifacts internal, but expose a lightweight user-facing history
- Do not bury scoring logic inside workflow nodes if it is expected to evolve significantly

## Diagram links

- System and flow diagrams live in [architecture-overview.md](architecture-overview.md)
