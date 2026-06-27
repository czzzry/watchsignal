from __future__ import annotations

from dataclasses import dataclass, replace

from movie_night_mediator.app.safe_pick import SafePickClassifier
from movie_night_mediator.domain.models import (
    Candidate,
    HouseholdDefaults,
    MediaType,
    ProviderAccessType,
    ProviderAvailability,
    RankedCandidate,
    ScoringRequest,
    SessionContext,
    UserProfile,
)
from movie_night_mediator.scoring import HeuristicScorer


@dataclass(frozen=True)
class FixtureProviderAvailability:
    provider_name: str
    access_type: ProviderAccessType
    region: str = "DE"


@dataclass(frozen=True)
class FixtureCandidate:
    source_movie_id: str
    title: str
    media_type: MediaType = MediaType.MOVIE
    release_year: int | None = None
    runtime_min: int | None = None
    genres: tuple[str, ...] = ()
    overview: str = ""
    provider_availability: tuple[FixtureProviderAvailability, ...] = ()
    original_language: str = "en"
    spoken_languages: tuple[str, ...] = ("en",)
    english_subtitles_verified: bool = False
    already_watched: bool = False
    is_interesting_safe_pick: bool = False


def fixture_candidate_to_domain(
    fixture: FixtureCandidate,
    *,
    session: SessionContext,
    household_defaults: HouseholdDefaults,
    classifier: SafePickClassifier | None = None,
) -> Candidate:
    provider_availability = tuple(
        ProviderAvailability(
            provider_name=availability.provider_name,
            access_type=availability.access_type,
            region=availability.region,
        )
        for availability in fixture.provider_availability
    )
    candidate = Candidate(
        source_movie_id=fixture.source_movie_id,
        title=fixture.title,
        media_type=fixture.media_type,
        release_year=fixture.release_year,
        runtime_min=fixture.runtime_min,
        genres=fixture.genres,
        overview=fixture.overview,
        providers=tuple(
            dict.fromkeys(
                availability.provider_name for availability in provider_availability
            )
        ),
        provider_availability=provider_availability,
        original_language=fixture.original_language,
        spoken_languages=fixture.spoken_languages,
        english_subtitles_verified=fixture.english_subtitles_verified,
        already_watched=fixture.already_watched,
        is_interesting_safe_pick=fixture.is_interesting_safe_pick,
    )
    classification = (classifier or SafePickClassifier()).classify(
        candidate,
        session=session,
        household_defaults=household_defaults,
    )
    return replace(candidate, safety_status=classification.status)


def fixture_candidates_to_domain(
    fixtures: tuple[FixtureCandidate, ...],
    *,
    session: SessionContext,
    household_defaults: HouseholdDefaults,
    classifier: SafePickClassifier | None = None,
) -> tuple[Candidate, ...]:
    resolved_classifier = classifier or SafePickClassifier()
    return tuple(
        fixture_candidate_to_domain(
            fixture,
            session=session,
            household_defaults=household_defaults,
            classifier=resolved_classifier,
        )
        for fixture in fixtures
    )


def fixture_candidates_to_shortlist(
    fixtures: tuple[FixtureCandidate, ...],
    *,
    session: SessionContext,
    household_defaults: HouseholdDefaults,
    users: tuple[UserProfile, ...],
    limit: int = 5,
    classifier: SafePickClassifier | None = None,
    scorer: HeuristicScorer | None = None,
) -> tuple[RankedCandidate, ...]:
    candidates = fixture_candidates_to_domain(
        fixtures,
        session=session,
        household_defaults=household_defaults,
        classifier=classifier,
    )
    result = (scorer or HeuristicScorer()).score(
        ScoringRequest(
            session=session,
            household_defaults=household_defaults,
            users=users,
            candidates=candidates,
        )
    )
    return result.ranked_candidates[:limit]
