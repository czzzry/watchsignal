# Personalized retrieval rollout

## What changed

Live recommendations now have a learned retrieval stage before the existing household scorer.

The collaborative lane retrieves from the trained MovieLens item-factor universe.

The content lane combines the hybrid factor artifact with a transparent catalog vector built from genres, release era, and profile-title signals.

The existing scorer still owns household compromise, confirmed intent constraints, safety, availability, diversity, explanations, and final ordering.

TMDb is used to hydrate the learned source ids and verify that a title is actually watchable in the selected region and service.

TMDb popularity is now an exploration fallback, not the primary live candidate pool.

## Runtime artifacts

The local runtime needs the collaborative model, hybrid model, MovieLens/TMDb links, and the compact catalog.

Prepare the catalog with:

```text
pnpm model:prepare:movielens-catalog
```

Override locations with `MOVIE_NIGHT_COLLABORATIVE_MODEL_PATH`, `MOVIE_NIGHT_HYBRID_MODEL_PATH`, `MOVIE_NIGHT_LEARNED_TASTE_LINKS_PATH`, and `MOVIE_NIGHT_RETRIEVAL_CATALOG_PATH`.

If an artifact is missing or fails its checksum, the service uses the existing V2 rollback path and marks the result uncertain.

## Evidence

The focused retrieval suite exercises profile-driven ordering, content-lane composition, cold-start protection, explicit exclusions, and learned-id hydration.

The local profile probe can be run with:

```text
pnpm eval:personalized-retrieval
```

The report records evidence depth, score spread, anchor ranks, top candidates, and superhero-title hits.

The probe is a diagnostic report, not a claim that offline MovieLens quality guarantees household quality.

## Promotion rule

Promote the learned default only when the local profile has at least ten mapped preference items per active participant, the artifacts pass checksum validation, and the live candidate source returns enough provider-eligible titles after hard filters.

Keep the environment override for `v1_heuristic`, `v2_contract`, and `v2_collaborative` rollback comparisons.
