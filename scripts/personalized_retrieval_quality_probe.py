"""Report learned retrieval behavior for one local household profile."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from movie_night_mediator.app.personalized_recommendation import (
    PersonalizedCandidateRetriever,
    load_movielens_catalog,
)
from movie_night_mediator.domain import UserProfile
from movie_night_mediator.scoring.learned_taste import (
    load_collaborative_taste_provider,
    load_hybrid_taste_provider,
)
from movie_night_mediator.storage.taste_lab import SQLiteTasteLabStore
from movie_night_mediator.taste_lab import TasteLabService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--profile-id", required=True)
    parser.add_argument("--household-id", default="default-household")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    summary = TasteLabService(
        SQLiteTasteLabStore(database_path=args.database)
    ).taste_profile_summary(
        household_id=args.household_id,
        profile_id=args.profile_id,
    )
    user = UserProfile(
        user_id=args.profile_id,
        role="user_a",
        display_label=args.profile_id,
        taste_profile_evidence=summary.watchsignal_taste_evidence,
    )
    repo = Path(__file__).resolve().parents[1]
    models = repo / ".tools" / "models"
    catalog = load_movielens_catalog(models / "movielens-tmdb-catalog-v1.json")
    collaborative = load_collaborative_taste_provider(
        models / "collaborative-search-candidate.zip",
        models / "movielens-tmdb-links-v1.json",
    )
    hybrid = load_hybrid_taste_provider(
        models / "hybrid-v1.zip",
        models / "movielens-tmdb-links-v1.json",
    )
    retriever = PersonalizedCandidateRetriever(
        collaborative_provider=collaborative,
        content_provider=hybrid,
        catalog=catalog,
        minimum_profile_matches=10,
    )
    rows = retriever.retrieve(users=(user,), limit=1000)
    catalog_by_source_id = {entry.source_movie_id: entry for entry in catalog}

    def find_rank(fragment: str) -> dict[str, object] | None:
        for index, row in enumerate(rows, start=1):
            entry = catalog_by_source_id[row.source_movie_id]
            if fragment.casefold() in entry.title.casefold():
                return {
                    "rank": index,
                    "title": entry.title,
                    "sourceMovieId": entry.source_movie_id,
                    "score": row.retrieval_score,
                    "lane": row.lane,
                }
        return None

    report = {
        "profileId": args.profile_id,
        "tasteEvidenceCount": len(summary.watchsignal_taste_evidence),
        "importableEvidenceCount": sum(
            evidence.preference_value is not None
            for evidence in summary.watchsignal_taste_evidence
        ),
        "retrievedCount": len(rows),
        "scoreSpread": {
            "top": rows[0].retrieval_score if rows else None,
            "bottom": rows[-1].retrieval_score if rows else None,
            "distinctTopTen": len({row.retrieval_score for row in rows[:10]}),
        },
        "anchors": {
            "heat": find_rank("heat (1995)"),
            "aSeriousMan": find_rank("serious man"),
        },
        "superheroTitleHits": [
            catalog_by_source_id[row.source_movie_id].title
            for row in rows[:30]
            if any(
                token in catalog_by_source_id[row.source_movie_id].title.casefold()
                for token in (
                    "spider-man",
                    "supergirl",
                    "mortal kombat",
                    "super mario",
                    "avatar",
                    "avengers",
                    "batman",
                    "superman",
                )
            )
        ],
        "topThirty": [
            {
                "rank": index,
                "title": catalog_by_source_id[row.source_movie_id].title,
                "sourceMovieId": row.source_movie_id,
                "score": row.retrieval_score,
                "lane": row.lane,
            }
            for index, row in enumerate(rows[:30], start=1)
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
