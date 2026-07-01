#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.taste_lab.seed_queue_artifact import (  # noqa: E402
    build_seed_queue_payload,
    load_tmdb_poster_paths,
    write_seed_queue_artifact,
)


TMDB_BASE_URL = "https://api.themoviedb.org/3"


class TmdbPosterClient:
    def __init__(self, *, api_key: str | None, read_access_token: str | None) -> None:
        if not api_key and not read_access_token:
            raise RuntimeError(
                "Set TMDB_READ_ACCESS_TOKEN or TMDB_API_KEY before enriching posters."
            )

        self.api_key = api_key
        self.read_access_token = read_access_token

    def poster_path_for_tmdb_id(self, tmdb_id: str) -> str | None:
        query: dict[str, str] = {"language": "en-US"}
        headers = {"accept": "application/json"}
        if self.read_access_token:
            headers["Authorization"] = f"Bearer {self.read_access_token}"
        else:
            query["api_key"] = self.api_key or ""

        url = f"{TMDB_BASE_URL}/movie/{tmdb_id}?{urlencode(query)}"
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 404:
                return None
            raise

        poster_path = payload.get("poster_path")
        if isinstance(poster_path, str) and poster_path.strip():
            return poster_path.strip()
        return None

    def poster_path_for_title(
        self,
        *,
        title: str,
        release_year: int | None,
    ) -> str | None:
        query = {
            "query": title,
            "language": "en-US",
        }
        if release_year is not None:
            query["year"] = str(release_year)

        headers = {"accept": "application/json"}
        if self.read_access_token:
            headers["Authorization"] = f"Bearer {self.read_access_token}"
        else:
            query["api_key"] = self.api_key or ""

        url = f"{TMDB_BASE_URL}/search/movie?{urlencode(query)}"
        request = Request(url, headers=headers)
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))

        results = payload.get("results")
        if not isinstance(results, list):
            return None

        for result in results:
            if not isinstance(result, dict):
                continue
            poster_path = result.get("poster_path")
            if isinstance(poster_path, str) and poster_path.strip():
                return poster_path.strip()

        return None


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    return values


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a WatchSignal Taste Lab seed queue from MovieLens CSVs."
    )
    parser.add_argument("--movies", required=True, type=Path, help="Path to movies.csv.")
    parser.add_argument("--ratings", required=True, type=Path, help="Path to ratings.csv.")
    parser.add_argument("--links", type=Path, help="Optional path to links.csv.")
    parser.add_argument("--output", required=True, type=Path, help="Output JSON path.")
    parser.add_argument("--limit", default=250, type=int, help="Number of candidates.")
    parser.add_argument(
        "--min-rating-count",
        default=20,
        type=int,
        help="Minimum ratings required before a movie can enter the queue.",
    )
    parser.add_argument(
        "--enrich-posters",
        action="store_true",
        help="Fetch TMDb poster paths for linked candidates.",
    )
    parser.add_argument(
        "--poster-workers",
        default=8,
        type=int,
        help="Concurrent TMDb poster fetches when --enrich-posters is enabled.",
    )
    args = parser.parse_args()

    payload = build_seed_queue_payload(
        movies_path=args.movies,
        ratings_path=args.ratings,
        links_path=args.links,
        limit=args.limit,
        min_rating_count=args.min_rating_count,
    )

    poster_paths_by_tmdb_id: dict[str, str] = {}
    if args.enrich_posters:
        if args.links is None:
            raise RuntimeError("--enrich-posters requires --links.")

        env = load_env_file(REPO_ROOT / ".env")
        client = TmdbPosterClient(
            api_key=env.get("TMDB_API_KEY") or os.environ.get("TMDB_API_KEY"),
            read_access_token=env.get("TMDB_READ_ACCESS_TOKEN")
            or os.environ.get("TMDB_READ_ACCESS_TOKEN"),
        )
        poster_paths_by_tmdb_id = load_tmdb_poster_paths(
            selected_tmdb_ids(payload),
            client=client,
            max_workers=args.poster_workers,
        )
        poster_paths_by_tmdb_id.update(
            title_fallback_poster_paths(payload, poster_paths_by_tmdb_id, client)
        )
        payload = build_seed_queue_payload(
            movies_path=args.movies,
            ratings_path=args.ratings,
            links_path=args.links,
            poster_paths_by_tmdb_id=poster_paths_by_tmdb_id,
            limit=args.limit,
            min_rating_count=args.min_rating_count,
        )
    write_seed_queue_artifact(payload, args.output)
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(args.output),
                "candidate_count": len(payload["candidates"]),
                "queue_source": payload["queue_source"],
                "poster_path_count": sum(
                    1
                    for candidate in payload["candidates"]
                    if candidate["movie"]["poster_path"]
                ),
            },
            indent=2,
        )
    )


def selected_tmdb_ids(payload: dict[str, object]) -> tuple[str, ...]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        return ()

    tmdb_ids: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        movie = candidate.get("movie")
        if not isinstance(movie, dict):
            continue
        tmdb_id = movie.get("tmdb_id")
        if isinstance(tmdb_id, str) and tmdb_id.strip():
            tmdb_ids.append(tmdb_id.strip())

    return tuple(tmdb_ids)


def title_fallback_poster_paths(
    payload: dict[str, object],
    poster_paths_by_tmdb_id: dict[str, str],
    client: TmdbPosterClient,
) -> dict[str, str]:
    fallback_paths: dict[str, str] = {}
    for movie in selected_movies(payload):
        tmdb_id = movie.get("tmdb_id")
        title = movie.get("title")
        release_year = movie.get("release_year")
        if not isinstance(tmdb_id, str) or tmdb_id in poster_paths_by_tmdb_id:
            continue
        if not isinstance(title, str):
            continue

        poster_path = client.poster_path_for_title(
            title=title,
            release_year=release_year if isinstance(release_year, int) else None,
        )
        if poster_path:
            fallback_paths[tmdb_id] = poster_path

    return fallback_paths


def selected_movies(payload: dict[str, object]) -> tuple[dict[str, object], ...]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        return ()

    movies: list[dict[str, object]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        movie = candidate.get("movie")
        if isinstance(movie, dict):
            movies.append(movie)

    return tuple(movies)


if __name__ == "__main__":
    main()
