# MovieLens Ratings-Only Collaborative Baseline

Date: 2026-07-10.
Phase: Recommendation Learning Lab.
Issue: #123.
Training role: Exploration only.
Selection role: Validation only.
Sealed labels opened: No.
Machine-readable report: `docs/validation/movielens-collaborative-baseline.json`.
Model artifact and per-user rows: Ignored local research storage only.

## Claim

A regularized ratings-only collaborative model can learn reusable movie factors from authorized exploration profiles, estimate a new user's taste vector from earlier ratings, and rank the same future candidate pools used by popularity, V1, and V2.
The model materially outperforms the hand-authored scorers.
It also beats popularity for deep-history validation users, but does not yet prove a broad win for established or cold-start users.

## Training Contract

The implementation uses explicit-feedback alternating least squares with a regularized squared-rating objective.
Each alternating step solves a ridge-regression problem for user vectors while movie vectors are fixed, then solves movie vectors while user vectors are fixed.

Training uses one deepest authorized profile per exploration user.
Deep-history users contribute 500 earlier ratings, established users contribute 100, and cold-start-only users contribute 10.
No future label enters training or fold-in.

- Training users: 5,406.
- Training ratings: 1,268,600.
- Learned movie items: 38,481.
- Deep-history source profiles: 1,883.
- Established source profiles: 3,243.
- Cold-start-only source profiles: 280.
- Seed: `20260710`.
- Optimizer: alternating ridge regression.
- Iterations: 5.
- Bias regularization: 5.0.

## Model Selection

Two configurations were declared before selection and compared on the 5,000 validation-established users.
The selection rule was highest NDCG@5, then pairwise preference accuracy, then lower dimensionality.

| Dimensions | Factor regularization | Final training RMSE | Validation NDCG@5 | Validation pairwise | Coverage |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 16 | 1.0 | 0.596575 | 0.603514 | 0.762530 | 0.989020 |
| 32 | 2.0 | 0.512643 | 0.598440 | 0.751263 | 0.989020 |

The 32-dimensional model reconstructed training ratings more accurately but ranked held-out future movies worse.
The 16-dimensional model therefore won.
This is why training loss is a diagnostic rather than the product-selection metric.

## Artifact And Fold-In

The selected artifact contains the global mean, 38,481 movie identifiers, movie biases, movie factors, configuration, and training-loss history.
It contains no user vectors and no raw user histories.

Artifact SHA-256: `683e6e47b33b11cf413cfc5ef3987480231e8580b954a0c370b98e5885e41ecd`.
An independent rebuild under pinned NumPy 2.4.6 reproduced the same checksum.

For a new user, the fold-in path holds movie factors fixed and solves one regularized taste vector from that user's earlier ratings.
The committed example supplied 10 validation cold-start ratings, matched all 10 to learned items, and used no future labels.

## Validation Results

| Cohort | Users | Collaborative NDCG@5 | Delta versus popularity, 95% CI | Pairwise | Dislike@5 | Item coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Cold start | 313 | 0.707810 | -0.015725 [-0.036616, 0.005550] | 0.726937 | 0.139936 | 0.997764 |
| Established | 5,000 | 0.603514 | 0.003336 [-0.001577, 0.008270] | 0.762530 | 0.081360 | 0.989020 |
| Deep history | 1,956 | 0.596007 | 0.022836 [0.015408, 0.030440] | 0.810338 | 0.081800 | 0.976738 |

The deep-history point estimate is 2.28 percentage points above popularity and its confidence interval is entirely positive.
However, the interval includes gains below the predeclared two-point minimum useful effect, so the data proves a real gain but does not prove with 95% confidence that the gain is at least two points.

The established point estimate is positive but the interval includes zero.
The cold-start point estimate is negative and its interval also includes zero.
The mature conclusion is therefore cohort-specific: collaborative structure helps users with rich histories, while the current model has not earned a broad all-user claim.

## Exploration Results

| Cohort | Users | Collaborative NDCG@5 | Delta versus popularity, 95% CI | Item coverage |
| --- | ---: | ---: | ---: | ---: |
| Cold start | 308 | 0.698587 | -0.003743 [-0.024257, 0.017318] | 0.998052 |
| Established | 4,617 | 0.593543 | -0.006641 [-0.012281, -0.000510] | 0.988239 |
| Deep history | 1,883 | 0.560271 | -0.007794 [-0.016390, 0.000956] | 0.976463 |

Exploration and validation differ because the model was trained on exploration users and hyperparameters were selected on validation-established performance.
The validation result is selection evidence, not sealed final proof.
The mixed exploration-versus-validation pattern is another reason not to promote the model yet.

## Safety And Coverage

On validation deep history, collaborative known-dislike rate@5 is 0.081800 versus popularity's 0.091207, a paired improvement of 0.009407.
On validation established, collaborative dislike@5 is 0.081360 versus popularity's 0.085680, an improvement of 0.004320.
Cold-start dislike@5 is slightly worse than popularity, with an inconclusive paired interval.

The learned item catalog covers 99.78% of cold-start, 98.90% of established, and 97.67% of deep-history validation candidates.
Unknown items receive the global-mean fallback and deterministic tie-breaking, and coverage is reported rather than hidden.
Profile-item coverage is 99.97% for cold start, 99.26% for established, and 98.66% for deep history.

## Runtime And Reproduction

The complete two-candidate selection and six-group evaluation took 1,218.723 seconds, or about 20.3 minutes.
Final selected-model evaluation took 284.834 seconds.
Peak memory was 458.94 MB.

Run `pnpm eval:movielens:collaborative` to reproduce training, selection, and evaluation.
Run `pnpm eval:movielens:collaborative:verify` to rebuild only the selected artifact and compare its checksum.
The environment pins NumPy 2.4.6 through the API project's lockfile.

## Limits And Next Move

This model learns only ratings relationships.
It cannot explain a recommendation through genre, style, cast, crew, language, or tonight intent.
It remains weaker than popularity for sparse users and cannot represent movies absent from exploration training.

The hybrid issue should preserve the collaborative factors while adding regularized content support for cold users and sparse items.
It should not assume metadata helps.
Feature families must earn retention through validation and later ablation rather than intuition.
