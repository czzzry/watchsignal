#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.adapters import TmdbCandidateSource  # noqa: E402
from movie_night_mediator.app.shortlist import get_candidate_source_shortlist  # noqa: E402
from movie_night_mediator.domain import AudienceMode, HouseholdDefaults, SessionContext  # noqa: E402
from movie_night_mediator.fixtures.demo_couple import (  # noqa: E402
    DEMO_HUSBAND_PROFILE,
    DEMO_WIFE_PROFILE,
)


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    load_env(REPO_ROOT / ".env")
    session = SessionContext(
        session_id="live-tmdb-candidate-smoke",
        audience_mode=AudienceMode.SHARED,
        viewer_user_ids=("husband", "wife"),
        region="DE",
        service_constraint="Prime Video",
    )
    defaults = HouseholdDefaults()
    source = TmdbCandidateSource()

    candidates = source.fetch_candidates(
        session=session,
        household_defaults=defaults,
        limit=10,
    )
    shortlist = get_candidate_source_shortlist(
        source,
        session=session,
        household_defaults=defaults,
        users=(DEMO_HUSBAND_PROFILE, DEMO_WIFE_PROFILE),
        limit=5,
        candidate_limit=20,
    )

    print(
        json.dumps(
            {
                "candidateCount": len(candidates),
                "safePickCount": sum(
                    1
                    for candidate in candidates
                    if candidate.safety_status == "safe_pick"
                ),
                "shortlist": [
                    {
                        "sourceMovieId": candidate.source_movie_id,
                        "title": candidate.title,
                        "candidateRank": candidate.candidate_rank,
                        "groupScore": candidate.group_score,
                    }
                    for candidate in shortlist
                ],
            },
            indent=2,
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
