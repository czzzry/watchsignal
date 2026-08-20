# README Recommender Research And Evidence Notes

Date: 2026-08-20.
Status: Source note for the README implementation, not a new model or product decision.

## Founder-Readable Conclusion

WatchSignal has a stronger story than "we trained a recommendation model."
It built a protected experiment around a real research dataset, compared simple and learned approaches on the same future-rating task, rejected training loss as the decision metric, and spent two hidden test panels only after the candidate models were frozen.
That process selected a compact ratings-only collaborative model because it matched the more complicated hybrid's ranking quality while being much smaller and faster.

The most important honest qualification is that this is evidence about an individual's historical movie taste on a fixed pool of movies they later rated.
It is not yet evidence that the complete product helps two people choose a better movie tonight.
The app therefore keeps machine-learned individual taste separate from household compromise, current mood, hard constraints, streaming availability, and explanations.
The current live web path requests learned retrieval and the hybrid learned scorer, while the V2 layer still owns household compromise and remains available for rollback comparisons.
When learned scoring artifacts are unavailable, the scorer falls back explicitly to V2 and marks the result uncertain.

## Suggested README Section

### How the recommendation work was tested

The model never sees the answer sheet while it is ranking.
For each MovieLens user in the main benchmark, WatchSignal gives the model 100 earlier ratings and asks it to order 30 movies that the same person rated later.
Only after the ranking is fixed does a separate evaluator reveal the later ratings.

The experiment used the official [MovieLens 32M dataset](https://files.grouplens.org/datasets/movielens/ml-32m-README.html), with 32,000,204 ratings from 200,948 users across 87,585 movies.
Users were assigned to non-overlapping fit, tuning, internal-test, and one-time hidden-test roles, with timestamp checks that keep every future rating out of training, feature construction, and model selection.
The exact manifests and model files are fingerprinted so the same run can be reproduced without publishing MovieLens user identifiers.

WatchSignal compared random ordering, popularity, two hand-written scorers, ratings-only matrix factorization, and a hybrid that added genre, release-era, and tag features.
Models were judged by top-five ranking quality, positive-versus-negative ordering, known dislikes in the top five, coverage, and paired confidence intervals.
Training error was diagnostic only.

The final 16-factor collaborative model scored `0.615832` NDCG@5 on 5,000 previously unused users, compared with `0.615439` for the support-aware hybrid and `0.437816` for the deployed V2 heuristic.
The collaborative-versus-hybrid difference was effectively a tie, with a paired 95% interval from `-0.001928` to `0.002588`.
The simpler model won because its artifact was 78.6% smaller, its measured fit time was 43.5% lower, and its same-loop scoring time was 35.5% lower.

This identifies the current offline individual-taste champion.
It does not prove better couple compromise, tonight-specific relevance, streaming availability, or product adoption.
The later live-retrieval rollout made learned retrieval and the hybrid scorer the live web route's requested path, replacing popularity as the primary candidate pool while V2 still owns the two-person rules.

### Research foundations

The scientific literature shaped three different parts of the work.

- [Harper and Konstan's MovieLens dataset paper](https://files.grouplens.org/papers/harper-tiis2015.pdf) defines the provenance and limitations of the rating data used for the benchmark.
- [Koren, Bell, and Volinsky's matrix-factorization overview](https://doi.org/10.1109/MC.2009.263) is the closest technical foundation for the latent user and movie factors used by the collaborative model.
- [Järvelin and Kekäläinen's graded-ranking work](https://doi.org/10.1145/582415.582418) is the standard source for the NDCG family used to reward highly rated movies near the top of the shortlist.
- [Meyer and colleagues' evaluation protocol](https://arxiv.org/abs/1209.1983) supports judging useful ranking rather than choosing the model with the lowest rating-prediction error.
- [Meng and colleagues](https://arxiv.org/abs/2010.14013), [Nguyen and colleagues](https://arxiv.org/abs/2406.00973), and [Pennock and colleagues](https://arxiv.org/abs/1301.3885) informed Taste Lab's cold-start idea: ask about movies that reveal more preference information instead of collecting arbitrary ratings.
- [Çano and Morisio's hybrid-recommender review](https://arxiv.org/abs/1901.03888) motivated testing content and collaborative signals together, while the project's own ablation and hidden-test results determined whether that extra complexity was worth keeping.
- [Peška and Vojtáš's offline-versus-online study](https://arxiv.org/abs/1809.03186) supports the boundary that a good offline score cannot replace real product evaluation.
- [Basu Roy, Lakshmanan, and Liu's group-recommendation work](https://arxiv.org/abs/1503.03753) supports treating group satisfaction as a separate problem rather than averaging two personal scores and calling the work finished.

The papers did not choose the winning hyperparameters.
WatchSignal's own fit, tuning, ablation, internal-test, and replacement-panel results did that.

## Exact Dataset And Protocol

### Source corpus

The corpus is MovieLens 32M, generated on 2023-10-13 from rating and tagging activity between 1995-01-09 and 2023-10-12.
The official README reports 32,000,204 ratings, 2,000,072 tag applications, 87,585 movies, and 200,948 users.
The local archive used for the benchmark has SHA-256 `e4a68655d7386b8f95f2f2424b2ff975dfdd15ffd59e0d864a14dca43e99d6ee`, and all four internal file checksums passed.
The source and license conditions are recorded in the [official MovieLens 32M README](https://files.grouplens.org/datasets/movielens/ml-32m-README.html) and the local [dataset census](validation/movielens-32m-census.md).
The repository keeps raw MovieLens rows local and does not redistribute them.

### First protected benchmark

The primary established-user task used each person's final 130 eligible ratings.
The first 100 ratings formed the visible profile and the last 30 formed the hidden future candidate-and-label window.
Eligibility required a strict timestamp gap between profile and future rows, at least one future rating of `4.0` or higher, at least one future rating of `2.5` or lower, at least 365 days across the selected window, and complete TMDb mapping for all future movies.

The deterministic seed `20260710` assigned all 14,617 eligible established users to 4,617 exploration users, 5,000 validation users, and 5,000 sealed users.
A user had one protected role across all cohort views, and cross-role overlap was zero.
The local manifests held membership only, while committed checksums made their membership verifiable without publishing source user IDs.
The exact contract is in the [locked benchmark protocol](validation/movielens-benchmark-protocol.md) and [machine-readable protocol record](validation/movielens-protocol-lock.json).

The project also reported separate diagnostic cohorts.
Cold start used the first 10 ratings followed by the next 10, sparse recent used the last 10 profile ratings followed by 10 future ratings, deep history used 500 followed by 50, and prolific history used 1,000 followed by 100.
These cohorts were not silently pooled into the established headline result because they answer different questions.

### Initial training and selection

The first collaborative baseline trained only on exploration-profile rows.
For each authorized user it used one deepest available profile: 500 ratings for deep-history membership, otherwise 100 for established membership, otherwise 10 for cold-start membership.
That produced 1,268,600 training ratings from 5,406 users across 38,481 items.

Two explicit-feedback alternating-least-squares candidates were compared on validation-established ranking quality.
The 16-factor candidate won over the 32-factor candidate even though the 32-factor model had lower training RMSE, which is direct evidence that the project did not select on fit-to-training-data alone.
The first collaborative result is recorded in the [collaborative baseline report](validation/movielens-collaborative-baseline.md).

The first hybrid mapped 19 genres, 10 release-era buckets, and 256 pre-cutoff tag features into collaborative item-factor space with regularized weighted ridge regression.
Tag vocabulary used exploration users only and rejected tag events after each user's authorized profile cutoff.
Genre, era, and tag ablations were run on validation data before one complete hybrid artifact was frozen.
The hybrid then ran once on the original 5,000-user sealed panel and improved over the collaborative baseline by `0.005553` NDCG@5, with a 95% paired interval from `0.003863` to `0.007349`.
That gain was statistically credible but far below the predeclared `0.02` minimum useful improvement, so the automatic result was hold rather than unconditional promotion.
The evidence is recorded in the [feature-ablation selection](validation/movielens-model-selection.md) and [first sealed benchmark](validation/movielens-sealed-benchmark.md).

### Second development round

After the first sealed panel was opened, all 14,617 established users from that source population were retired as independent final evidence and repartitioned for development.
The deterministic seed `20260711` assigned 8,770 established users to development fit, 2,923 to development tune, and 2,924 to one shared internal test, with zero user overlap.
The internal test was explicitly labeled development evidence because aggregate results from that population had already influenced the program.

The final development-fit training set used 2,395,300 profile ratings from 10,187 authorized users across 49,299 items.
The user count is larger than the 8,770 established-fit count because the training builder also admitted development-fit users whose deepest authorized membership came from the cold-start or deep-history cohort.
No tuning or internal-test future label entered model fitting.
The exact split is recorded in the [model-improvement protocol](validation/model-improvement-development-protocol.md) and [machine-readable lock](validation/model-improvement-protocol-lock.json).

The collaborative search was capped at 12 declared candidates.
It varied 16 versus 32 latent dimensions, regularization `0.5`, `1.0`, or `2.0`, five versus eight iterations, and optional preference weights `0.5`, `1.0`, or `2.0` that emphasized ratings far from neutral.
The winning candidate was ordinary explicit ALS with 16 factors, regularization `2.0`, bias regularization `5.0`, five iterations, and no preference weighting.
The full candidate list and tune results are in the [collaborative search report](validation/movielens-collaborative-search.md).

The content-aware search compared eight declared support-blend shrinkages from `1` through `160` and selected `80` on development-tune NDCG@5.
Its fixed content snapshot still contained genre, era, and authorized pre-cutoff tags, and the internal-test labels remained closed during this search.
The search is recorded in the [support-aware hybrid report](validation/movielens-support-aware-hybrid.md).

### Independent replacement panel

The internal test selected the collaborative challenger through the predeclared simplicity route, then the project created a replacement hidden panel before opening any of its labels.
The replacement eligibility contract retained the final 100-profile and 30-future task but required a 30-to-364-day activity span and excluded every user in any prior exploration, validation, sealed, development-fit, development-tune, or internal-test manifest.
Of 9,706 eligible disjoint users, 5,000 were selected deterministically with seed `20260712`.
Selected overlap with every prior manifest was zero.

The frozen collaborative challenger, collaborative reference, support-aware hybrid, V1, V2, and popularity control ran through one unchanged evaluator exactly once.
That panel is now spent and cannot be called hidden evidence again.
The panel lock and result are in the [replacement-panel contract](validation/replacement-sealed-panel-lock.json) and [replacement sealed benchmark](validation/movielens-replacement-sealed-benchmark.md).

## Leakage And Comparison Controls

The following controls are implemented in code and visible in committed reports.

- Each per-user window is sorted by timestamp and movie ID, and the last profile timestamp must be strictly earlier than the first future timestamp.
- The scoring request contains profile evidence and future movie identities, but it does not contain the future rating labels.
- Future ratings are joined only after each model returns a ranking.
- Every compared model receives the same fingerprinted user input and candidate pool.
- Protected role loaders fail closed when a training or development command is given an unauthorized manifest.
- User membership is disjoint across protected roles, and checksum locks detect a changed local manifest.
- The popularity baseline removes the evaluated exploration user's own contribution, which prevents a trivial self-leak for that model.
- Hybrid tag features accept only exploration-user tag events at or before each user's authorized profile cutoff.
- Validation could choose models and parameters, while the original and replacement hidden panels could only evaluate a previously checksummed artifact.
- Raw user histories and learned user factors are absent from the saved collaborative artifact.

These controls are implemented in [benchmark protocol code](../apps/api/src/movie_night_mediator/evaluation/benchmark_protocol.py), [the chronological evaluator](../apps/api/src/movie_night_mediator/evaluation/chronological_tracer.py), [the baseline evaluator](../apps/api/src/movie_night_mediator/evaluation/cohort_baselines.py), [the collaborative trainer](../apps/api/src/movie_night_mediator/evaluation/collaborative.py), and [the content snapshot builder](../apps/api/src/movie_night_mediator/evaluation/content_features.py).

## Models And Baselines Actually Evaluated

| Approach | What it did | Why it mattered |
| --- | --- | --- |
| Deterministic random | Ordered the same future candidate pool by a seeded hash. | It exposed whether any apparent quality was better than chance. |
| Popularity | Ranked by an exploration-trained, shrinkage-smoothed average rating with leave-one-user-out handling during exploration evaluation. | It was the serious non-personalized control and beat both product heuristics on the offline task. |
| V1 | Applied the original hand-authored genre-oriented product scorer. | It preserved the old product baseline. |
| V2 | Applied the expanded hand-authored scorer. | It was the deployed control during the benchmark and remains the household-logic and rollback baseline. |
| Collaborative reference | Learned user and movie biases plus 16 latent item factors from explicit star ratings with regularization `1.0`. | It established whether ratings-only learning beat popularity and heuristics. |
| Collaborative challenger | Used the same explicit ALS family with regularization `2.0`. | It became the final offline champion. |
| Initial hybrid | Blended collaborative factors with genre, era, and tag-predicted factors. | It tested whether content improved sparse-item coverage and ranking. |
| Support-aware hybrid | Tuned how strongly collaborative evidence replaced content predictions as item rating support increased. | It was the quality and complexity comparator for the final model. |
| Preference-weighted ALS candidates | Increased squared-error weight for strong likes and dislikes. | They tested a ranking-aligned surrogate but did not win. |

The final collaborative model is not BPR, a neural recommender, an LLM ranker, or a model trained on WatchSignal household behavior.
It is a deterministic explicit-feedback matrix-factorization model implemented with alternating regularized ridge solves.

## Evaluation Metrics And Decision Rules

`NDCG@5` rewards highly rated future movies near the top of a five-item shortlist and discounts later positions.
The implementation maps ratings at or below `2.5` to zero relevance and gives progressively more gain to higher ratings.

`Pairwise preference accuracy` measures how often every future positive rating of `4.0` or higher is ranked above every future negative rating of `2.5` or lower.
Neutral ratings remain visible in denominators and reports but do not form positive-negative pairs.

`Known-dislike rate@5` measures the share of the first five ranked movies that the user later rated `2.5` or lower.
It is the safety metric and could not regress by more than `0.01` absolute.

`Coverage` measures how much of the candidate pool the model can score from its learned item universe.
The final learned-model gate required coverage of at least `0.98`.

Reports compute metrics per user and use a seeded paired user-level percentile bootstrap with 1,000 resamples for 95% intervals.
The original quality route required at least `0.02` absolute NDCG@5 improvement, a positive lower interval bound, non-regressing pairwise accuracy, dislike safety, and coverage safety.
The later simplicity route allowed a challenger whose NDCG@5 lower bound versus hybrid was no worse than `-0.005`, provided safety and coverage passed, at least one declared cost improved by 25%, and no other measured cost regressed by more than 25%.

Training RMSE was recorded after every ALS iteration but could not select the production candidate.
The 32-factor initial candidate is the clearest example: it fit the training ratings better and ranked future movies worse.

## Evidence That Selected The Current Approach

On the 2,924-user internal development test, the collaborative challenger scored `0.626508` NDCG@5 and the support-aware hybrid scored `0.626059`.
The paired difference was `+0.000449`, with a 95% interval from `-0.002967` to `0.003682`.
That failed the `0.02` quality route but passed the simplicity route because the challenger artifact was 78.6% smaller, fit time was 43.5% lower, scoring time was 32.6% lower, and the content-snapshot dependency disappeared.

On the 5,000-user replacement hidden panel, the collaborative challenger scored `0.615832`, hybrid scored `0.615439`, and V2 scored `0.437816` NDCG@5.
Collaborative minus V2 was `+0.178017`, with a 95% interval from `0.171070` to `0.184620`.
Collaborative minus hybrid was only `+0.000393`, with a 95% interval from `-0.001928` to `0.002588`.
The challenger again failed the separate quality route and passed the simplicity route, with 78.6% lower artifact size, 43.5% lower measured fit time, and 35.5% lower same-loop scoring time.

The evidence-backed statement is therefore that the collaborative model matched the hybrid's measured ranking quality at materially lower cost.
The evidence does not support saying that collaborative was meaningfully more accurate than hybrid.

## What The Scientific Articles Actually Influenced

The repository's papers and its benchmark did different jobs.
They should be presented together without claiming that one substituted for the other.

| Source | Repository use | Claim boundary |
| --- | --- | --- |
| [Harper and Konstan, 2015](https://doi.org/10.1145/2827872) | Required citation and context for MovieLens data. | It does not validate this project's split or results. |
| [Meng et al., 2020](https://arxiv.org/abs/2010.14013) | Supported treating cold-start item choice as an information problem in the Taste Lab research brief. | WatchSignal implemented an inspectable heuristic signal score, not the paper's algorithm. |
| [Nguyen et al., 2024](https://arxiv.org/abs/2406.00973) | Supported a recognizable burn-in followed by adaptive elicitation. | The current Taste Lab does not implement personalized embedding-region elicitation. |
| [Pennock et al., 2000](https://arxiv.org/abs/1301.3885) | Supported value-of-information reasoning for preference questions. | The current collaborative model is not personality diagnosis. |
| [Çano and Morisio, 2017](https://doi.org/10.3233/IDA-163209) | Supported trying a content-collaborative model to address sparse evidence and cold start. | The paper did not choose WatchSignal's feature families or shrinkage. |
| [Meyer et al., 2012](https://arxiv.org/abs/1209.1983) | Supported segmented ranking evaluation and the decision not to select on RMSE alone. | WatchSignal's exact metrics and gates are project-specific. |
| [Peška and Vojtáš, 2020](https://doi.org/10.1145/3372923.3404781) | Supported the rule that offline ranking evidence must be followed by product evidence. | Its e-commerce results do not predict WatchSignal household outcomes. |
| [Basu Roy, Lakshmanan, and Liu, 2015](https://doi.org/10.1145/2723372.2749448) | Supported treating group recommendation semantics as a separate layer. | The paper does not validate WatchSignal's exact two-person compromise weights. |

Two additional citations accurately describe implemented techniques but are not currently named in the July model-selection reports.
[Koren, Bell, and Volinsky, 2009](https://doi.org/10.1109/MC.2009.263) is the canonical model-family reference for regularized matrix factorization, and [Järvelin and Kekäläinen, 2002](https://doi.org/10.1145/582415.582418) is the canonical reference for discounted cumulative gain.
The README may cite them as technical foundations, but it should not imply that WatchSignal reproduced an experiment or copied a published implementation line for line.

## Claims The README Must Not Make

- Do not call the model a household or couple model.
- Do not say the model was trained on the founder's household, Taste Lab ratings, pass-the-phone reactions, or post-watch outcomes.
- Do not say collaborative was more accurate than hybrid in a practically meaningful sense.
- Do not describe the replacement panel as cross-dataset replication, because it used new users from the same MovieLens 32M corpus.
- Do not say the benchmark proves open-catalog discovery, because every model reranked a fixed set of movies that the user later rated.
- Do not say the evaluation proves streaming availability, tonight mood, two-person compromise, explanation quality, trust, adoption, watch starts, completion, or satisfaction.
- Do not call either opened hidden panel reusable test data, because both have been spent as independent evidence.
- Do not imply that the scientific papers selected the final factors, regularization, iteration count, or hybrid shrinkage, because the repository's protected experiments selected them.
- Do not present the hybrid's genre, era, and tag features as part of the winning model, because the final champion is ratings-only.
- Do not say the offline collaborative champion is the sole product default.
  The current live web route requests personalized learned retrieval plus `v2_hybrid`, while V2 still owns household rules and remains the explicit fallback when learned scoring artifacts are unavailable.
- Do not hide the MovieLens non-commercial license condition or imply that the raw corpus ships with the production app.

## Best Short Portfolio Claim

Designed and implemented a leakage-resistant recommender evaluation and model-selection system over MovieLens 32M, using chronological user histories, user-disjoint fit and test roles, random, popularity, heuristic, collaborative, and hybrid baselines, top-five ranking and safety metrics, paired bootstrap intervals, bounded parameter search, feature ablations, checksummed artifacts, and two one-time hidden evaluations.
The final 16-factor collaborative model matched the hybrid's offline ranking quality while reducing artifact size by 78.6% and scoring time by 35.5% on a 5,000-user replacement panel.

## Repository Evidence Index

- Narrative: [Recommendation Evaluation At WatchSignal](recommendation-evaluation.md).
- Dataset census: [MovieLens 32M Census](validation/movielens-32m-census.md).
- First protocol: [MovieLens Benchmark Protocol Lock](validation/movielens-benchmark-protocol.md).
- Baselines: [MovieLens Cohort Baselines](validation/movielens-cohort-baselines.md).
- Initial collaborative model: [Ratings-Only Collaborative Baseline](validation/movielens-collaborative-baseline.md).
- Initial hybrid: [Content-Collaborative Hybrid Baseline](validation/movielens-hybrid-baseline.md).
- Feature ablations: [MovieLens Feature-Family Ablation And Model Selection](validation/movielens-model-selection.md).
- First sealed result: [MovieLens Sealed Model Benchmark](validation/movielens-sealed-benchmark.md).
- Second development protocol: [Recommendation Model Improvement Development Protocol](validation/model-improvement-development-protocol.md).
- Final collaborative search: [Collaborative Ranking Search](validation/movielens-collaborative-search.md).
- Final hybrid search: [Support-Aware Hybrid Search](validation/movielens-support-aware-hybrid.md).
- Internal winner: [Internal Model Winner](validation/movielens-internal-winner.md).
- Replacement panel lock: [Replacement Sealed Panel Lock](validation/replacement-sealed-panel-lock.json).
- Final independent result: [Replacement Sealed Model Benchmark](validation/movielens-replacement-sealed-benchmark.md).
- Product boundary: [Learned Taste Product Integration](validation/learned-taste-product-integration.md).
- Taste Lab research: [Taste Lab Research Brief](taste-lab-research-brief.md).
- Broader V2 research: [Scoring V2 Data Research Spike](scoring-v2-data-research-spike.md).
