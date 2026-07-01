# Taste Lab Issue Breakdown

This issue set breaks [docs/prd-taste-lab.md](../prd-taste-lab.md) into bounded vertical slices.
It is prepared as local issue material and is not yet published to GitHub Issues.
Publishing these as GitHub issues is an external service action and should happen only after explicit founder approval.

## MVP Plus 1 Outcome

The next Taste Lab milestone is not a nicer standalone Taste Lab.
The next milestone is that Taste Lab ratings update WatchSignal taste data and influence the main app.

Minimum outcome improvement:

> As a user, I can use Taste Lab and have my tastes updated to the WatchSignal app.

Taste Lab should remain private and optional.
The data it captures should become durable profile-level evidence that WatchSignal can read.
The main couch-flow UI should not need to expose Taste Lab yet.

## Current Local Status

Slices 1 through 4 are substantially implemented in local app code.
Slices 5 through 8 are implemented locally in the current working tree.
The current private Taste Lab loop can generate a MovieLens-derived high-signal queue, enrich it with TMDb posters, persist ratings, exclude answered movies, and support repeated private rating batches.
The local WatchSignal read model can expose saved Taste Lab ratings as profile taste evidence.
The local recommender can consume that profile taste evidence and explain when Taste Lab signals influenced scores.
The review-only session evidence drawer can show Taste Lab-derived taste-profile signals beside the saved scoring snapshot.
The local evaluation command compares no Taste Lab data, weak seeded data, and high-signal Taste Lab data through the same profile-evidence scoring path.

The generated MovieLens-derived artifact remains local-only and ignored by Git.
The committed repo contains the generator, contract, API, UI, tests, and setup docs.

## Slice 1 - Offline Signal-Score Research Spike

- Type: AFK
- Suggested labels: `mvp-plus-1`, `research`, `ready-for-agent`
- Blocked by: None
- User stories covered: 2, 8, 9, 10, 11, 17, 18, 19, 20
- Primary goal: prove whether a high-signal movie queue can be computed from public ratings data in a way that is inspectable and sane.

### What to build

Build a local offline script that can load a small MovieLens-style dataset, compute signal-score features, and output a ranked list of candidate movies.
The script should not require the web app or API.
The output should include score components, not only a final score, so the founder can inspect why each movie was selected.

The first implementation can use a tiny committed fixture dataset for tests and document how to run against a larger local MovieLens download later.
Do not commit downloaded MovieLens datasets unless their license and size are explicitly approved.

### Acceptance criteria

- [ ] A local command computes a ranked signal-candidate list from MovieLens-shaped inputs.
- [ ] The output includes recognizability, divisiveness, coverage, non-redundancy, and total signal score.
- [ ] The output explains enough score components for human inspection.
- [ ] The command can run against a tiny fixture dataset in tests.
- [ ] Tests prove that already-selected or duplicate-like movies are penalized.
- [ ] Documentation explains how to use a larger MovieLens dataset locally without committing it.
- [ ] No app UI or production scoring behavior changes.

### Validation commands

```sh
pnpm check
```

or the narrower API test command if only Python files are touched.

### Stop condition

Stop when the repo can produce and test a ranked high-signal queue from local fixture data, with clear notes about using real MovieLens data locally.

### Risk notes

Avoid overclaiming.
This slice proves that a queue can be computed, not that it improves real recommendations yet.

## Slice 2 - Taste Signal Export Contract

- Type: AFK
- Suggested labels: `mvp-plus-1`, `data`, `ready-for-agent`
- Blocked by: Slice 1 recommended, but not strictly required
- User stories covered: 4, 5, 15, 16, 21, 23, 24
- Primary goal: define the portable data shape that lets Taste Lab start standalone and later import cleanly into WatchSignal.

### What to build

Define a stable Taste Lab rating export/import contract.
The contract should cover profile identity, source movie id, title, year, rating label, familiarity, queue source, timestamp, and optional score-feature provenance.
It should map `Loved`, `Liked`, `Meh`, `Hated`, and `Haven't seen` into WatchSignal taste semantics without treating unseen movies as dislike.

This slice may be docs-only if the schema is not yet needed by code.
If code is added, keep it as a small domain model with tests.

### Acceptance criteria

- [ ] The export contract is documented.
- [ ] `Haven't seen` is explicitly modeled as familiarity, not negative taste.
- [ ] Rating labels map to current or planned WatchSignal taste signals.
- [ ] The contract supports standalone Taste Lab data and future WatchSignal ingestion.
- [ ] Tests exist if code-level schema or validation is added.

### Validation commands

```sh
pnpm check
```

or docs validation only if no code changes.

### Stop condition

Stop when future slices have an agreed data contract to write to and read from.

### Risk notes

Do not couple the contract to one UI route.
The contract should survive either standalone Taste Lab or in-app Taste Lab.

## Slice 3 - Private Taste Lab Storage And API

- Type: AFK
- Suggested labels: `mvp-plus-1`, `backend`, `ready-for-agent`
- Blocked by: Slice 2
- User stories covered: 1, 3, 4, 5, 6, 7, 13, 15, 16, 21, 24
- Primary goal: make Taste Lab ratings persist locally and expose a small private API for batch queue and batch submit.

### What to build

Add local storage and API behavior for Taste Lab.
A private client should be able to request the next batch of 10 movies and submit a batch of labels.
The next-batch behavior should exclude already-rated movies and deprioritize recent `Haven't seen` movies.

The first queue can use the offline signal-score output as a static or generated local candidate list.
It does not need adaptive personalized selection yet.

### Acceptance criteria

- [ ] A profile can fetch a batch of 10 Taste Lab candidates.
- [ ] A profile can submit labels for a batch.
- [ ] Submitted labels persist locally.
- [ ] Already-rated movies are excluded from future batches.
- [ ] `Haven't seen` is persisted and deprioritized without becoming dislike.
- [ ] API tests cover fetch, submit, duplicate handling, and unseen handling.
- [ ] No public couch-flow behavior regresses.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when Taste Lab has a backend loop that can be exercised without UI.

### Risk notes

Keep the API private and local.
Do not introduce auth complexity unless the app is deployed beyond local development.

## Slice 4 - Private Taste Lab Rating UI

- Type: HITL for final interaction review, AFK for implementation
- Suggested labels: `mvp-plus-1`, `ui`, `ready-for-agent`
- Blocked by: Slice 3
- User stories covered: 1, 3, 4, 6, 7, 8, 12, 13, 14, 16
- Primary goal: let the founder rapidly rate batches of 10 movies in a private route.

### What to build

Build a private Taste Lab route for fast batch rating.
The UI should show 10 movie cards with real poster art, title, year, and enough metadata for recognition.
Each card should support `Loved`, `Liked`, `Meh`, `Hated`, and `Haven't seen`.
The page should save the batch and refresh to the next batch.

The UI can be utilitarian, but it must not look broken or use fake poster art.

### Acceptance criteria

- [ ] The private route displays 10 candidates when enough unrated candidates exist.
- [ ] Each candidate supports all five labels.
- [ ] Submitting a batch saves ratings and loads fresh candidates.
- [ ] The UI shows rating progress.
- [ ] The UI distinguishes `Haven't seen` from negative ratings.
- [ ] A phone-sized browser review confirms the flow is fast enough for repeated use.
- [ ] Production web build passes.

### Validation commands

```sh
pnpm build:web
```

```sh
pnpm check
```

### Stop condition

Stop when the founder can rate repeated batches locally without touching the normal couch-flow app.

### Risk notes

Do not make this route public-facing or recruiter-facing by accident.
Do not let UI polish consume the research purpose.

## Slice 5 - Taste Lab Recommendation Evaluation

- Type: AFK, with HITL for founder interpretation
- Suggested labels: `mvp-plus-1`, `evaluation`, `ready-for-agent`
- Blocked by: Slices 1 and 3
- User stories covered: 18, 19, 21, 22, 23, 25
- Primary goal: test whether Taste Lab ratings can improve or explainably influence WatchSignal recommendations compared with no Taste Lab data.

### What to build

Create an evaluation harness that compares recommendation behavior before and after Taste Lab ratings.
The first evaluation should use fixed scenarios and held-out, synthetic, or seeded Taste Lab preferences so changes can be compared consistently.
The evaluation should not require a polished UI.

Compare at least:
- no Taste Lab ratings,
- neutral or popularity-only seeded ratings,
- and high-signal Taste Lab ratings mapped into WatchSignal taste evidence.

### Acceptance criteria

- [x] The evaluation can run from a local command.
- [x] It compares at least two elicitation strategies.
- [x] It reports recommendation-quality metrics or inspectable ranking deltas.
- [x] It proves Taste Lab-derived signals can reach recommendation inputs.
- [x] At least one fixed recommendation scenario changes or is explainably influenced by Taste Lab-derived signals.
- [x] It records enough output for founder review.
- [x] It does not change production ranking behavior by default.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when the repo can produce a before/after recommendation comparison grounded in fixed inputs.

### Risk notes

The first metrics may be imperfect.
The important thing is to create a repeatable evaluation loop before changing the main recommender.

## Slice 6 - Taste Lab To WatchSignal Taste Profile Read Model

- Type: AFK
- Suggested labels: `mvp-plus-1`, `data`, `backend`, `ready-for-agent`
- Blocked by: Slices 2 and 3
- User stories covered: 21, 23, 24, 26, 28
- Primary goal: make saved Taste Lab ratings readable as WatchSignal taste-profile evidence without coupling the private Taste Lab route to the couch flow.

### What to build

Create a profile-level read model that summarizes Taste Lab ratings into WatchSignal taste evidence.
The model should preserve profile identity, source movie identity, label strength, familiarity, genres, queue provenance, and timestamp.
It should treat `Haven't seen` as familiarity evidence only.

The read model should be additive.
It should sit beside existing onboarding, session reaction, watched-history, and post-watch feedback signals rather than replacing them.
It does not need a mature public UI.

### Acceptance criteria

- [x] Taste Lab ratings can be read through a WatchSignal-facing profile summary or evidence API.
- [x] Loved, liked, meh, hated, and unseen labels map to explicit WatchSignal taste semantics.
- [x] `Haven't seen` contributes familiarity evidence without becoming negative preference.
- [x] Profile identities remain separate.
- [x] The read model includes enough provenance to show that a signal came from Taste Lab.
- [x] Tests cover the mapping from saved Taste Lab ratings to WatchSignal taste evidence.
- [x] No main couch-flow UI changes are required.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when WatchSignal code can read Taste Lab-derived taste evidence without knowing about the private Taste Lab UI.

### Risk notes

Do not make Taste Lab the only source of truth for taste.
Keep it as one durable evidence source that the recommendation layer can consume.

## Slice 7 - Recommendation Scoring Consumes Taste Lab Evidence

- Type: AFK, with HITL for founder interpretation of changed picks
- Suggested labels: `mvp-plus-1`, `recommendations`, `backend`, `ready-for-agent`
- Blocked by: Slice 6
- User stories covered: 21, 23, 25, 27, 28
- Primary goal: use Taste Lab-derived taste evidence in WatchSignal recommendation scoring so calibration effort can improve the main app outcome.

### What to build

Teach the recommendation layer to consume the Taste Lab-backed taste-profile read model.
Start with a narrow, inspectable scoring adjustment rather than a broad recommender rewrite.
For example, liked or loved genres and titles can add positive evidence, hated genres and titles can add negative evidence, and unseen movies can inform familiarity without preference penalty.

The implementation should preserve existing recommendation behavior when no Taste Lab evidence exists.
It should expose enough explanation data to show when Taste Lab evidence affected a candidate.

### Acceptance criteria

- [x] Recommendation scoring can read Taste Lab-derived taste evidence for each profile.
- [x] Existing scenarios behave the same when no Taste Lab ratings exist.
- [x] At least one fixed test scenario changes ranking or explanation when Taste Lab ratings are present.
- [x] Recommendation explanations can identify Taste Lab as an influence source.
- [x] Household overlap remains profile-aware and does not collapse separate people into one taste bucket.
- [x] Tests cover both no-data and Taste-Lab-data paths.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when the main WatchSignal recommendation path can be demonstrably influenced by saved Taste Lab ratings.

### Risk notes

Avoid pretending the first scoring adjustment is a mature personalization engine.
The goal is a defensible tracer bullet from calibration data to recommendation outcome.

## Slice 8 - Minimal App Evidence Of Updated Taste

- Type: HITL for copy and browser review, AFK for implementation
- Suggested labels: `mvp-plus-1`, `ui`, `validation`, `ready-for-agent`
- Blocked by: Slices 6 and 7
- User stories covered: 13, 14, 21, 26, 27, 28
- Primary goal: make the outcome improvement visible enough that the founder can verify Taste Lab updated WatchSignal, without making Taste Lab part of the normal couch flow.

### What to build

Add minimal evidence that the main app can see Taste Lab-derived taste data.
This could be a private debug/profile panel, a recommendation explanation line, or a non-public profile summary route.
It should show that Taste Lab ratings are saved, mapped, and available to WatchSignal recommendations.

Do not add a prominent public Taste Lab entry point yet.
Do not require normal movie-night users to complete Taste Lab before starting a session.

### Acceptance criteria

- [x] There is a small local way to inspect Taste Lab-derived WatchSignal taste evidence.
- [x] Recommendation output can show when Taste Lab evidence influenced a pick or ranking.
- [x] The private Taste Lab route remains optional and outside the normal couch flow.
- [x] A phone-sized browser review confirms the evidence is understandable.
- [x] The UI does not imply that Taste Lab is a public or mandatory feature.
- [ ] Production web build passes if frontend files change.

### Validation commands

```sh
pnpm build:web
```

```sh
pnpm check
```

### Stop condition

Stop when a founder can rate in Taste Lab, return to WatchSignal, and verify that the app has absorbed those signals.

### Risk notes

Keep the surface small.
This is evidence of the pipeline, not the mature Taste Lab product experience.

## Recommended Order

1. Slice 1 - Offline Signal-Score Research Spike.
2. Slice 2 - Taste Signal Export Contract.
3. Slice 3 - Private Taste Lab Storage And API.
4. Slice 4 - Private Taste Lab Rating UI.
5. Slice 6 - Taste Lab To WatchSignal Taste Profile Read Model.
6. Slice 7 - Recommendation Scoring Consumes Taste Lab Evidence.
7. Slice 5 - Taste Lab Recommendation Evaluation.
8. Slice 8 - Minimal App Evidence Of Updated Taste.

## Open Questions

- The first WatchSignal taste-profile read model is profile-level evidence with source, source movie id, title, genres, preference value, familiarity, label, and timestamp.
- The first scoring integration uses genre-level Taste Lab evidence only.
- Household overlap stays profile-aware by attaching Taste Lab evidence to individual `UserProfile` records.
- Minimal app evidence lives in the review-only session evidence drawer before Taste Lab becomes a mature optional app feature.
- Which MovieLens dataset size should be the first real local dataset?
- Should we use MovieLens Tag Genome in Slice 1, or defer tag dimensions until the basic rating-statistics queue works?
- Should `Liked` and `Loved` map to separate strength values in the current scorer, or stay raw until the evaluation slice?
