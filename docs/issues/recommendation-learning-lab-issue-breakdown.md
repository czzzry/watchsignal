# Recommendation Learning Lab Issue Breakdown

This issue set turns the accepted MovieLens evaluation and machine-learning plan into bounded vertical slices.
It keeps the completed Scoring V2 phase unchanged and starts a new phase for offline evidence, learned recommendation baselines, hybrid modeling, and product promotion.

## Current Phase

The current phase is **Recommendation Learning Lab**.
The founder accepted the phase direction and authorized issue publication.

```text
Recommendation Learning Lab: [################....] 7/9 issues done
```

The phase contains one data-profiling slice, one founder protocol gate, five implementation and evidence slices, one sealed-test decision gate, and one product-integration gate.
New work discovered during execution must be classified as in-scope risk closure, a scope-change candidate requiring founder approval, or next-phase backlog.

## GitHub Tracker

- [#119 - Profile MovieLens 32M And Recommend The Benchmark Protocol](https://github.com/czzzry/watchsignal/issues/119)
- [#120 - Approve The Benchmark Protocol And Seal Cohort Manifests](https://github.com/czzzry/watchsignal/issues/120)
- [#121 - Run A One-User Chronological Benchmark Tracer Bullet](https://github.com/czzzry/watchsignal/issues/121)
- [#122 - Publish Cohort-Scale Popularity, V1, And V2 Baselines](https://github.com/czzzry/watchsignal/issues/122)
- [#123 - Train And Evaluate A Ratings-Only Collaborative Baseline](https://github.com/czzzry/watchsignal/issues/123)
- [#124 - Train And Evaluate A Hybrid Content-Collaborative Scorer](https://github.com/czzzry/watchsignal/issues/124)
- [#125 - Run Feature-Family Ablations And Select A Validation Winner](https://github.com/czzzry/watchsignal/issues/125)
- [#126 - Run The Sealed Benchmark And Make The Model Promotion Decision](https://github.com/czzzry/watchsignal/issues/126)
- [#127 - Integrate The Approved Taste Model And Pass The Household Gate](https://github.com/czzzry/watchsignal/issues/127)

## Phase Promise

WatchSignal can use a protected MovieLens benchmark to compare popularity, V1, V2, a ratings-only collaborative model, and a hybrid recommendation model, then integrate a learned durable-taste signal only after it wins on sealed future ratings and real household review.

The phase is done only when all of these are true:

- Raw MovieLens data remains local, reproducible, license-aware, and outside Git.
- Exploration, validation, and sealed benchmark users and labels have explicit manifests and checksums.
- Chronological evaluation prevents future evidence from entering profile or model inputs.
- Popularity, V1, V2, collaborative, and hybrid baselines run through the same external evaluation contract.
- Feature-family ablations show what metadata contributes without choosing features from sealed-test results.
- A founder decision records whether a learned model earned promotion.
- Any promoted model remains behind a reversible scoring boundary.
- Tonight intent, availability, safety, and couple reconciliation remain product-owned reranking concerns.
- A phone-sized household test confirms that offline improvement helps real movie-night decisions.

## Product And Evaluation Invariants

- V2 produces scores and does not evaluate itself.
- The external harness owns evaluation and cannot alter scorer behavior to make a benchmark pass.
- Unrated movies remain unknown rather than being labeled as dislikes.
- Metrics are calculated per user before aggregation.
- Sample size is derived from pilot variance and a founder-approved minimum useful effect.
- MovieLens users below the main history threshold may remain in a separately reported cold-start cohort.
- Sealed benchmark labels are not used for feature invention, tuning, or model selection.
- Candidate generation, durable taste estimation, and tonight or couple reranking remain separate responsibilities.
- No paid vendor, secret, commercial dataset use, or new production service is introduced without founder approval.
- Production V2 remains available until a learned replacement passes the explicit promotion gate.

## Issue 1 - Profile MovieLens 32M And Recommend The Benchmark Protocol

- Type: AFK
- Suggested label: `ready-for-agent`
- Blocked by: None
- User story: As the founder, I can see what the real dataset supports before accepting cohort sizes, history windows, metrics, or sample counts.
- Status: Done locally through `pnpm eval:movielens:census`, the committed JSON and Markdown census reports, focused census tests, and the full repository check.

### What to build

Create a reproducible local census of the official MovieLens 32M corpus and a protocol recommendation.
Measure user history depth, rating distribution and variance, chronological activity span, duplicate behavior, future positive and negative label balance, movie identifier coverage, and eligibility under candidate history and holdout windows.
Run a small exploration-only variance pilot and produce sample-size options for declared minimum useful improvements.
Do not change any scorer or open a sealed benchmark.

### Acceptance criteria

- [x] The official dataset version, provenance, checksums, and license constraints are recorded.
- [x] Raw dataset files remain under an ignored local data path and are not committed.
- [x] The census reports counts for cold-start, sparse-recent, established, deep-history, and prolific-user cohorts.
- [x] Candidate history and future-rating windows include eligibility counts and positive or negative label coverage.
- [x] TMDb mapping coverage, missing metadata, timestamp anomalies, and excluded rows are reported rather than silently dropped.
- [x] An exploration-only pilot estimates user-level metric variance.
- [x] A sample-size table shows the users required for at least three candidate minimum useful effects.
- [x] The report recommends a protocol but leaves the final lock to Issue 2.

## Issue 2 - Approve The Benchmark Protocol And Seal Cohort Manifests

- Type: HITL
- Suggested label: `ready-for-human`
- Blocked by: Issue 1
- User story: As the founder, I can approve exactly what the benchmark will prove before implementation or model tuning begins.

### What to build

Review the census and make the founder-owned protocol decisions.
Lock the primary and safety metrics, minimum useful effect, user eligibility rules, fixed history and future windows, cold-start reporting posture, sample size, and MovieLens license posture.
Generate deterministic exploration, validation, and sealed benchmark manifests with recorded checksums and an access policy for sealed labels.

### Acceptance criteria

- [x] The founder accepts or revises the main, deep-history, and cold-start cohort rules.
- [x] The founder selects the minimum useful improvement used by the power calculation.
- [x] Primary metrics, safety metrics, confidence intervals, and exclusion reporting are locked.
- [x] Per-user chronological windows and any global time boundary are documented.
- [x] Exploration, validation, and sealed benchmark manifests have fixed seeds and checksums.
- [x] The sealed-label access rule and benchmark-reset trigger are documented.
- [x] The decision record states what the benchmark cannot prove about couples, tonight intent, availability, or real product success.

## Issue 3 - Run A One-User Chronological Benchmark Tracer Bullet

- Type: AFK
- Suggested label: `ready-for-agent`
- Blocked by: Issue 2
- User story: As an engineer, I can trace one real user from raw ratings through hidden future labels and a scored result without temporal leakage.

### What to build

Build the smallest complete offline-evaluation path through the application contracts.
Translate one exploration user’s earlier MovieLens ratings into application-native profile evidence, translate later rated movies into an identical candidate pool, run at least V1 and V2, and score the returned ranking only after the future labels are unsealed inside the evaluator.
Keep the evaluation package outside the production request path.

### Acceptance criteria

- [x] MovieLens ratings map deterministically into application-native profile evidence with traceable source IDs and timestamps.
- [x] Later labels remain absent from profile and scoring request inputs.
- [x] V1 and V2 receive byte-equivalent user, session, and candidate inputs where their contracts overlap.
- [x] One deliberate future-row injection makes a leakage test fail.
- [x] Candidate-pool inequality between scorers makes a parity test fail.
- [x] Missing movie identifiers and excluded labels are counted explicitly.
- [x] Repeated runs with the fixed seed produce identical machine-readable results.
- [x] No production API, UI, or default scorer behavior changes.

## Issue 4 - Publish Cohort-Scale Popularity, V1, And V2 Baselines

- Type: AFK
- Suggested label: `ready-for-agent`
- Blocked by: Issue 3
- User story: As the founder, I can see how current scoring compares with simple baselines across cold-start, established, and deep-history users.

### What to build

Scale the benchmark runner across the locked exploration and validation cohorts.
Run random-order and popularity sanity baselines plus unchanged V1 and V2 scorers.
Publish per-user and aggregate learning curves, ranking metrics, known-dislike exposure, confidence behavior, coverage, exclusions, runtime, and paired model deltas with user-level confidence intervals.

### Acceptance criteria

- [x] Random and popularity baselines run through the same candidate and label contract as V1 and V2.
- [x] V1 and V2 run unchanged and use the same eligible users and candidate pools.
- [x] Metrics are calculated per user before cohort aggregation.
- [x] Results are separated by cold-start, established, and deep-history cohorts.
- [x] Every headline result includes its denominator, uncertainty interval, and exclusion count.
- [x] The report shows how quality changes with profile evidence depth.
- [x] Runtime and memory usage are recorded for a reproducible local run.
- [x] The report does not inspect or summarize sealed benchmark labels.

## Issue 5 - Train And Evaluate A Ratings-Only Collaborative Baseline

- Type: AFK
- Suggested label: `ready-for-agent`
- Blocked by: Issue 4
- User story: As the founder, I can see whether learned user and movie relationships outperform hand-authored recommendation rules without relying on metadata guesses.

### What to build

Train a simple, regularized collaborative recommendation baseline on the authorized training data.
Prefer a boring and inspectable matrix-factorization or pairwise-ranking implementation with deterministic configuration, explicit model artifacts, and a documented fold-in path for a new app user who supplies initial ratings.
Evaluate it through the same external harness and candidate pools used by the existing baselines.

### Acceptance criteria

- [x] The training objective, latent dimension count, regularization, optimizer, and seed are recorded.
- [x] Training and validation obey the locked temporal protocol.
- [x] Model artifacts are reproducible and contain no raw personal histories.
- [x] A new-user fold-in example estimates a taste vector from earlier ratings without future labels.
- [x] Collaborative results are compared with popularity, V1, and V2 by locked cohort and metric.
- [x] Cold-start limitations and unmapped-movie limitations are reported honestly.
- [x] Hyperparameters are selected only from authorized development and validation data.
- [x] Sealed benchmark labels remain unopened.

## Issue 6 - Train And Evaluate A Hybrid Content-Collaborative Scorer

- Type: AFK
- Suggested label: `ready-for-agent`
- Blocked by: Issue 5
- User story: As the founder, I can test whether movie meaning and creative metadata improve learned collaborative taste, especially for sparse users and less-rated movies.

### What to build

Add a versioned content feature matrix to the collaborative baseline and train the first hybrid model.
Use coherent feature families such as genres, release era, language, MovieLens tags or Tag Genome values, role-aware cast and crew, and style concepts where license, mapping, and cache coverage permit.
Evaluation runs must use fixed local feature snapshots rather than live provider calls.

### Acceptance criteria

- [x] The feature schema records provenance, type, missingness, coverage, and license posture for every family.
- [x] Cast and crew preserve role identity rather than collapsing every person into one undifferentiated field.
- [x] Feature extraction is fitted only on authorized training data where fitting can leak corpus-wide statistics.
- [x] Evaluation uses versioned local snapshots and makes no live TMDb calls.
- [x] Regularization or equivalent controls limit fragile high-cardinality people and tag features.
- [x] The hybrid is compared with the ratings-only collaborative baseline on the same validation users and metrics.
- [x] Cold-start and sparse-item results are reported separately.
- [x] The model exposes enough contribution evidence for later family-level ablation and product debugging.

## Issue 7 - Run Feature-Family Ablations And Select A Validation Winner

- Type: AFK
- Suggested label: `ready-for-agent`
- Blocked by: Issue 6
- User story: As the founder, I can understand which broad evidence families improve recommendation quality without manually guessing individual weights.

### What to build

Retrain controlled model variants that remove one coherent feature family at a time while holding the protocol and remaining configuration fixed.
Measure the contribution of genres and era, semantic tags and style, cast, crew, language, and collaborative latent factors where available.
Use the locked validation decision rule to select one candidate model for sealed evaluation.

### Acceptance criteria

- [x] Each ablation changes one declared feature family while preserving all other experiment settings.
- [x] Validation reports show overall and cohort-specific metric deltas with user-level confidence intervals.
- [x] Known-dislike exposure, confidence behavior, coverage, and runtime are considered alongside ranking accuracy.
- [x] High-cardinality families report support and regularization diagnostics.
- [x] No feature family is retained because of sealed-test performance.
- [x] The selected model and exact artifact checksum are recorded before Issue 8 begins.
- [x] V1, V2, popularity, ratings-only collaborative, and hybrid results remain visible in the selection packet.

## Issue 8 - Run The Sealed Benchmark And Make The Model Promotion Decision

- Type: HITL
- Suggested label: `ready-for-human`
- Blocked by: Issue 7
- User story: As the founder, I can make one evidence-backed decision about whether the selected learned model deserves product integration.

### What to build

Run the preselected model and all required baselines once against the sealed benchmark manifest.
Produce a decision packet that applies the locked promotion rules without post-hoc metric substitution.
Record whether to promote, hold, revise with a new untouched benchmark, or stop the learned-model path.

### Acceptance criteria

- [ ] The selected artifact checksum matches the Issue 7 selection record.
- [ ] Sealed labels are opened only by the benchmark runner and access is logged.
- [ ] The packet compares the selected model with popularity, V1, V2, and the ratings-only collaborative baseline.
- [ ] Primary, safety, confidence, coverage, runtime, and cohort results use the predeclared decision rules.
- [ ] The packet distinguishes statistical evidence from practical product significance.
- [ ] The founder records a promote, hold, revise, or stop decision.
- [ ] Any revise decision documents whether a fresh sealed manifest is required before another claim.

## Issue 9 - Integrate The Approved Taste Model And Pass The Household Gate

- Type: HITL
- Suggested label: `ready-for-human`
- Blocked by: Issue 8
- User story: As a household user, I receive recommendations informed by the approved learned taste model while tonight intent, safety, availability, and couple compromise remain intact.

### What to build

If Issue 8 approves promotion, integrate the selected durable-taste model behind the existing reversible scoring boundary.
Keep production candidate generation, hard constraints, tonight-intent interpretation, and couple reconciliation as explicit application-owned layers.
Run a phone-sized real flow and blind household comparison before changing the default.
If Issue 8 does not approve promotion, close this issue with the recorded hold, revise, or stop outcome and make no product change.

### Acceptance criteria

- [ ] The learned model is selected through an explicit reversible configuration seam.
- [ ] V1 and V2 rollback paths remain available until the founder accepts the household gate.
- [ ] Candidate generation and hard watchability constraints remain outside the learned taste model.
- [ ] Tonight intent and couple reconciliation consume the durable taste score without being trained from MovieLens labels.
- [ ] Existing API consumers remain compatible or receive an explicitly approved contract migration.
- [ ] Automated tests cover fallback, missing artifact, cold-start, and deterministic rollback behavior.
- [ ] A phone-sized browser click-through records what was tested and any visible rough edges.
- [ ] Blind household comparisons record where offline evidence agrees or disagrees with actual choices.
- [ ] The founder records the final default-promotion decision.

## Dependency Chain

```text
Issue 1 -> Issue 2 -> Issue 3 -> Issue 4 -> Issue 5 -> Issue 6 -> Issue 7 -> Issue 8 -> Issue 9
```

This sequence is deliberately linear through the first benchmark and promotion cycle.
Parallel feature experiments may be proposed after Issue 6, but they must not bypass Issue 7 validation selection or Issue 8 sealed evaluation.
