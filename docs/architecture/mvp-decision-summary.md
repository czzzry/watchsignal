# MVP Decision Summary

This file summarizes the narrowed grill decisions for the code-first app.
Inherited product decisions from the carried-over docs stand unless this file or a future ADR says otherwise.

## Product Shape

- The product remains a private household Movie Night Mediator.
- The MVP must support the shared couple use case.
- Pass-the-phone is the first shared input mode.
- Separate-phone use is MVP plus N unless it is cheap to add safely.
- The UI should be a polished mobile wizard flow, not a dashboard or chat clone.

## Interface And Runtime

- The MVP interface is a local mobile web app.
- The app should run on a laptop and be opened from a phone on the same local network.
- Hosted web is a likely later step.
- Native mobile is only a later option if web or PWA becomes limiting.
- Telegram remains a possible later adapter.

## Technical Shape

- Use a single monorepo.
- Use `apps/web` for the Next.js phone UI.
- Use `apps/api` for the FastAPI backend and Python recommendation core.
- Use SQLite as the MVP source of truth.
- Use `uv` for Python dependency management.
- Use `pnpm` for frontend dependency management.
- Use pragmatic REST APIs with FastAPI-generated OpenAPI contracts.

## Recommendation Shape

- MVP ranking should use Safe Picks by default.
- A Safe Pick is Prime Video Germany, language-compatible, constraint-compatible, and not already watched unless rewatches are allowed.
- Needs Quick Check items may be shown separately but should not be the main recommendation.
- Amazon DE access may be flatrate, rent, or buy as long as the title otherwise passes the active filters.
- Foreign-language titles should be Needs Quick Check unless English subtitles are verified by another source or manual correction.
- Manual verified-watchable corrections should be stored so practical availability can improve over time.
- The shortlist should show five titles.
- Include one interesting Safe Pick when possible.
- Score watchability first, taste second, and session mode third.
- Keep weights and scoring behavior tunable.

## Onboarding And Data

- Use configurable household profiles with Husband and Wife as defaults.
- Use minimal onboarding plus a tiny hard-constraint interview.
- Allow low-polish manual watched-history backfill.
- Resolve seed and backfill titles through TMDb when possible.
- Allow unresolved plain-text titles when lookup is annoying or fails.

## Future Lanes

- LLM interpretation is MVP plus 1.
- The MVP should store structured feedback and free-text notes so LLM interpretation has useful inputs later.
- A future recommender-evaluation agent can use fixtures, household feedback, and appropriate public datasets to compare scorers against held-out ratings.
- GNHF should wait until the monorepo has bounded issues, validation commands, and clean worktree rules.
