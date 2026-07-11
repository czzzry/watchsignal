# MovieLens Benchmark Protocol Lock

Date: 2026-07-10.
Phase: Recommendation Learning Lab.
Decision owner: Founder.
Status: Approved for implementation.
Machine-readable record: `docs/validation/movielens-protocol-lock.json`.

## Claim

WatchSignal may compare popularity, V1, V2, collaborative, and hybrid recommendation approaches on protected MovieLens future ratings.
The benchmark is designed to detect a repeatable improvement of at least two absolute percentage points without allowing validation or sealed answers to influence earlier model construction.

## Locked Cohorts

The established headline cohort uses each eligible user's final 100 profile ratings followed by 30 future ratings.
The deep-history cohort uses 500 profile ratings followed by 50 future ratings.
The initial cold-start diagnostic uses the earliest 10 ratings followed by the next 10 ratings.
The sparse-recent diagnostic uses the final 10 profile ratings followed by 10 future ratings.
The prolific sensitivity cohort uses 1,000 profile ratings followed by 100 future ratings.

Every reported cohort requires a strict timestamp boundary between profile and future labels, at least one positive and one negative future label, at least 365 days across the selected window, and complete TMDb mapping for future movies.
Initial cold start and sparse recent evidence must be reported separately because they answer different product questions.

## Temporal Contract

The benchmark uses per-user chronological windows rather than one global calendar cutoff.
MovieLens users have substantially different activity periods, so one global cutoff would discard useful users without creating a more faithful product simulation.
For every user, the last profile timestamp must still be strictly earlier than the first future-label timestamp.
No future row may enter profile construction, feature generation, candidate scoring, or model selection.

## Protected Roles

The deterministic seed is `20260710`.
The established cohort is divided into 4,617 exploration users, 5,000 validation users, and 5,000 sealed users.
One user has one role across every cohort, and the generated manifests report zero cross-role overlap.
The local manifests contain user membership only and never contain ratings or future labels.
The MovieLens-derived manifest files remain under ignored local storage because the project does not redistribute raw dataset identifiers.
The committed lock records cohort counts and SHA-256 checksums so the exact local membership can be verified without publication.

Exploration labels may be inspected for adapter development, debugging, feature invention, and failure analysis.
Validation labels may select model families, features, and parameters, but they do not constitute final proof.
Sealed labels may be opened only during GitHub issue #126 after the selected model artifact checksum has been recorded.
The sealed access event and resulting decision must be recorded.

If sealed results influence any model, feature, or parameter change, the panel loses its status as independent evidence.
Its rows may later join training, but another final claim requires a recorded replacement sealed panel.

## Metrics And Decision Protection

The primary metrics are NDCG@5 and pairwise preference accuracy.
NDCG@5 measures whether highly rated future movies appear near the top of the five-item ranking, with earlier positions receiving more credit.
Pairwise preference accuracy measures how often the scorer correctly orders a more-preferred future movie above a less-preferred one.

The safety metric is known-dislike rate@5.
It may not regress by more than one absolute percentage point.
Every report must aggregate per user, include 95% bootstrap confidence intervals, and state all exclusions and denominators.
The minimum useful improvement is two absolute percentage points.

## What This Benchmark Cannot Prove

MovieLens contains individual historical ratings rather than two-person household decisions.
It cannot prove recommendation quality for couple compromise, tonight-specific mood, current streaming availability, or real product trust and adoption.
Offline promotion therefore remains necessary but not sufficient.
Any promoted model must still pass the WatchSignal household gate.

## Evidence And Reproduction

Run `pnpm eval:movielens:protocol` to regenerate the ignored local manifests from the local MovieLens 32M archive.
Run `pnpm eval:movielens:protocol:verify` to compare those files with the committed checksums.
The approved machine-readable lock is `docs/validation/movielens-protocol-lock.json`.
The dataset census supporting this decision is `docs/validation/movielens-32m-census.md`.
