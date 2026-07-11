# MovieLens 32M Census And Protocol Recommendation

Date: 2026-07-10
Phase: Recommendation Learning Lab: MovieLens 32M Census
GitHub issue: #119
Command: `pnpm eval:movielens:census`

## Engineering Evidence Loop

- Claim: Benchmark sizing and cohort rules can come from measured corpus properties rather than guessed percentages.
- Contract: This JSON and Markdown pair records provenance, integrity, cohort eligibility, label balance, mapping, anomalies, pilot variance, and sample-size options.
- Boundary: Offline evaluation tooling and ignored local data only; no production scorer path changes.
- Behavior: The same archive, cohort definitions, pilot size, and seed reproduce the same report.
- Evidence: Internal file checksums, full-corpus counts, deterministic cohort windows, and an exploration-only variance proxy.
- Decision: Issue #120 must approve or revise the proposal before manifests, model tuning, or sealed testing begin.

## Dataset Summary

- Users: 200,948
- Ratings: 32,000,204
- Mean ratings per user: 159.25
- Movie rows: 87,585
- Movies with TMDb IDs: 87,461
- Archive SHA-256: `e4a68655d7386b8f95f2f2424b2ff975dfdd15ffd59e0d864a14dca43e99d6ee`
- Internal checksum status: passed

## License Posture

- Research use: Research use under the MovieLens README conditions.
- Commercial constraint: Commercial or revenue-bearing use requires GroupLens permission.
- Repository rule: Do not publish raw files from this repository; preserve attribution and source license conditions for any authorized redistribution.

## User History Depth

| Ratings per user | Users |
|---|---:|
| 20-49 | 72,604 |
| 50-99 | 47,669 |
| 100-199 | 38,478 |
| 200-499 | 29,594 |
| 500-999 | 8,982 |
| 1000+ | 3,621 |

## Candidate Cohorts

| Cohort | Window | History | Future | Eligible users | Strict + both labels | Strict + both + 365 days | Analysis-ready + mapped | Holdout TMDb coverage |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| cold_start | start | 10 | 10 | 200,948 | 91,234 | 936 | 934 | 99.99% |
| sparse_recent_profile | end | 10 | 10 | 200,948 | 87,886 | 6,089 | 6,076 | 99.98% |
| established | end | 100 | 30 | 63,668 | 46,072 | 14,700 | 14,617 | 99.98% |
| deep_history | end | 500 | 50 | 10,756 | 8,941 | 5,987 | 5,912 | 99.97% |
| prolific | end | 1,000 | 100 | 2,940 | 2,523 | 2,040 | 1,989 | 99.97% |

## Coverage And Anomalies

- Rating rows with TMDb ID: 31,995,478 / 32,000,204 (99.99%)
- Rating rows with movie metadata: 32,000,204 / 32,000,204 (100.00%)
- Rating rows without genres: 55,498 / 32,000,204 (0.17%)
- Invalid rating rows: 0
- Invalid timestamps: 0
- Nonpositive timestamps: 0
- Duplicate user-movie rows: 0
- User-order anomalies: 0
- Duplicate timestamps within a user: 5,262,395
- Users with at least one duplicate timestamp: 88,745

## Exploration-Only Variance Pilot

- Method: Deterministic established-user sample scored by a simple profile-genre content proxy. This estimates user-level metric scale, not model-delta variance.
- Eligible established users considered: 63,668
- Deterministic sample size: 2,000

| Metric | Users | Mean | Standard deviation |
|---|---:|---:|---:|
| ndcg_at_5 | 2,000 | 0.5092 | 0.2113 |
| pairwise_accuracy | 1,636 | 0.6124 | 0.2187 |
| known_dislike_rate_at_5 | 2,000 | 0.1272 | 0.1998 |

## Sample-Size Options

These are two-sided 95% planning estimates with 80% power for independent user-level observations.
The conservative column uses standard deviation 0.5.
The proxy columns use the exploration genre baseline and must be replaced by paired model-difference variance once it exists.

| Minimum effect | Conservative users | NDCG@5 proxy | Pairwise proxy | Dislike@5 proxy |
|---:|---:|---:|---:|---:|
| 1.00% | 19,623 | 3,505 | 3,756 | 3,134 |
| 2.00% | 4,906 | 877 | 939 | 784 |
| 3.00% | 2,181 | 390 | 418 | 349 |

## Protocol Recommendation For Issue #120

- Main cohort: Use established users with the immediately preceding 100 ratings as profile evidence and the final 30 ratings as a fixed future window.
- Deep-history cohort: Report 500-history plus 50-future users separately for richer feature experiments; do not let prolific users dominate the main estimate.
- Cold-start cohort: Use each user's earliest 10 ratings as history and next 10 as future labels. Treat this as a limited calibration diagnostic because strict, long-span eligibility is much smaller than the full dataset.
- Sparse recent-profile cohort: Use the 10 ratings immediately before a final 10-rating window to test limited visible evidence at a mature point, and do not call it true cold start.
- Sample size: Select the final user count in Issue 120 from the declared minimum useful effect and the conservative or pilot-based table. Re-estimate paired-difference variance after real baseline results exist.
- Temporal rule: Preserve per-user chronology now and add a global time boundary before training collaborative models across users and movies.
- Sealed-data rule: Issue 119 uses exploration data only. Validation and sealed manifests are created only after the founder locks the protocol in Issue 120.

## Evidence Limits

- The genre proxy pilot estimates metric scale, not V1/V2 paired-difference variance.
- Many users batch-record ratings, so rating timestamps are not guaranteed watch timestamps.
- MovieLens ratings do not represent tonight intent, streaming availability, or couple negotiation.
- Selecting only prolific users would improve per-user stability while reducing product representativeness.
- Unrated movies remain unknown and are not counted as dislikes.
- The census does not tune or promote any scorer.
