# Backend-Backed Couch Flow Slice 4 Validation

Date: 2026-06-30.

Slice: Prove Backend-Backed Local Couch Flow.

## Scope

This validation proved the local backend-backed couch flow against isolated SQLite storage.

It did not use live provider calls, live poster providers, live critic-score providers, LLM behavior, or persistent household data.

## API Smoke

`python3 scripts/couch_flow_smoke.py` passed.

The smoke used a temporary SQLite database under the system temp directory.

It seeded setup data and completed onboarding for both participants.

It created a shared session with five shortlist items.

It submitted the first participant reaction pass.

It exercised the handoff transition.

It submitted the second participant reaction pass.

It verified reranked state, reranked source ids, and best pick.

It saved a `watched_recommended` session outcome.

It saved post-watch feedback for both participants.

It verified debug history included the persisted outcome and both feedback rows.

## Backend-Backed Mobile Smoke Command

`MOBILE_UX_SMOKE_EXPECT_API=1 pnpm smoke:ux:mobile` now starts FastAPI against an isolated temporary SQLite database.

It seeds onboarding through the API.

It builds and starts the local web app against the temporary API.

It remains blocked at browser startup in this agent environment because Brave exits with `SIGABRT` before exposing a DevTools endpoint.

That browser startup failure matches the Slice 2 environment blocker and is not treated as a product-flow failure here.

## Backend-Backed Browser Fallback

Fallback validation used the in-app browser at a 390 by 844 viewport against a local web server connected to an isolated SQLite database at `/private/tmp`.

The flow created a real backend session.

It recorded five first-pass reactions.

It advanced through handoff.

It recorded five second-pass reactions.

It reached the results screen with a best pick and reranked backups.

It saved a `watched_recommended` outcome from the result screen.

It saved post-watch feedback for both participants.

Recent session history returned the persisted reranked session, watched-recommended outcome, and both feedback rows.

Debug history returned five shortlist items, five founder reactions, five wife reactions, best pick `arrival`, the persisted outcome, and both feedback rows.

Debug history only listed `recommendation_scoring_request` as unavailable evidence in this backend-backed UI run.

## Open Follow-Up

Rerun `MOBILE_UX_SMOKE_EXPECT_API=1 pnpm smoke:ux:mobile` from a normal local browser environment where Chromium can expose DevTools.

If it still fails there, treat the failure as a product or smoke-script issue.
