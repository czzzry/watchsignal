from __future__ import annotations

from movie_night_mediator.domain.models import (
    AudienceMode,
    Candidate,
    HouseholdDefaults,
    OnboardingSeed,
    ProviderAccessType,
    RankedCandidate,
    ScoringRequest,
    SessionContext,
    SessionMode,
    UserProfile,
)
from movie_night_mediator.fixtures.candidate_adapter import (
    FixtureCandidate,
    FixtureProviderAvailability,
    fixture_candidates_to_domain,
    fixture_candidates_to_shortlist,
)

DEMO_HOUSEHOLD_DEFAULTS = HouseholdDefaults(
    default_region="DE",
    default_service="Prime Video",
    default_language_mode="english_or_english_subtitles",
    rewatch_avoidance_default=True,
)

DEMO_HUSBAND_PROFILE = UserProfile(
    user_id="husband",
    role="husband",
    display_label="Husband",
    onboarding_seeds=(
        OnboardingSeed(
            title="The Matrix",
            label="loved",
            genres=("Action", "Sci-Fi"),
        ),
        OnboardingSeed(
            title="Arrival",
            label="fine",
            genres=("Drama", "Sci-Fi"),
        ),
        OnboardingSeed(
            title="The Notebook",
            label="no",
            genres=("Romance",),
        ),
    ),
)

DEMO_WIFE_PROFILE = UserProfile(
    user_id="wife",
    role="wife",
    display_label="Wife",
    onboarding_seeds=(
        OnboardingSeed(
            title="Knives Out",
            label="loved",
            genres=("Comedy", "Mystery"),
        ),
        OnboardingSeed(
            title="Arrival",
            label="fine",
            genres=("Drama", "Sci-Fi"),
        ),
        OnboardingSeed(
            title="John Wick",
            label="no",
            genres=("Action",),
        ),
    ),
    horror_exclusion=True,
)

DEMO_SHARED_SESSION = SessionContext(
    session_id="demo-shared-couple",
    audience_mode=AudienceMode.SHARED,
    session_mode=SessionMode.COMPROMISE,
    viewer_user_ids=(DEMO_HUSBAND_PROFILE.user_id, DEMO_WIFE_PROFILE.user_id),
    region="DE",
    service_constraint="Prime Video",
    language_constraint="english_or_english_subtitles",
)

DEMO_CANDIDATE_FIXTURES = (
    FixtureCandidate(
        source_movie_id="fixture:shared-time-loop",
        title="Shared Time Loop",
        release_year=2024,
        runtime_min=108,
        genres=("Comedy", "Sci-Fi"),
        poster_url="https://image.tmdb.org/t/p/w342/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg",
        tone="Funny, high-concept, easy to start",
        reason="A lively compromise pick with a clear hook and enough momentum for both viewers.",
        provider_availability=(
            FixtureProviderAvailability(
                provider_name="Prime Video",
                access_type=ProviderAccessType.FLATRATE,
                region="DE",
            ),
        ),
        original_language="en",
        spoken_languages=("en",),
        is_interesting_safe_pick=True,
    ),
    FixtureCandidate(
        source_movie_id="fixture:quiet-investigation",
        title="Quiet Investigation",
        release_year=2023,
        runtime_min=116,
        genres=("Drama", "Mystery"),
        poster_url="https://image.tmdb.org/t/p/w342/pThyQovXQrw2m0s9x82twj48Jq4.jpg",
        tone="Clever, grounded, low-chaos",
        reason="A steady mystery option that keeps the compromise lane readable and calm.",
        provider_availability=(
            FixtureProviderAvailability(
                provider_name="Prime Video",
                access_type=ProviderAccessType.FLATRATE,
                region="DE",
            ),
        ),
        original_language="en",
        spoken_languages=("en",),
    ),
    FixtureCandidate(
        source_movie_id="fixture:subtitled-family-mystery",
        title="Subtitled Family Mystery",
        release_year=2021,
        runtime_min=101,
        genres=("Family", "Mystery"),
        poster_url="https://image.tmdb.org/t/p/w342/k3waqVXSnvCZWfJYNtdamTgTtTA.jpg",
        tone="Warm, curious, subtitle-friendly",
        reason="The subtitle-safe wildcard that still stays gentle enough for a relaxed night.",
        provider_availability=(
            FixtureProviderAvailability(
                provider_name="Prime Video",
                access_type=ProviderAccessType.FLATRATE,
                region="DE",
            ),
        ),
        original_language="de",
        spoken_languages=("de",),
        english_subtitles_verified=True,
    ),
    FixtureCandidate(
        source_movie_id="fixture:english-dubbed-adventure",
        title="English Dubbed Adventure",
        release_year=2020,
        runtime_min=94,
        genres=("Adventure", "Family"),
        poster_url="https://image.tmdb.org/t/p/w342/eWdyYQreja6JGCzqHWXpWHDrrPo.jpg",
        tone="Brisk, light, dubbed comfort watch",
        reason="An easy-start adventure with explicit English audio support in the fixture data.",
        provider_availability=(
            FixtureProviderAvailability(
                provider_name="Prime Video",
                access_type=ProviderAccessType.FLATRATE,
                region="DE",
            ),
        ),
        original_language="fr",
        spoken_languages=("fr", "en"),
    ),
    FixtureCandidate(
        source_movie_id="fixture:thoughtful-space-walk",
        title="Thoughtful Space Walk",
        release_year=2025,
        runtime_min=112,
        genres=("Drama", "Sci-Fi"),
        poster_url="https://image.tmdb.org/t/p/w342/uUHvlkLavotfGsNtosDy8ShsIYF.jpg",
        tone="Thoughtful, spacious, emotional",
        reason="A reflective sci-fi choice with enough overlap to stay near the top of the shortlist.",
        provider_availability=(
            FixtureProviderAvailability(
                provider_name="Prime Video",
                access_type=ProviderAccessType.FLATRATE,
                region="DE",
            ),
        ),
        original_language="en",
        spoken_languages=("en",),
    ),
    FixtureCandidate(
        source_movie_id="fixture:gentle-puzzle-box",
        title="Gentle Puzzle Box",
        release_year=2024,
        runtime_min=103,
        genres=("Comedy", "Mystery"),
        poster_url="https://image.tmdb.org/t/p/w342/pThyQovXQrw2m0s9x82twj48Jq4.jpg",
        tone="Playful, tidy, low homework",
        reason="A lighter mystery that keeps the shortlist varied without pushing either viewer too far.",
        provider_availability=(
            FixtureProviderAvailability(
                provider_name="Prime Video",
                access_type=ProviderAccessType.FLATRATE,
                region="DE",
            ),
        ),
        original_language="en",
        spoken_languages=("en",),
    ),
    FixtureCandidate(
        source_movie_id="fixture:unverified-language-drama",
        title="Unverified Language Drama",
        release_year=2022,
        runtime_min=99,
        genres=("Drama",),
        provider_availability=(
            FixtureProviderAvailability(
                provider_name="Prime Video",
                access_type=ProviderAccessType.FLATRATE,
                region="DE",
            ),
        ),
        original_language="ja",
        spoken_languages=("ja",),
    ),
    FixtureCandidate(
        source_movie_id="fixture:already-watched-classic",
        title="Already Watched Classic",
        release_year=1999,
        runtime_min=136,
        genres=("Action", "Sci-Fi"),
        provider_availability=(
            FixtureProviderAvailability(
                provider_name="Prime Video",
                access_type=ProviderAccessType.FLATRATE,
                region="DE",
            ),
        ),
        original_language="en",
        spoken_languages=("en",),
        already_watched=True,
    ),
    FixtureCandidate(
        source_movie_id="fixture:rent-only-thriller",
        title="Rent Only Thriller",
        release_year=2022,
        runtime_min=104,
        genres=("Thriller", "Mystery"),
        provider_availability=(
            FixtureProviderAvailability(
                provider_name="Amazon Video",
                access_type=ProviderAccessType.RENT,
                region="DE",
            ),
        ),
        original_language="en",
        spoken_languages=("en",),
    ),
)

DEMO_CANDIDATES = fixture_candidates_to_domain(
    DEMO_CANDIDATE_FIXTURES,
    session=DEMO_SHARED_SESSION,
    household_defaults=DEMO_HOUSEHOLD_DEFAULTS,
)


def demo_scoring_request(
    candidates: tuple[Candidate, ...] = DEMO_CANDIDATES,
) -> ScoringRequest:
    return ScoringRequest(
        session=DEMO_SHARED_SESSION,
        household_defaults=DEMO_HOUSEHOLD_DEFAULTS,
        users=(DEMO_HUSBAND_PROFILE, DEMO_WIFE_PROFILE),
        candidates=candidates,
    )


def demo_candidate_shortlist(limit: int = 5) -> tuple[RankedCandidate, ...]:
    return fixture_candidates_to_shortlist(
        DEMO_CANDIDATE_FIXTURES,
        session=DEMO_SHARED_SESSION,
        household_defaults=DEMO_HOUSEHOLD_DEFAULTS,
        users=(DEMO_HUSBAND_PROFILE, DEMO_WIFE_PROFILE),
        limit=limit,
    )
