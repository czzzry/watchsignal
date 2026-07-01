# Taste Lab Signal Score Setup

This document explains the first offline WatchSignal Taste Lab queue generator.
It is intentionally inspectable rather than magical.
The goal is to find movies whose ratings are likely to teach the recommender more than arbitrary popular movies.

## What The Score Means

The first signal score is a weighted blend of five components.

- `recognizability` rewards movies with many ratings in the dataset.
- `divisiveness` rewards movies where historical viewers split strongly.
- `discrimination_proxy` combines divisiveness with recognizability as a first-pass stand-in for preference separation.
- `coverage` rewards movies that add useful genre breadth or less common genre coverage.
- `non_redundancy` penalizes movies that look too similar to already selected movies.

This is not the final recommender.
It is the first evidence-backed way to create a fast rating queue.
The output includes every component so the founder can inspect whether the ranking feels sane.

## Research Basis

The idea maps to active learning and cold-start preference elicitation.
Meng et al. frame first-item selection as an explicit cold-start problem.
Nguyen et al. describe an elicitation approach where early questions are chosen for information value after a popular-item burn-in.
Pennock et al. connect collaborative filtering with value-of-information reasoning.
Item response theory contributes the idea that some items discriminate better than others along a latent trait.
MovieLens provides the public ratings substrate used by recommender research.

Sources:

- [Meng et al., The item selection problem for user cold-start recommendation](https://arxiv.org/abs/2010.14013)
- [Nguyen et al., Cold-start Recommendation by Personalized Embedding Region Elicitation](https://arxiv.org/abs/2406.00973)
- [Pennock et al., Collaborative Filtering by Personality Diagnosis](https://arxiv.org/abs/1301.3885)
- [Item response theory overview](https://en.wikipedia.org/wiki/Item_response_theory)
- [GroupLens MovieLens datasets](https://grouplens.org/datasets/movielens/)

## Run With The Tiny Fixture

From the repo root:

```sh
python3 scripts/taste_lab_signal_score.py \
  --movies apps/api/tests/fixtures/taste_lab/movies.csv \
  --ratings apps/api/tests/fixtures/taste_lab/ratings.csv \
  --limit 5
```

To save the output:

```sh
python3 scripts/taste_lab_signal_score.py \
  --movies apps/api/tests/fixtures/taste_lab/movies.csv \
  --ratings apps/api/tests/fixtures/taste_lab/ratings.csv \
  --limit 5 \
  --output /tmp/watchsignal-taste-lab-candidates.json
```

The fixture uses invented movie titles.
It exists only to make the tests deterministic.

## Run With A Larger MovieLens Dataset

Download a MovieLens dataset from GroupLens into a local, uncommitted folder such as `/tmp` or `data/local`.
Do not commit the downloaded dataset unless license, size, and privacy implications are explicitly approved.

For example, after downloading and unzipping a MovieLens dataset that contains `movies.csv` and `ratings.csv`:

```sh
python3 scripts/taste_lab_signal_score.py \
  --movies /path/to/ml-latest-small/movies.csv \
  --ratings /path/to/ml-latest-small/ratings.csv \
  --limit 200 \
  --min-rating-count 50 \
  --output /tmp/watchsignal-signal-candidates.json
```

The script accepts MovieLens-shaped CSV files with:

- `movies.csv`: `movieId`, `title`, `genres`
- `ratings.csv`: `userId`, `movieId`, `rating`

## Reading The Output

Each row includes:

- movie identity and genres
- rating count, mean rating, variance, and polarized rating share
- the five signal components
- total `signal_score`
- a short explanation

Use the ranked output as a candidate queue for Taste Lab.
Do not treat it as proof that recommendations improved.
That proof belongs to the later evaluation slice.
