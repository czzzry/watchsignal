from __future__ import annotations

import re
from collections.abc import Mapping

from movie_night_mediator.domain import (
    MediaType,
    TitleResolutionCandidate,
    TitleResolutionEntry,
    TitleSearchResult,
)


DEFAULT_TMDB_TITLE_FIXTURES: tuple[TitleResolutionCandidate, ...] = (
    TitleResolutionCandidate(
        source="tmdb",
        source_id="603",
        title="The Matrix",
        media_type=MediaType.MOVIE,
        release_year=1999,
        overview="A hacker discovers reality is stranger than it looks.",
        original_language="en",
        popularity=83.1,
    ),
    TitleResolutionCandidate(
        source="tmdb",
        source_id="348",
        title="Alien",
        media_type=MediaType.MOVIE,
        release_year=1979,
        overview="A deep space crew answers a distress signal.",
        original_language="en",
        popularity=58.2,
    ),
    TitleResolutionCandidate(
        source="tmdb",
        source_id="679",
        title="Aliens",
        media_type=MediaType.MOVIE,
        release_year=1986,
        overview="A survivor returns to face the creatures again.",
        original_language="en",
        popularity=61.4,
    ),
    TitleResolutionCandidate(
        source="tmdb",
        source_id="105",
        title="Back to the Future",
        media_type=MediaType.MOVIE,
        release_year=1985,
        overview="A teenager is accidentally sent thirty years into the past.",
        original_language="en",
        popularity=45.5,
    ),
)


DEFAULT_TMDB_QUERY_ALIASES: Mapping[str, tuple[str, ...]] = {
    "the matrx": ("tmdb:603",),
    "matrix": ("tmdb:603",),
    "alien": ("tmdb:348", "tmdb:679"),
}


class FixtureTmdbTitleResolver:
    """Deterministic TMDb-shaped resolver for tests and local development."""

    def __init__(
        self,
        candidates: tuple[TitleResolutionCandidate, ...] = DEFAULT_TMDB_TITLE_FIXTURES,
        aliases: Mapping[str, tuple[str, ...]] = DEFAULT_TMDB_QUERY_ALIASES,
    ) -> None:
        self._candidates = candidates
        self._aliases = aliases
        self._candidates_by_source_movie_id = {
            candidate.source_movie_id: candidate for candidate in candidates
        }

    def search(
        self,
        query: str,
        *,
        region: str = "DE",
        language: str = "en-US",
    ) -> TitleSearchResult:
        normalized_query = normalize_title_query(query)
        if not normalized_query:
            return TitleSearchResult(raw_query=query)

        aliased_ids = self._aliases.get(normalized_query)
        if aliased_ids is not None:
            return TitleSearchResult(
                raw_query=query,
                candidates=tuple(
                    self._candidates_by_source_movie_id[source_movie_id]
                    for source_movie_id in aliased_ids
                    if source_movie_id in self._candidates_by_source_movie_id
                ),
            )

        candidates = tuple(
            candidate
            for candidate in self._candidates
            if normalized_query in normalize_title_query(candidate.title)
        )
        return TitleSearchResult(raw_query=query, candidates=candidates)

    def resolve(
        self,
        query: str,
        *,
        selected_source_movie_id: str | None = None,
        region: str = "DE",
        language: str = "en-US",
    ) -> TitleResolutionEntry:
        search_result = self.search(query, region=region, language=language)

        if selected_source_movie_id is not None:
            selected_candidate = next(
                (
                    candidate
                    for candidate in search_result.candidates
                    if candidate.source_movie_id == selected_source_movie_id
                ),
                None,
            )
            if selected_candidate is not None:
                return TitleResolutionEntry.resolved(query, selected_candidate)

            return TitleResolutionEntry.unresolved(query, reason="candidate_not_found")

        if len(search_result.candidates) == 1:
            return TitleResolutionEntry.resolved(query, search_result.candidates[0])

        reason = "ambiguous_match" if search_result.candidates else "no_match"
        return TitleResolutionEntry.unresolved(query, reason=reason)


def normalize_title_query(query: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", query.lower())).strip()
