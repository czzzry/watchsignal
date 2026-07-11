# Learned Taste Product Integration

Date: 2026-07-11.
Phase: Recommendation Learning Lab.
Issue: #127.
Status: Reversible integration complete; default promotion deferred until sufficient second-profile evidence exists.

## Decision Boundary

The founder originally approved hybrid for reversible product integration, not unconditional default promotion.
The original hybrid-versus-collaborative two-point practical-effect gate remains failed and has not been rewritten.
The second model-improvement phase subsequently selected a regularization-2.0 collaborative challenger as the offline champion through the predeclared simplicity route on a fresh replacement panel.
The product integration tests a separate question: whether a learned individual-taste provider improves the complete WatchSignal household path relative to the current V2 control.

## Runtime Architecture

The app now exposes four additive scorer identifiers:

- `v1_heuristic` preserves the original rollback path.
- `v2_contract` remains the unchanged default and deployed control.
- `v2_collaborative` supplies ratings-only learned individual scores to V2.
- `v2_hybrid` supplies content-collaborative learned individual scores to V2.

The learned provider replaces only each active person's durable individual taste score.
Existing V2 code continues to own compromise mode, husband-first and wife-first weighting, tonight intent, session reactions, candidate generation, hard watchability constraints, availability, confidence, and explanations.
The default remains `v2_contract` until the founder accepts the household gate.

## Artifact Boundary

The runtime verifies the exact selected artifact checksums before loading either model.

- Collaborative offline champion: `d6858942711fe929858c9143c8ca419952be9f135addd3f9b9694ac2294a344b`.
- Hybrid: `ab0a9622d31e0506ab91ec9be31fcbc3a7bf1a05a8360453df0b7dc92867d41a`.

The default `v2_collaborative` artifact path is `.tools/models/collaborative-search-candidate.zip`.
The hybrid path remains available as a historical comparator and rollback experiment.

Model files remain under ignored local `.tools/models` storage.
The app does not load the 318 MB MovieLens corpus or any MovieLens user history at recommendation time.
A generated compact link artifact maps public TMDb movie identifiers to model item identifiers and contains no user data.

Run `pnpm model:prepare:movielens-links` after preparing the local MovieLens archive.
The app accepts explicit path overrides through `MOVIE_NIGHT_COLLABORATIVE_MODEL_PATH`, `MOVIE_NIGHT_HYBRID_MODEL_PATH`, and `MOVIE_NIGHT_LEARNED_TASTE_LINKS_PATH`.

## Fallback Contract

Missing artifacts, checksum mismatches, missing link artifacts, cold profiles, and unmapped candidates cannot bypass product safety.
The scorer falls back deterministically to the unchanged V2 individual scores, records the fallback reason, marks the result uncertain, and preserves V1 and V2 as explicit rollback selections.
Candidates without learned coverage retain their V2 score rather than disappearing.

## Automated Evidence

The integration test matrix covers learned reranking, TMDb mapping, collaborative and hybrid adapters, cold-start fallback, missing-artifact fallback, deterministic rollback, compromise behavior, and mode-specific household reconciliation.
The full API suite passes more than 325 tests, including a regression link between the runtime collaborative checksum and the replacement sealed decision packet.
API compilation, generated TypeScript contract output, and the production Next.js build pass.
An exact-artifact runtime smoke loads both selected checksums and produces distinct learned rankings without opening sealed labels or raw MovieLens rows.

## Blind Household Gate

The draft comparison `household-gate-2026-07-11` used the real local profile and memory stores.
The harness fetches one live TMDb pool of 30 candidates, freezes its fingerprint, and gives that identical pool to all three complete product paths.
The paths are current V2, collaborative individual taste plus V2 household logic, and hybrid individual taste plus V2 household logic.
Their identities are randomized behind Path A, Path B, and Path C and stored only in an ignored local reveal key.

The tester profile supplies 50 mapped preference ratings after familiarity-only rows are excluded.
The configured second household profile, `profile-2`, currently supplies zero mapped preference ratings.
An attempted draft used an obsolete legacy profile named `wife`, but that profile supplied only one unique mapped durable rating plus several fixture-like rows and is not the configured household identity.
The draft was invalidated before the reveal because it would mostly measure the tester model and V2 fallback rather than two learned household profiles.
The harness now requires at least 10 mapped preference items per active profile, matching the locked cold-start benchmark depth.

The invalid comparison reveal key remains unopened and must not inform the rerun.
A fresh comparison may be generated only after the configured `profile-2` reaches the 10-item minimum.

## Deferred Household Gate

After a valid reveal, record where the household result agrees or disagrees with the offline evidence.
Then record one final product decision: promote the learned collaborative path to default, retain V2, or revise the household experiment.
Issue #127 is closed as reversible integration complete, while default promotion remains explicitly deferred rather than falsely blocked or silently accepted.
