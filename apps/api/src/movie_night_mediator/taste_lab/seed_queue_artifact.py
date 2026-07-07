from __future__ import annotations

import csv
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from movie_night_mediator.taste_lab.export_contract import (
    TasteLabMovieIdentity,
    TasteLabQueueProvenance,
)
from movie_night_mediator.taste_lab.service import TasteLabCandidate
from movie_night_mediator.taste_lab.signal_score import (
    SignalCandidate,
    SignalScoreConfig,
    load_movielens_movies,
    load_movielens_ratings,
    rank_signal_candidates,
)


TASTE_LAB_SEED_QUEUE_SCHEMA_VERSION = "taste_lab.seed_queue.v1"


def build_seed_queue_payload(
    *,
    movies_path: Path,
    ratings_path: Path,
    links_path: Path | None = None,
    poster_paths_by_tmdb_id: Mapping[str, str] | None = None,
    limit: int = 250,
    min_rating_count: int = 20,
    generated_at: str | None = None,
) -> dict[str, object]:
    links_by_movie_id = load_movielens_links(links_path) if links_path else {}
    poster_paths = poster_paths_by_tmdb_id or {}
    generated_timestamp = generated_at or _current_timestamp()
    candidates = rank_signal_candidates(
        load_movielens_movies(movies_path),
        load_movielens_ratings(ratings_path),
        limit=limit,
        config=SignalScoreConfig(min_rating_count=min_rating_count),
    )

    return {
        "schema_version": TASTE_LAB_SEED_QUEUE_SCHEMA_VERSION,
        "queue_source": "movielens_signal_score_v1",
        "generated_at": generated_timestamp,
        "candidates": [
            _candidate_to_payload(
                candidate,
                rank=rank,
                generated_at=generated_timestamp,
                tmdb_id=links_by_movie_id.get(candidate.movie_id),
                poster_path=poster_paths.get(links_by_movie_id.get(candidate.movie_id, "")),
            )
            for rank, candidate in enumerate(candidates, start=1)
        ],
    }


def load_seed_queue_artifact(path: Path | str) -> tuple[TasteLabCandidate, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != TASTE_LAB_SEED_QUEUE_SCHEMA_VERSION:
        raise ValueError("Unsupported Taste Lab seed queue schema version.")

    raw_candidates = payload.get("candidates")
    if not isinstance(raw_candidates, list):
        raise ValueError("Taste Lab seed queue artifact must contain candidates.")

    return tuple(_payload_to_candidate(candidate) for candidate in raw_candidates)


def write_seed_queue_artifact(payload: Mapping[str, object], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


class TmdbPosterClient(Protocol):
    def poster_path_for_tmdb_id(self, tmdb_id: str) -> str | None:
        raise NotImplementedError


def load_tmdb_poster_paths(
    tmdb_ids: Sequence[str],
    *,
    client: TmdbPosterClient,
    max_workers: int = 1,
) -> dict[str, str]:
    unique_tmdb_ids = tuple(dict.fromkeys(tmdb_ids))
    if max_workers < 1:
        raise ValueError("max_workers must be at least 1.")

    if max_workers == 1:
        return {
            tmdb_id: poster_path
            for tmdb_id in unique_tmdb_ids
            if (poster_path := client.poster_path_for_tmdb_id(tmdb_id))
        }

    poster_paths: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_tmdb_id = {
            executor.submit(client.poster_path_for_tmdb_id, tmdb_id): tmdb_id
            for tmdb_id in unique_tmdb_ids
        }
        for future in as_completed(future_to_tmdb_id):
            poster_path = future.result()
            if poster_path:
                poster_paths[future_to_tmdb_id[future]] = poster_path

    return poster_paths


def load_movielens_links(path: Path | str) -> dict[str, str]:
    with Path(path).open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return {
            row["movieId"]: row["tmdbId"]
            for row in reader
            if row.get("movieId") and row.get("tmdbId")
        }


def _candidate_to_payload(
    candidate: SignalCandidate,
    *,
    rank: int,
    generated_at: str,
    tmdb_id: str | None,
    poster_path: str | None,
) -> dict[str, object]:
    title, release_year = _split_movielens_title(candidate.title)
    return {
        "movie": {
            "source_movie_id": f"movielens:{candidate.movie_id}",
            "title": title,
            "release_year": release_year,
            "tmdb_id": tmdb_id,
            "poster_path": poster_path,
            "genres": list(candidate.genres),
        },
        "queue_provenance": {
            "queue_source": "movielens_signal_score_v1",
            "generated_at": generated_at,
            "rank": rank,
            "signal_score": round(candidate.signal_score, 6),
            "score_components": {
                "recognizability": round(candidate.recognizability, 6),
                "divisiveness": round(candidate.divisiveness, 6),
                "discrimination_proxy": round(candidate.discrimination_proxy, 6),
                "coverage": round(candidate.coverage, 6),
                "non_redundancy": round(candidate.non_redundancy, 6),
                "rating_count": float(candidate.rating_count),
                "rating_variance": round(candidate.rating_variance, 6),
                "polarized_share": round(candidate.polarized_share, 6),
                "mean_rating": round(candidate.mean_rating, 6),
            },
        },
    }


def _payload_to_candidate(payload: Mapping[str, Any]) -> TasteLabCandidate:
    movie_payload = payload.get("movie")
    provenance_payload = payload.get("queue_provenance")
    if not isinstance(movie_payload, Mapping) or not isinstance(
        provenance_payload,
        Mapping,
    ):
        raise ValueError("Taste Lab seed candidate must include movie and provenance.")

    return TasteLabCandidate(
        movie=TasteLabMovieIdentity(
            source_movie_id=str(movie_payload["source_movie_id"]),
            title=str(movie_payload["title"]),
            release_year=movie_payload.get("release_year"),
            tmdb_id=movie_payload.get("tmdb_id"),
            poster_path=movie_payload.get("poster_path"),
            genres=tuple(movie_payload.get("genres", ())),
        ),
        queue_provenance=TasteLabQueueProvenance(
            queue_source=str(provenance_payload["queue_source"]),
            generated_at=provenance_payload.get("generated_at"),
            rank=provenance_payload.get("rank"),
            signal_score=provenance_payload.get("signal_score"),
            score_components=provenance_payload.get("score_components", {}),
            queue_reason=provenance_payload.get("queue_reason"),
        ),
    )


def _split_movielens_title(raw_title: str) -> tuple[str, int | None]:
    match = re.search(r"\s+\((\d{4})\)$", raw_title)
    if match is None:
        return raw_title, None

    return raw_title[: match.start()].strip(), int(match.group(1))


def _current_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
