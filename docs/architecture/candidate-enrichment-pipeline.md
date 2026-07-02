# Candidate Enrichment Pipeline

MVP Plus 2 keeps TMDb as the live candidate and display source.
The enrichment path adds offline feature dimensions only after a candidate has already entered the local scoring pool.

## Source Posture

The committed implementation uses a tiny fixture that mimics derived MovieLens Tag Genome-style feature scores.
It is intentionally hand-sized and test-oriented.
It does not commit a downloaded MovieLens dataset, a generated full mapping, or a proprietary artifact.

The fixture lives in `apps/api/src/movie_night_mediator/app/candidate_enrichment.py`.
It is enough to prove the contract shape:

- match a TMDb candidate identity to an offline enrichment identity
- attach feature or tag dimensions beyond genre
- keep unmatched candidates valid as fallback candidates
- report enrichment coverage for recommendation review

## Matching Limits

The current matcher checks:

- exact offline source movie id
- normalized title plus release year
- normalized title fallback

Title-only fallback is acceptable for committed tests and local demos.
A production-grade dataset import should tighten this with TMDb ids, MovieLens links metadata, release year checks, and collision reports before scores affect real recommendations.

## Runtime Behavior

Every candidate receives enrichment metadata before scoring:

- `enrichment_status`
- `enrichment_provider`
- `matched_enrichment_source_movie_id`
- `enrichment_feature_scores`

Mapped candidates use `enriched` and the fixture provider.
Unmapped candidates use `fallback` and retain their TMDb metadata, genres, availability, language, and safe-pick fields.
Fallback candidates remain rankable.

Recommendation snapshots persist candidate-level enrichment metadata and expose aggregate coverage through debug history.
This lets later scoring and evaluation show which recommendations were rich-scored versus fallback-scored.

## Artifact Handling

Downloaded MovieLens files, generated full mappings, and restricted derived artifacts must stay out of Git.
If a future local import is added, it should read from a developer-local path or ignored cache, then write only review-safe summaries or tiny committed fixtures.
