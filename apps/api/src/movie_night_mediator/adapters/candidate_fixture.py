from __future__ import annotations

from movie_night_mediator.domain.models import Candidate, MediaType


def load_fixture_candidates() -> tuple[Candidate, ...]:
    return (
        Candidate(
            source_movie_id="tmdb:603",
            title="The Matrix",
            media_type=MediaType.MOVIE,
            release_year=1999,
            runtime_min=136,
            genres=("Action", "Sci-Fi"),
            providers=("Prime Video",),
            overview="A hacker discovers reality is stranger than it looks.",
        ),
        Candidate(
            source_movie_id="tmdb:105",
            title="Back to the Future",
            media_type=MediaType.MOVIE,
            release_year=1985,
            runtime_min=116,
            genres=("Adventure", "Comedy", "Sci-Fi"),
            providers=("Prime Video",),
            overview="A teenager is accidentally sent thirty years into the past.",
        ),
        Candidate(
            source_movie_id="tmdb:694",
            title="The Shining",
            media_type=MediaType.MOVIE,
            release_year=1980,
            runtime_min=144,
            genres=("Horror", "Thriller"),
            providers=("Prime Video",),
            overview="A family's isolated winter turns terrifying.",
        ),
    )

