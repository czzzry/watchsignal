# Phase 2 Fixed-Source Feature Inventory

Date: 2026-07-12.
Phase: Recommendation Model Discovery Phase 2.
Issue: 3 - Build A Fixed-Source Feature Inventory.
Status: Complete locally.

## Decision

Issue 3 is complete locally.
Phase 2 may use fixed MovieLens-derived `genre`, `era`, and authorized `tag` evidence for content-aware challengers.
Phase 2 may not use cast, director, writer, language, runtime, keywords, collections, production country, or live TMDb fields for training until a separate fixed-source snapshot and license contract exists.

This is a conservative inventory.
It favors evidence we can reproduce over features that sound useful but would mutate under our feet.

## Benchmark Feature Inventory

The existing fixed content snapshot is `movielens-content-v1`.
It contains 87,585 MovieLens items and 285 feature columns.
The snapshot was fitted from the exploration role only and records `future_tag_rows_used=false`.

| Family | Source | Columns | Benchmark coverage | License posture | Phase 2 status |
| --- | --- | ---: | ---: | --- | --- |
| Genre | MovieLens `movies.csv` | 19 | 91.9164 percent | Local MovieLens research use | Eligible |
| Era | Release year parsed from MovieLens title | 10 | 100 percent | Local MovieLens research use | Eligible |
| Tags | Authorized MovieLens `tags.csv` rows at or before profile cutoff | 256 | 12.9109 percent | Local MovieLens research use | Eligible with sparse-support controls |
| Language | Not present in MovieLens 32M | 0 | 0 percent | No external fetch performed | Excluded |
| Cast | Not present in MovieLens 32M | 0 | 0 percent | No live TMDb fetch performed | Excluded |
| Crew | Not present in MovieLens 32M | 0 | 0 percent | No live TMDb fetch performed | Excluded |

Tag evidence used 241,383 authorized tag rows.
The tag vocabulary is capped at 256 terms with minimum five-movie support.
High-cardinality risk is controlled by top-support vocabulary selection plus stronger hybrid ridge penalty.

## Product Candidate Inventory

The app's local product fixture universe contains 13 demo candidates.

| Product field | Fixture coverage | Training status |
| --- | ---: | --- |
| Genres | 13 of 13 | Already aligned with eligible genre family |
| Runtime minutes | 13 of 13 | Product runtime field only, not fixed benchmark training data |
| Original language | 13 of 13 | Product watchability field only, not fixed benchmark training data |
| Spoken languages | 13 of 13 | Product watchability field only, not fixed benchmark training data |
| Top cast | 10 of 13 | Product explanation/candidate field only, not fixed benchmark training data |
| Overview text | 0 of 13 in fixtures | Not available as fixed training data |
| Enrichment feature scores | 0 of 13 in fixtures | Not available as fixed training data |
| Matched person names | 0 of 13 in fixtures | Product runtime signal only when present |

The product can continue using runtime, language, provider, cast, and person fields for filtering, explanations, candidate generation, and tonight intent.
Those fields are not approved as Phase 2 training features because they are not yet a frozen training snapshot.

## Leakage And Update Risks

MovieLens tags can leak future taste if all tag rows are used indiscriminately.
The existing snapshot avoids that by accepting only tag rows from exploration users at or before their authorized profile cutoff.

TMDb metadata can change over time and can depend on live API availability.
Using it for model training would require a dated local snapshot, checksum, source terms review, coverage report, and a no-live-fetch evaluation rule.

Cast and crew must remain role-aware.
An actor, director, and writer with the same name must not collapse into one undifferentiated person feature.

## Recommendation For Issue 5

Issue 5 may train with these eligible families:

- Genre.
- Era.
- Authorized MovieLens tags.

Issue 5 should not train a richer content-aware challenger on TMDb cast, director, writer, keyword, language, runtime, collection, or production-company features during this phase.
Those belong in a future fixed-source metadata slice.

## Engineering Evidence Loop

Claim: Phase 2 can safely define which content features are available before training content-aware challengers.

Contract: Feature families must list source, license posture, coverage, cardinality, update stability, and leakage risk.

Boundary: Product runtime metadata may support filtering and explanations.
Offline training features require fixed snapshots and checksums.

Behavior: Genre, era, and authorized tags are eligible.
Cast, crew, language, runtime, keywords, and other live metadata are excluded from Phase 2 training.

Evidence: The existing MovieLens content schema reports 285 fixed columns across genre, era, and tags, with explicit zero-column placeholders for cast, crew, and language.
The product fixture probe shows runtime, language, and cast exist in app candidates but are not fixed training data.

Decision: Mark Issue 3 complete locally and constrain Issue 5 to the eligible fixed families unless the founder approves a separate metadata-snapshot slice.
