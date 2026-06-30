# PRD - Code-First Movie Night Mediator MVP

## Problem Statement

The founder wants a private household tool that helps two people decide what to watch with less friction and better outcomes over time.
The n8n version established the product shape, but this repo exists to build the same intent as normal application code.
The founder wants a recommendation engine usable from a phone on the couch, without relying on n8n.
The MVP must support the shared couple use case, not only solo viewing.
The implementation should be scoped and documented so autonomous agents can take bounded work without the founder babysitting every step.

## Solution

Build a local mobile web app for Movie Night Mediator.
The app runs on the founder's laptop and is opened from a phone on the same local network.
The primary MVP interaction mode is pass-the-phone.
The founder starts a shared movie-night session, reacts to a five-title shortlist, hands the phone to the second participant, and then the app reranks the shortlist and recommends a best pick.

The implementation uses a Next.js frontend, a FastAPI backend, SQLite persistence, TMDb metadata, and a replaceable Python scoring module.
The current MVP completion pass may close a local demo-complete baseline before live TMDb candidate sourcing exists.
The app should use live TMDb candidate sourcing before it is considered live-usable outside fixture/demo mode.
Fixture candidates remain valuable for tests and autonomous-agent work.
The app should recommend Safe Picks by default and show uncertain options only as Needs Quick Check.
Safe Picks must not overclaim provider-specific audio or subtitle certainty that TMDb cannot prove.

The repo should preserve learning artifacts, diagrams, API contracts, and agent-ready issue boundaries.
Pocock-style skills shape the work into PRDs and vertical slices.
Kun Cheng GNHF can later execute bounded issues once each issue has clear ownership, stop conditions, and validation commands.

## User Stories

1. As the founder, I want this repo to remain separate from the n8n project, so that the code-first implementation can evolve without changing n8n decisions.
2. As the founder, I want inherited product decisions to stand unless the code-first architecture creates a true gap, so that we do not re-litigate settled scope.
3. As the founder, I want to run the app locally and open it on my phone, so that I can use it on the couch without deployment work.
4. As the founder, I want the MVP to support shared couple recommendations, so that the app solves the real household problem.
5. As the founder, I want pass-the-phone to be the primary MVP input mode, so that my wife can participate with minimal friction.
6. As the founder, I want separate-phone participation to stay possible later, so that the app can become more friction-free after the core flow works.
7. As a household user, I want the app to use configurable household profiles with generic defaults, so that the experience is understandable without committing real names.
8. As a household user, I want the app to default to movie mode, so that common sessions start quickly.
9. As a household user, I want the app to remember common defaults, so that repeated setup stays light.
10. As a household user, I want Prime Video Germany to be treated as the normal availability constraint, so that recommendations are watchable in our real context.
11. As a household user, I want English audio or verified English subtitles to be respected, so that the shortlist avoids unusable titles.
12. As a household user, I want the app to avoid already-watched titles by default, so that it does not waste shortlist space.
13. As a household user, I want onboarding before real recommendations, so that the first shortlist is not based on an empty taste model.
14. As a household user, I want onboarding to focus on real seed titles, so that taste learning begins from actual examples.
15. As a household user, I want a tiny hard-constraint interview, so that strong exclusions such as horror intolerance are captured early.
16. As a household user, I want the app to resolve seed titles through TMDb when possible, so that the scoring engine gets useful metadata.
17. As a household user, I want the app to allow unresolved title entries when matching is annoying, so that onboarding is not blocked by lookup friction.
18. As a founder, I want a low-polish manual backfill path, so that I can add watched-history data without waiting for a beautiful UX.
19. As a household user, I want live TMDb metadata in the MVP, so that the app can recommend real titles rather than fixture-only examples.
20. As a household user, I want the app to distinguish Safe Picks from Needs Quick Check titles, so that I know which recommendations are truly ready for tonight.
21. As a household user, I want Amazon rent or buy availability not to be confused with Prime subscription availability, so that recommendations do not create surprise costs.
22. As a household user, I want foreign-language titles without verified English subtitles to appear only as Needs Quick Check, so that the main recommendation stays trustworthy.
23. As a household user, I want to manually correct watchability errors, so that practical Prime Germany knowledge improves over time.
24. As a household user, I want a five-title shortlist, so that there is enough variety without making pass-the-phone feel like homework.
25. As a household user, I want one interesting safe pick when possible, so that the recommender does not become boring.
26. As a household user, I want quick reactions using Interested, Maybe, No, and Seen, so that the app can learn tonight-level intent.
27. As a household user, I want each person to react separately, so that the app does not collapse two taste profiles into one.
28. As a household user, I want the app to rerank after both reaction passes, so that the final pick reflects current intent.
29. As a household user, I want a best pick plus reranked shortlist, so that we get a clear answer without losing choice.
30. As a household user, I want the app to capture what we actually watched, so that recommendations can improve from outcomes.
31. As a household user, I want post-watch feedback to use Loved, Fine, and No, so that feedback stays lightweight.
32. As a household user, I want optional free-text notes stored from day one, so that MVP plus 1 can interpret richer feedback later.
33. As the founder, I want the first scoring engine to be simple and tunable, so that early bad recommendations can be fixed without rewriting the app.
34. As the founder, I want scoring to prioritize watchability first, taste second, and session mode third, so that the app remains practical and mode-aware.
35. As the founder, I want husband-first, wife-first, and compromise modes, so that session intent shapes the ranking.
36. As the founder, I want compromise mode to protect against strong dislike, so that compromise does not become bland averaging.
37. As the founder, I want a visible history of sessions and outcomes, so that I can tell whether the app is learning.
38. As the founder, I want deeper internal session artifacts stored, so that debugging and later evaluation have evidence.
39. As the founder, I want LLM interpretation kept out of MVP, so that the first build stays focused.
40. As the founder, I want LLM interpretation planned for MVP plus 1, so that free-text feedback can become useful later.
41. As the founder, I want future recommender-evaluation work to compare scorers against fixed test sets, so that ranking improvements are evidence-based.
42. As the founder, I want meaningful UI work to produce reviewable visual artifacts when useful, so that I can react to direction without blocking every step.
43. As the founder, I want learning artifacts after meaningful changes, so that I understand the system without interrupting autonomous work.
44. As the founder, I want GitHub issues to become the source of implementation slices, so that agents can work from clear tasks.
45. As the founder, I want GNHF tasks to have stop conditions, validation commands, and file ownership, so that autonomous runs stay bounded.
46. As an autonomous agent, I want issue briefs to identify owned and off-limits files, so that I can make progress without colliding with other agents.
47. As an autonomous agent, I want validation commands documented, so that I can prove my slice works before stopping.
48. As the founder, I want real household ratings, notes, identifiers, and watch history to stay local, so that committed artifacts remain safe.
49. As the founder, I want public movie metadata to be allowed in fixtures, so that tests remain understandable without exposing private household data.
50. As the founder, I want setup blockers documented, so that AFK work does not stall on missing credentials or decisions.

## Implementation Decisions

- The MVP is a local mobile web app, not a Telegram bot.
- Telegram remains a possible later adapter.
- The codebase is a monorepo.
- `apps/web` contains the Next.js phone UI.
- `apps/api` contains the FastAPI backend, SQLite persistence, and Python recommendation core.
- SQLite is the MVP source of truth.
- TMDb is the first metadata source.
- Live TMDb candidate sourcing is required before the app is considered live-usable outside fixture/demo mode.
- Local demo-complete MVP closure can happen first when it is clearly labeled as fixture-backed.
- Live poster provider integration is separate from live candidate sourcing.
- Live critic-score provider integration is separate from live candidate sourcing.
- Richer live availability verification is separate from live candidate sourcing.
- Fixture candidates remain available for tests, local demos, and agent work.
- The app uses pragmatic REST APIs with FastAPI-generated OpenAPI contracts.
- FastAPI/Pydantic models are the source of truth for API request and response schemas.
- The UI should be a polished mobile wizard flow.
- Pass-the-phone is the primary MVP input mode.
- Separate-phone mode is MVP plus N unless it is cheap to add safely.
- Household profiles are configurable with Husband and Wife as committed defaults.
- Seed and backfill title resolution is hybrid.
- The app tries TMDb resolution immediately and allows unresolved text fallback.
- The main recommendation pool uses Safe Picks.
- Needs Quick Check titles can be visible separately but should not become the main recommendation by default.
- Amazon Video rent or buy is not equivalent to Prime Video subscription availability.
- Foreign-language titles require verified English subtitles before becoming Safe Picks.
- Manual verified-watchable corrections should be stored.
- The shortlist has five titles.
- One slot should be available for an interesting Safe Pick when possible.
- Scoring remains behind a replaceable module boundary.
- V1 scoring is heuristic, tunable, and mode-aware.
- V1 scoring prioritizes watchability first, taste second, and session mode third.
- Optional free-text notes are stored in MVP but interpreted in MVP plus 1.
- LLM interpretation is not in MVP.
- LLM ranking authority is out of scope for MVP.
- Future recommender experiments should compare scorer changes against fixed test sets.
- Real household data stays out of committed fixtures and docs.
- Public movie metadata may appear in committed fixtures.
- GNHF should not run on broad goals.
- GNHF-ready issues must include ownership boundaries, stop condition, validation commands, and expected learning artifact.

## Testing Decisions

- Tests should verify public behavior through high-level seams rather than internal formula steps.
- API tests should verify route behavior and OpenAPI contract shape.
- Persistence tests should verify that sessions, profiles, reactions, outcomes, and feedback survive round trips through SQLite.
- TMDb adapter tests should use fixtures or controlled fakes for repeatability.
- A separate smoke test can verify local credentials against live TMDb without printing secrets.
- Safe Pick gate tests should cover provider buckets, Amazon rent or buy, original language, foreign-language uncertainty, already-watched filtering, and manual watchability corrections.
- Scoring tests should verify observable ranking behavior under husband-first, wife-first, and compromise modes.
- Pass-the-phone tests should verify state transitions from founder reaction pass to wife reaction pass to reranked result.
- Frontend tests should focus on wizard flow behavior once the UI has real screens.
- Visual UI review should use Lavish or another reviewable artifact for meaningful screens or design alternatives.
- The baseline validation commands are the API test suite, API compile check, and Next.js production build.
- GNHF work should stop only after the relevant validation command passes and no unrelated files were changed.

## Out of Scope

- Public product release.
- Native mobile app.
- Hosted deployment.
- Telegram MVP implementation.
- Separate-phone shared sessions unless cheap to add safely.
- Full account/auth system.
- Production-grade availability provider integration beyond TMDb.
- Perfect provider-specific audio or subtitle verification.
- LLM-assisted feedback interpretation.
- LLM ranking authority.
- Sophisticated recommender research.
- Deep taste profile visualization.
- Rich analytics dashboard.
- Multi-household public app behavior.
- Real household data in committed fixtures.
- Autopreso for MVP app implementation.

## Further Notes

The carried-over n8n PRD remains useful source material.
This file is the implementation PRD for the code-first app.

Pocock-style skills should be used to shape PRD and issue boundaries.
Kun Cheng GNHF should be used only after those boundaries are concrete enough for autonomous execution.

The first GNHF trial should be intentionally tiny and run in Companion mode.
The host agent should independently verify GNHF output before treating it as accepted.

## Proposed Test Seams

Before turning this PRD into implementation issues, confirm these seams:

- API contract seam: FastAPI routes and OpenAPI schemas.
- SQLite persistence seam: repository behavior over local database state.
- TMDb adapter seam: title search, movie detail, provider data, and controlled test fixtures.
- Safe Pick gate seam: watchability and language compatibility classification.
- Scoring seam: replaceable scorer contract and observable ranking behavior.
- Pass-the-phone state seam: session state transitions through both reaction passes.
- Mobile wizard seam: user-visible flow from setup to recommendation to feedback.
- Agent execution seam: issue-level owned files, off-limits files, stop condition, validation command, and learning artifact.
