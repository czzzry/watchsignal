# Taste Lab Issue Breakdown

This issue set breaks [docs/prd-taste-lab.md](../prd-taste-lab.md) into bounded vertical slices.
It is prepared as local issue material and is not yet published to GitHub Issues.
Publishing these as GitHub issues is an external service action and should happen only after explicit founder approval.

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
- Primary goal: test whether Taste Lab ratings improve recommendation behavior compared with popularity-only or arbitrary rating.

### What to build

Create an evaluation harness that compares recommendation behavior before and after Taste Lab ratings.
The first evaluation should use fixed scenarios and held-out or synthetic preferences so changes can be compared consistently.
The evaluation should not require a polished UI.

Compare at least:
- no Taste Lab ratings,
- popularity-only seeded ratings,
- and high-signal seeded ratings.

### Acceptance criteria

- [ ] The evaluation can run from a local command.
- [ ] It compares at least two elicitation strategies.
- [ ] It reports recommendation-quality metrics or inspectable ranking deltas.
- [ ] It records enough output for founder review.
- [ ] It does not change production ranking behavior by default.

### Validation commands

```sh
pnpm check
```

### Stop condition

Stop when the repo can produce a before/after recommendation comparison grounded in fixed inputs.

### Risk notes

The first metrics may be imperfect.
The important thing is to create a repeatable evaluation loop before changing the main recommender.

## Recommended Order

1. Slice 1 - Offline Signal-Score Research Spike.
2. Slice 2 - Taste Signal Export Contract.
3. Slice 3 - Private Taste Lab Storage And API.
4. Slice 4 - Private Taste Lab Rating UI.
5. Slice 5 - Taste Lab Recommendation Evaluation.

## Open Questions

- Should Taste Lab live under the main `apps/api` and `apps/web` code from the start, or start under `tools/` and import later?
- Which MovieLens dataset size should be the first real local dataset?
- Should we use MovieLens Tag Genome in Slice 1, or defer tag dimensions until the basic rating-statistics queue works?
- Should the first queue be founder-only, or support both household profiles immediately?
- Should `Liked` and `Loved` map to separate strength values in the current scorer, or stay raw until the evaluation slice?
