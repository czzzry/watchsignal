from __future__ import annotations

from movie_night_mediator.domain.models import (
    AudienceMode,
    Candidate,
    HouseholdDefaults,
    MediaType,
    OnboardingSeed,
    ProviderAccessType,
    ProviderAvailability,
    ScoringRequest,
    SessionContext,
    SessionMode,
    UserProfile,
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

PRIME_DE_FLATRATE = ProviderAvailability(
    provider_name="Prime Video",
    access_type=ProviderAccessType.FLATRATE,
    region="DE",
)

AMAZON_DE_RENT = ProviderAvailability(
    provider_name="Amazon Video",
    access_type=ProviderAccessType.RENT,
    region="DE",
)

DEMO_CANDIDATES = (
    Candidate(
        source_movie_id="fixture:shared-time-loop",
        title="Shared Time Loop",
        media_type=MediaType.MOVIE,
        release_year=2024,
        runtime_min=108,
        genres=("Comedy", "Sci-Fi"),
        providers=("Prime Video",),
        provider_availability=(PRIME_DE_FLATRATE,),
        original_language="en",
        spoken_languages=("en",),
        is_interesting_safe_pick=True,
    ),
    Candidate(
        source_movie_id="fixture:quiet-investigation",
        title="Quiet Investigation",
        media_type=MediaType.MOVIE,
        release_year=2023,
        runtime_min=116,
        genres=("Drama", "Mystery"),
        providers=("Prime Video",),
        provider_availability=(PRIME_DE_FLATRATE,),
        original_language="en",
        spoken_languages=("en",),
    ),
    Candidate(
        source_movie_id="fixture:already-watched-classic",
        title="Already Watched Classic",
        media_type=MediaType.MOVIE,
        release_year=1999,
        runtime_min=136,
        genres=("Action", "Sci-Fi"),
        providers=("Prime Video",),
        provider_availability=(PRIME_DE_FLATRATE,),
        original_language="en",
        spoken_languages=("en",),
        already_watched=True,
    ),
    Candidate(
        source_movie_id="fixture:rent-only-thriller",
        title="Rent Only Thriller",
        media_type=MediaType.MOVIE,
        release_year=2022,
        runtime_min=104,
        genres=("Thriller", "Mystery"),
        providers=("Amazon Video",),
        provider_availability=(AMAZON_DE_RENT,),
        original_language="en",
        spoken_languages=("en",),
    ),
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

