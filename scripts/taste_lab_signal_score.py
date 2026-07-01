#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.taste_lab import (  # noqa: E402
    SignalScoreConfig,
    load_movielens_movies,
    load_movielens_ratings,
    rank_signal_candidates,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rank MovieLens-shaped movies by WatchSignal Taste Lab signal value."
    )
    parser.add_argument("--movies", required=True, type=Path, help="Path to movies.csv.")
    parser.add_argument("--ratings", required=True, type=Path, help="Path to ratings.csv.")
    parser.add_argument("--limit", default=100, type=int, help="Number of rows to output.")
    parser.add_argument(
        "--exclude-movie-id",
        action="append",
        default=[],
        help="MovieLens movieId to exclude and count as already selected.",
    )
    parser.add_argument(
        "--min-rating-count",
        default=1,
        type=int,
        help="Minimum ratings required before a movie can be ranked.",
    )
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    args = parser.parse_args()

    config = SignalScoreConfig(min_rating_count=args.min_rating_count)
    candidates = rank_signal_candidates(
        load_movielens_movies(args.movies),
        load_movielens_ratings(args.ratings),
        limit=args.limit,
        excluded_movie_ids=args.exclude_movie_id,
        config=config,
    )
    payload = [candidate.as_dict() for candidate in candidates]
    output = json.dumps(payload, indent=2)

    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
