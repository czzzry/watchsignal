# PRD - MVP+6 MVP Readiness Reconciliation

## Problem Statement

The accepted cinematic pass-the-phone UI now shows the intended local mobile web experience.
The remaining MVP work should tie that experience to a clean, honest, testable product baseline before MVP plus 1 planning begins.
The current risk is not that the flow is unclear.
The current risk is that demo fixture data, backend tests, validation gates, and source-of-truth docs are slightly out of sync after the recent UI work.

## Completion Objective

Finish the code-first MVP baseline as a local mobile web pass-the-phone app that can be tested on a phone and trusted as either demo mode or backend-backed local mode.
Preserve the accepted UI direction from checkpoint `13835d0`.
Do not roll back to the older approved design checkpoint `ab5568f`.
Do not introduce LLM interpretation, hosted deployment, Telegram, separate-phone shared sessions, paid providers, or production account behavior.

## Current Accepted State

- The accepted visual checkpoint is `13835d0`.
- The current local flow has Launch, Setup, Reaction, Handoff, and Results screens.
- The current interface target is local mobile web.
- Pass-the-phone is the primary shared-session interaction.
- The UI can continue in demo mode when the local API is unavailable.
- The backend already has session, reaction, outcome, feedback, history, setup, onboarding, scoring, and fixture-backed shortlist seams.
- A behavior-preserving UI refactor exists on `codex/cinematic-pass-phone-refactor`.
- Accepted MVP+3 and MVP+4 gates already proved real phone-sized dogfood coverage.
- Current sandbox browser smoke remains vulnerable to macOS browser startup restrictions, not known app code failure.

## Remaining MVP Issues

### 1. Source-of-truth docs still need reconciliation

The repo contains older MVP-completion language that predates the accepted MVP+3 through MVP+5 validation trail.
That stale language can make already-proven flow coverage sound hypothetical.
The remaining cleanup work is largely about making the docs match the accepted validation record and the current product rules.

### 2. Amazon DE watchability policy is now broader than older docs assumed

The current product decision is that Amazon DE access counts whether the title is flatrate, rental, or purchase, as long as it still passes the active language and watched-state rules.
Several older docs and tests had assumed a subscription-only interpretation.
MVP+6 brings those tests, fixtures, and decision docs back into sync.

### 3. Live-usable MVP now hinges on environment-independent browser confirmation

The product flow itself has already been exercised through accepted dogfood gates and passing backend-backed validation.
What remains is not an observed product-flow defect.
What remains is deciding whether one final normal-browser or real-phone rerun outside the current sandbox is still required before the repo declares the live-usable MVP gate fully closed.

## User Stories

1. As the founder, I want the accepted cinematic UI direction preserved, so that refactor work does not reopen the visual decision.
2. As the founder, I want the local demo to be honest about fixture data, so that demo confidence does not depend on pretending local assets are live provider data.
3. As the founder, I want backend tests to reflect the accepted candidate set, so that failing tests point to real problems.
4. As the founder, I want one local phone-sized validation path, so that MVP readiness can be checked without guesswork.
5. As an autonomous agent, I want bounded vertical issues, so that MVP cleanup can proceed without drifting into MVP plus 1.
6. As an autonomous agent, I want explicit non-goals, so that no live provider or LLM work sneaks into fixture cleanup.

## Acceptance Criteria

- The accepted cinematic pass-the-phone visual direction is unchanged.
- The API and web demo candidate contracts agree on IDs, ranking, safe-pick labels, provider labels, poster provenance, and score provenance.
- The API unit test suite passes or has only separately documented environmental failures.
- The web production build passes.
- The API compile check passes.
- The phone-sized UX smoke command is documented, and sandbox browser failures are distinguished from observed product-flow failures.
- Demo mode clearly remains fixture-backed.
- Backend-backed local mode writes only to isolated local storage during smoke validation.
- MVP plus 1 work is not included in MVP completion issues.

## Non-Goals

- No LLM interpretation.
- No LLM ranking authority.
- No hosted deployment.
- No Telegram MVP surface.
- No separate-phone shared-session product work.
- No live critic-score provider in this completion pass.
- No live poster provider in this completion pass.
- No paid provider integration.
- No production account or auth system.
- No visual redesign away from `13835d0`.
- No rollback to `ab5568f`.
- No private household data in committed fixtures.

## Validation Commands

Run these from the repo root unless a command says otherwise.

```sh
pnpm check
```

```sh
pnpm build:web
```

```sh
pnpm smoke:ux:mobile
```

For the backend-backed local flow:

```sh
MOBILE_UX_SMOKE_EXPECT_API=1 pnpm smoke:ux:mobile
```

If the browser smoke cannot run inside an agent sandbox, run it from a normal local terminal and record the result in the implementing issue.

## Risk Areas

- Updating fixture IDs can accidentally change ranking expectations rather than only updating tests.
- Removing or relabeling critic scores can change the accepted visual balance if done visibly.
- Swapping poster URLs between local assets and remote URLs can change screenshot appearance and offline behavior.
- Tightening demo provenance copy can make the UI feel less polished if it is placed in the main flow.
- Running backend-backed smoke against the wrong database could mutate real local state.
- Treating live TMDb provider work as a tiny cleanup task would make the MVP completion pass too broad.

## Recommended First Slice

Start with doc and contract reconciliation against the accepted validation trail.
That keeps later implementation slices grounded in current truth rather than stale intermediate assumptions.
