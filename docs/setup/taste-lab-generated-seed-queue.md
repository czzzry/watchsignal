# Taste Lab Generated Seed Queue

Taste Lab should seed from a generated high-signal queue, not from a handpicked movie list.

The queue is generated from MovieLens-shaped `movies.csv`, `ratings.csv`, and optional `links.csv`.

MovieLens provides the statistical substrate.

`links.csv` provides TMDb ids when available.

Poster paths are not included in MovieLens.
The generator can enrich poster paths from TMDb when local TMDb credentials are available.

## Generate From MovieLens Small

Download and unzip MovieLens locally.

Do not commit the downloaded MovieLens dataset.

The generated queue is also ignored by Git for now because it is derived from MovieLens data.

```bash
curl -L --fail --output /private/tmp/ml-latest-small.zip https://files.grouplens.org/datasets/movielens/ml-latest-small.zip
unzip -o /private/tmp/ml-latest-small.zip -d /private/tmp/watchsignal-movielens
```

Generate the WatchSignal queue artifact:

```bash
cd /Users/cezarybaraniecki/Documents/movie-night-mediator-app
env UV_CACHE_DIR=/Users/cezarybaraniecki/Documents/movie-night-mediator-app/.tools/uv-cache \
  apps/api/../../.tools/uv/bin/uv run --project apps/api \
  python scripts/taste_lab_generate_seed_queue.py \
  --movies /private/tmp/watchsignal-movielens/ml-latest-small/movies.csv \
  --ratings /private/tmp/watchsignal-movielens/ml-latest-small/ratings.csv \
  --links /private/tmp/watchsignal-movielens/ml-latest-small/links.csv \
  --output apps/api/data/taste_lab_seed_queue.generated.json \
  --limit 250 \
  --min-rating-count 20
```

Generate the same queue with TMDb poster paths:

```bash
cd /Users/cezarybaraniecki/Documents/movie-night-mediator-app
env UV_CACHE_DIR=/Users/cezarybaraniecki/Documents/movie-night-mediator-app/.tools/uv-cache \
  apps/api/../../.tools/uv/bin/uv run --project apps/api \
  python scripts/taste_lab_generate_seed_queue.py \
  --movies /private/tmp/watchsignal-movielens/ml-latest-small/movies.csv \
  --ratings /private/tmp/watchsignal-movielens/ml-latest-small/ratings.csv \
  --links /private/tmp/watchsignal-movielens/ml-latest-small/links.csv \
  --output apps/api/data/taste_lab_seed_queue.generated.json \
  --limit 250 \
  --min-rating-count 20 \
  --enrich-posters \
  --poster-workers 8
```

`--enrich-posters` reads `TMDB_READ_ACCESS_TOKEN` or `TMDB_API_KEY` from `.env` or the shell environment.

It stores TMDb poster paths such as `/poster.jpg`, not downloaded images.

If a MovieLens-linked TMDb id is stale or missing a poster, the generator falls back to a TMDb title/year search for that candidate.

The API default seed endpoint reads:

```text
apps/api/data/taste_lab_seed_queue.generated.json
```

You can override that path with:

```bash
TASTE_LAB_SEED_QUEUE_PATH=/path/to/taste_lab_seed_queue.generated.json
```

## What The Algorithm Uses

The generator uses the existing `rank_signal_candidates` algorithm.

The score combines:

- recognizability
- divisiveness
- discrimination proxy
- genre coverage
- non-redundancy

The generated artifact includes each movie's rank, signal score, and component scores so the queue can be inspected.

## Current Local Artifact

The current local artifact was generated from `ml-latest-small`.

It contains 250 candidates.

It is a real algorithm output, not the old hardcoded 10-movie demo list.

Run the poster-enriched command above before using the private Taste Lab screen for portfolio-quality review.
