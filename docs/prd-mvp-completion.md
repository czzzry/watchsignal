# PRD - MVP Completion

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
- Browser smoke validation is blocked inside the current sandbox by macOS browser startup restrictions, not by known app code failure.

## Remaining MVP Issues

### 1. Accepted UI refactor needs final local browser proof

The refactor branch preserves the accepted design and has passed TypeScript, production build, API compile, and partial backend validation.
The final phone-sized browser smoke still needs to run in a normal local browser environment.
This is a release-readiness issue, not a product feature.

### 2. Demo shortlist fixture contract drift

The backend demo fixture now uses accepted real movie IDs such as `arrival`, `knives-out`, `the-grand-budapest-hotel`, `edge-of-tomorrow`, and `past-lives`.
Before Slice 1, several backend tests and docs still asserted older synthetic IDs such as `fixture:shared-time-loop`.
Slice 1 aligns the fixture-facing tests and API contract docs to the accepted demo IDs so future failures can point to real regressions.

### 3. Demo data provenance must be explicit

The mobile demo uses local poster assets and hard-coded critic score values.
The local demo does not have a live poster provider or live critic-score provider wired into the flow.
The MVP must be honest about this in code, docs, tests, and any visible UI copy that could otherwise imply sourced real-time data.
Slice 3 keeps the accepted flow visually unchanged while making poster, critic-score, descriptive-copy, API-payload, fallback, and unavailable-field provenance explicit in code-facing and doc-facing surfaces.

### 4. Backend-backed local happy path needs one clean gate

The app has a demo-safe UI path and a backend-backed local path.
MVP completion needs one documented command path that proves setup, shared session, reactions, handoff, rerank, outcome, feedback, and debug history against isolated local storage.
This should avoid real household data and avoid external network calls.

### 5. MVP source-of-truth docs need a completion layer

The repo contains older n8n and Telegram-oriented MVP docs as historical guidance.
The code-first app has since settled on local mobile web.
MVP completion needs a short current layer that explains what remains, what is deliberately deferred, and what the first implementation slice should be.

### 6. Live candidate and provider integration remains a separate MVP readiness question

Existing architecture docs say live TMDb is required before the app is considered usable outside demo mode.
The current completion plan does not hide that requirement.
It separates the immediate local-demo tie-up from the larger live-candidate-provider work.
For this completion pass, MVP closure means a demo-complete local mobile web baseline with honest fixture provenance and validated backend-backed local storage.
Live candidate sourcing remains required before the app is called live-usable outside fixture/demo mode.
That live candidate sourcing work is a next MVP readiness phase, not MVP plus 1 LLM work.
Poster provider integration, critic-score provider integration, and richer availability verification are not part of the UI refactor cleanup.

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
- The phone-sized UX smoke command is documented and runnable in a normal local browser environment.
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

Start with the fixture and test contract alignment slice.
It is the cleanest AFK slice because it fixes a known validation failure without changing product behavior or visual design.
After that, run the local validation gate and only then touch demo provenance or live-provider scope decisions.
