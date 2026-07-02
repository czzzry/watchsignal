# MVP Plus 2 Issue Breakdown

This issue set breaks [docs/prd-mvp-plus-2.md](../prd-mvp-plus-2.md) into bounded vertical slices.
It has been published to GitHub Issues as the locked MVP Plus 2 tracker.

## Current MVP Phase

MVP Plus 2 is **Memory, Steering, And Rich Recommendation Intelligence**.

Current tracker:

```text
[░░░░░░░░░░░░░░░░░░░░] 0/12 issues done
```

The issue count is twelve.
New work discovered during execution should be classified as in-scope risk closure, a scope-change candidate that needs founder approval, or next-phase backlog.

## GitHub Tracker

Parent PRD issue:

- #47 - PRD - MVP Plus 2 Memory, Steering, And Rich Recommendation Intelligence

Implementation and acceptance slices:

- #48 - MVP+2 Slice 1 - MVP Plus 2 Contracts For Parallel Work
- #49 - MVP+2 Slice 2 - Profile Labels And Lightweight Avatars
- #50 - MVP+2 Slice 3 - Shared Household Watchlist
- #51 - MVP+2 Slice 4 - App-Owned Watched And Rating Actions
- #52 - MVP+2 Slice 5 - Profile Memory Panel
- #53 - MVP+2 Slice 6 - Tonight Intent Interpreter
- #54 - MVP+2 Slice 7 - Tonight Intent Setup And Confirmation UI
- #55 - MVP+2 Slice 8 - Show 5 More Session Continuation
- #56 - MVP+2 Slice 9 - Steer Next 5
- #57 - MVP+2 Slice 10 - Hybrid Candidate Enrichment Pipeline
- #58 - MVP+2 Slice 11 - Rich Recommendation Scoring And Evidence
- #59 - MVP+2 Slice 12 - MVP Plus 2 Evaluation And Acceptance Gate

## Phase Promise

WatchSignal has memory and taste steering, not just a one-night flow.

The phase is done only when both are true:

- The phone-sized app flow proves profile setup, watchlist, Show 5 more, Steer next 5, and profile memory work together.
- The recommendation-quality report proves richer profile and enrichment evidence changed ranking behavior in reviewable ways.

## Slice 1 - MVP Plus 2 Contracts For Parallel Work

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: None
- User stories covered: 1, 2, 3, 28, 30, 39, 40, 49, 50
- Primary goal: lock the data and API contracts that let Treehouse workers parallelize the phase safely.

### What to build

Define the MVP Plus 2 contracts for profile identity, shared watchlist, profile memory summary, tonight intent interpretation, session continuation, candidate enrichment, scoring evidence, and evaluation coverage.
This slice should create or update docs and contract tests at the highest useful seam.
It should not build every feature.
It should give later workers stable shapes to implement against.

### Acceptance criteria

- [ ] Profile identity contract includes labels and lightweight avatar or color identity.
- [ ] Watchlist contract supports shared household ownership, optional saved-by profile, remove behavior, and no automatic taste boost.
- [ ] Intent contract supports direct confirmation, clarification-required output, structured filters, soft signals, confidence, and deterministic fallback.
- [ ] Session continuation contract distinguishes Show 5 more from Steer next 5.
- [ ] Enrichment contract supports TMDb-only fallback and MovieLens or feature-enriched candidates.
- [ ] Scoring evidence contract can identify genre, title similarity, feature/tag, session reaction, tonight intent, and fallback signals.
- [ ] Evaluation contract can report enrichment coverage and rank deltas.
- [ ] Contract tests or schema-level tests prove the most important shapes.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when parallel workers can build against the same contracts without inventing incompatible payloads.

### Risk notes

Keep this slice thin.
Do not let it become the full implementation.

## Slice 2 - Profile Labels And Lightweight Avatars

- Type: AFK with HITL visual review if the setup UI changes materially
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 1
- User stories covered: 4, 5, 6, 7, 17, 18
- Primary goal: make the two household profiles feel recognizable without redesigning onboarding.

### What to build

Let the user rename the two profiles and choose lightweight avatars or profile colors.
Persist that identity and use it consistently in the pass-the-phone flow, saved-by attribution, and memory surfaces where available.
This slice should not add photo upload or rebuild onboarding.

### Acceptance criteria

- [ ] Users can edit profile labels from the setup path.
- [ ] Users can choose from a small built-in avatar or color set.
- [ ] Profile identity persists locally.
- [ ] The pass-the-phone flow uses the saved profile labels and avatar or color identity.
- [ ] Taste Lab remains out of the visible setup flow.
- [ ] Tests cover persistence and API or UI contract behavior.
- [ ] A production web build passes if UI files are touched.

### Validation commands

```sh
pnpm check
```

```sh
pnpm build:web
```

### Stop condition

Stop when profile identity is saved and visible enough for later watchlist, memory, and session work.

### Risk notes

Do not turn this into a full onboarding redesign.

## Slice 3 - Shared Household Watchlist

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 1
- User stories covered: 8, 9, 10, 11, 12, 13
- Primary goal: make save-for-later real as a shared household watchlist.

### What to build

Add a shared household watchlist that can save app-owned movie candidates, list saved movies, remove saved movies, and record who saved an item when the active profile is known.
Saving should not become an automatic taste signal or scoring boost.
The watchlist should be visible enough that a saved movie can be found later.

### Acceptance criteria

- [ ] A movie from the shared flow can be saved for later.
- [ ] Saved movies appear in a shared household watchlist.
- [ ] Saved movies can be removed.
- [ ] The data model records optional saved-by profile identity when known.
- [ ] Saving the same movie twice does not create confusing duplicates.
- [ ] Saved-for-later does not change recommendation scoring in this slice.
- [ ] Tests cover save, list, remove, duplicate handling, and optional saved-by attribution.

### Validation commands

```sh
pnpm check
```

```sh
pnpm build:web
```

### Stop condition

Stop when the save button is real, removable, and no longer a fake UI affordance.

### Risk notes

Do not overload saved-for-later with taste semantics yet.

## Slice 4 - App-Owned Watched And Rating Actions

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 1
- User stories covered: 14, 15, 16, 17, 18
- Primary goal: keep lightweight watched and rating actions for movies already surfaced by WatchSignal, without adding a competing manual backfill flow.

### What to build

Let users mark a recommended, saved, or historical movie as watched and optionally rate it with the existing simple feedback language.
This should reuse the app's outcome, feedback, and watched-history concepts where practical.
It should not create an arbitrary title-entry backfill tool.

### Acceptance criteria

- [ ] App-owned movies can be marked watched from at least one existing surface.
- [ ] A watched app-owned movie can receive a simple profile-specific rating when relevant.
- [ ] The behavior updates existing watched-history or feedback records where appropriate.
- [ ] No separate manual backfill search flow is introduced.
- [ ] Taste Lab remains the future intentional calibration and bulk rating service.
- [ ] Tests cover watched and rating persistence for app-owned movies.

### Validation commands

```sh
pnpm check
```

```sh
pnpm build:web
```

### Stop condition

Stop when WatchSignal can remember watched or rated movies it already showed to the user.

### Risk notes

Avoid duplicate learning paths that compete with Taste Lab.

## Slice 5 - Profile Memory Panel

- Type: AFK with HITL visual review if the panel becomes prominent
- Suggested labels: `ready-for-agent`
- Blocked by: Slices 2, 3, and 4
- User stories covered: 19, 20, 21, 41
- Primary goal: make WatchSignal's memory visible without building a full taste profile dashboard.

### What to build

Add a small profile memory panel that shows practical memory indicators such as saved-for-later count, recent reactions, watched or rated count, and simple taste signals.
The panel may use Taste Lab-derived profile evidence when available, but it must not expose Taste Lab as a main app flow.

### Acceptance criteria

- [ ] Each profile has a small memory summary.
- [ ] The summary includes saved count, recent reactions or ratings, watched or rated count, and simple taste signals where available.
- [ ] The panel distinguishes visible app memory from private Taste Lab calibration where needed.
- [ ] The panel does not become a full taste dashboard.
- [ ] Tests cover the memory summary read model.
- [ ] A phone-sized UI check confirms the panel does not clutter the main flow.

### Validation commands

```sh
pnpm check
```

```sh
pnpm build:web
```

### Stop condition

Stop when memory is visible enough to prove the app remembers, without overbuilding analytics.

### Risk notes

The future full profile dashboard stays out of scope.

## Slice 6 - Tonight Intent Interpreter

- Type: AFK, with live LLM smoke optional
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 1
- User stories covered: 22, 23, 24, 25, 26, 27, 28, 29, 30, 35, 36
- Primary goal: turn human tonight-level language into confirmed, structured intent without giving the LLM ranking authority.

### What to build

Build a narrow intent interpreter that accepts user text and returns structured filters, soft signals, confidence, confirmation text, or one clarification question.
Concrete requests can go straight to confirmation.
Ambiguous emotional intent should ask one short clarification.
The implementation must support deterministic fake behavior for tests and local validation.
Live LLM behavior can sit behind the same contract when credentials are present.

### Acceptance criteria

- [ ] The interpreter maps concrete requests such as 90s movies into structured filters.
- [ ] The interpreter maps person or franchise requests into structured constraints where possible.
- [ ] Ambiguous emotional requests return a clarification question before candidate generation.
- [ ] The response includes confirmation text for direct intent.
- [ ] The interpreter has deterministic test behavior.
- [ ] Live LLM use is isolated behind the same contract and is optional for required tests.
- [ ] The interpreter never returns final rankings.

### Validation commands

```sh
pnpm check
```

Optional live smoke when credentials and network are available:

```sh
python3 scripts/check_llm_intent_smoke.py
```

### Stop condition

Stop when messy user language can become reviewable structured intent without depending on live calls for normal validation.

### Risk notes

Do not let this become open-ended chat.

## Slice 7 - Tonight Intent Setup And Confirmation UI

- Type: HITL for interaction review, AFK for implementation
- Suggested labels: `ready-for-agent`
- Blocked by: Slices 1 and 6
- User stories covered: 22, 23, 24, 25, 26, 27, 30, 36
- Primary goal: let the user enter tonight-level intent and confirm or clarify it before candidate generation.

### What to build

Add the user-facing tonight intent entry point to the shared flow.
The UI should let a user type normal language, review the app's interpretation, answer one clarification when needed, and apply the confirmed intent to candidate generation.
The feature should feel like steering the night, not editing a permanent profile.

### Acceptance criteria

- [ ] The shared flow has a natural-language tonight intent entry point.
- [ ] Direct interpretations show a concise confirmation before applying.
- [ ] Ambiguous emotional intent shows one short clarification.
- [ ] Confirmed intent is visible as active tonight context.
- [ ] The UI distinguishes tonight context from durable taste profile.
- [ ] A phone-sized click-through covers direct confirmation and clarification paths.
- [ ] Production web build passes.

### Validation commands

```sh
pnpm check
```

```sh
pnpm build:web
```

### Stop condition

Stop when the user can steer tonight in human language and see what the app understood.

### Risk notes

Do not make this a general chat surface.

## Slice 8 - Show 5 More Session Continuation

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 1
- User stories covered: 31, 32, 33, 47
- Primary goal: replace Start over with a continuation path that preserves useful session signal.

### What to build

Add **Show 5 more** behavior to the shared flow.
It should preserve prior reactions, avoid already-shown movies, keep active tonight intent, and generate a new batch in the same movie-night context.
This should feel like continuation, not a destructive restart.

### Acceptance criteria

- [ ] The primary weak-shortlist escape action is Show 5 more, not Start over.
- [ ] Prior session reactions are preserved.
- [ ] Already-shown movies are excluded from the next batch.
- [ ] Active tonight intent stays applied.
- [ ] The session history or evidence surface can show multiple batches or enough continuation evidence.
- [ ] Tests cover preservation, exclusion, and continuation behavior.
- [ ] A production web build passes if UI is touched.

### Validation commands

```sh
pnpm check
```

```sh
pnpm build:web
```

### Stop condition

Stop when a user can ask for five more without losing the signal they just created.

### Risk notes

Avoid destructive reset semantics.

## Slice 9 - Steer Next 5

- Type: HITL for interaction review, AFK for implementation
- Suggested labels: `ready-for-agent`
- Blocked by: Slices 6, 7, and 8
- User stories covered: 34, 35, 36, 47
- Primary goal: let users add another confirmed natural-language steer before the next batch.

### What to build

Add **Steer next 5** as an optional continuation path.
After rating a batch, the user can add a new tonight-level steer, confirm the interpretation, and generate another five movies using prior reactions plus accumulated steering context.
The app should keep previous filters active unless the user explicitly changes them.

### Acceptance criteria

- [ ] The user can choose Steer next 5 after a batch.
- [ ] The steer uses the same intent interpretation and confirmation contract.
- [ ] Prior ratings remain active.
- [ ] Prior confirmed tonight filters remain active.
- [ ] The new steer is visible as part of active session context.
- [ ] Tests cover additive steering and prior-signal preservation.
- [ ] A phone-sized click-through proves the loop.

### Validation commands

```sh
pnpm check
```

```sh
pnpm build:web
```

### Stop condition

Stop when the user can rate five, realize what they want, steer, and get another five without losing context.

### Risk notes

Keep steering additive and understandable.

## Slice 10 - Hybrid Candidate Enrichment Pipeline

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: Slice 1
- User stories covered: 37, 38, 39, 40, 41, 42, 46
- Primary goal: enrich TMDb candidates with richer offline features where available while preserving graceful fallback.

### What to build

Build the local enrichment path that maps TMDb candidates to MovieLens or derived offline feature data where available.
The implementation should use committed fixtures for tests and keep downloaded datasets or generated proprietary artifacts out of Git.
It should report enrichment coverage so later scoring and evaluation can tell which candidates were rich-scored versus fallback-scored.

### Acceptance criteria

- [ ] TMDb candidate identity can be matched to an offline enrichment identity when available.
- [ ] Enriched candidates can carry feature or tag dimensions beyond genre.
- [ ] Candidates without enrichment remain valid fallback candidates.
- [ ] Enrichment coverage is reported in a reviewable shape.
- [ ] Tests use committed fixtures and do not require downloaded datasets.
- [ ] Documentation records source, license posture, local artifact handling, and mapping limits.
- [ ] No downloaded MovieLens dataset or generated restricted artifact is committed.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when scoring can receive enriched and fallback candidates through one inspectable path.

### Risk notes

Do not block every candidate on perfect MovieLens coverage.

## Slice 11 - Rich Recommendation Scoring And Evidence

- Type: AFK
- Suggested labels: `ready-for-agent`
- Blocked by: Slices 1 and 10
- User stories covered: 30, 40, 41, 42, 43, 45, 46, 48
- Primary goal: make the scorer use movie-level evidence, title similarity, feature/tag dimensions, session reactions, and tonight intent in an inspectable way.

### What to build

Extend recommendation scoring so full profile evidence and candidate enrichment matter beyond genre counts.
The scorer should use movie-level anchors from Taste Lab or app-owned ratings, title similarity, richer feature dimensions when available, session reactions, tonight intent, and existing hard constraints.
Explanations and snapshots should identify which signal families influenced a recommendation.
Fallback behavior should remain stable when enrichment is missing.

### Acceptance criteria

- [ ] Movie-level profile evidence can influence scoring beyond genre counts.
- [ ] Title similarity can influence ranking in at least one fixed scenario.
- [ ] Feature or tag dimensions can influence ranking when enrichment exists.
- [ ] Tonight intent can affect candidate fit without becoming permanent profile taste.
- [ ] Fallback candidates still score when enrichment is missing.
- [ ] Recommendation explanations distinguish the main signal families.
- [ ] Recommendation snapshots or evidence surfaces preserve enough detail for review.
- [ ] Tests verify observable ranking and explanation behavior.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when rich evidence changes recommendations in a testable, inspectable way without LLM ranking authority.

### Risk notes

Avoid tuning weights to only one happy-path fixture.

## Slice 12 - MVP Plus 2 Evaluation And Acceptance Gate

- Type: HITL
- Suggested labels: `ready-for-human`
- Blocked by: Slices 2 through 11
- User stories covered: 1, 2, 3, 40, 43, 44, 45, 46, 47, 48, 50
- Primary goal: prove MVP Plus 2 is done with both user-flow evidence and recommendation-quality evidence.

### What to build

Create the founder-facing acceptance gate for MVP Plus 2.
It should regenerate a recommendation-quality report, record enrichment coverage, compare baseline and enriched ranking behavior, and run a phone-sized click-through of the memory and steering loop.
This slice may include small docs and validation fixes needed to record the gate.

### Acceptance criteria

- [ ] A fixed evaluation report compares baseline, fallback, and enriched scoring.
- [ ] The report includes rank deltas, top-pick changes, explanation excerpts, and enrichment coverage.
- [ ] The report calls out where enrichment is missing or where richer scoring hurts or overfits.
- [ ] A phone-sized click-through covers profile identity, tonight intent, shared flow, Show 5 more, Steer next 5, save/remove, watched/rated action, memory panel, and evidence.
- [ ] The acceptance note states whether MVP Plus 2 is complete.
- [ ] Full validation passes.
- [ ] The current MVP tracker can honestly show 12/12 done only after this gate passes.

### Validation commands

```sh
pnpm check
```

```sh
pnpm build:web
```

```sh
python3 scripts/mvp_plus_2_evaluation.py
```

### Stop condition

Stop when MVP Plus 2 has both product-flow proof and recommendation-quality proof.

### Risk notes

This is the phase gate.
Do not close it because only the UI works or only the scoring report works.
