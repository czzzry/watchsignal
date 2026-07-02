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
        source_movie_id="arrival",
        title="Arrival",
        release_year=2016,
        runtime_min=116,
        genres=("Drama", "Sci-Fi"),
        poster_url="https://image.tmdb.org/t/p/w342/x2FJsf1ElAgr63Y3PNPtJrcmpoe.jpg",
        tone="Smart, tense, emotional",
        reason="When mysterious spacecraft land around the world, a linguist is recruited to figure out whether the visitors come in peace before fear wins.",
        top_cast=("Amy Adams", "Jeremy Renner", "Forest Whitaker"),
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
        source_movie_id="knives-out",
        title="Knives Out",
        release_year=2019,
        runtime_min=131,
        genres=("Comedy", "Mystery"),
        poster_url="https://image.tmdb.org/t/p/w342/pThyQovXQrw2m0s9x82twj48Jq4.jpg",
        tone="Funny, clever, low homework",
        reason="A master detective picks through a wildly petty rich family after the family patriarch turns up dead right after his birthday party.",
        top_cast=("Daniel Craig", "Ana de Armas", "Chris Evans"),
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
        source_movie_id="past-lives",
        title="Past Lives",
        release_year=2023,
        runtime_min=106,
        genres=("Drama", "Romance"),
        poster_url="https://image.tmdb.org/t/p/w342/k3waqVXSnvCZWfJYNtdamTgTtTA.jpg",
        tone="Quiet, romantic, reflective",
        reason="Two childhood friends reconnect decades later and spend one week testing what was fate, what was choice, and what still lingers between them.",
        top_cast=("Greta Lee", "Teo Yoo", "John Magaro"),
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
        source_movie_id="the-grand-budapest-hotel",
        title="The Grand Budapest Hotel",
        release_year=2014,
        runtime_min=100,
        genres=("Comedy", "Adventure"),
        poster_url="https://image.tmdb.org/t/p/w342/eWdyYQreja6JGCzqHWXpWHDrrPo.jpg",
        tone="Stylized, charming, brisk",
        reason="A legendary concierge and his anxious lobby boy are swept into murder, inheritance chaos, and a ridiculously elegant chase across Europe.",
        top_cast=("Ralph Fiennes", "Tony Revolori", "Saoirse Ronan"),
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
        source_movie_id="edge-of-tomorrow",
        title="Edge of Tomorrow",
        release_year=2014,
        runtime_min=113,
        genres=("Action", "Sci-Fi"),
        poster_url="https://image.tmdb.org/t/p/w342/uUHvlkLavotfGsNtosDy8ShsIYF.jpg",
        tone="Fast, funny, action-heavy",
        reason="A smug officer gets trapped in a time loop on the worst battlefield imaginable and has to die, learn, and improve his way toward survival.",
        top_cast=("Tom Cruise", "Emily Blunt", "Bill Paxton"),
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
    FixtureCandidate(
        source_movie_id="little-miss-sunshine",
        title="Little Miss Sunshine",
        release_year=2006,
        runtime_min=102,
        genres=("Comedy", "Drama"),
        tone="Warm, awkward, bittersweet",
        reason="A chaotic family piles into a van for a kid's pageant and somehow turns dysfunction into tenderness.",
        top_cast=("Abigail Breslin", "Greg Kinnear", "Toni Collette"),
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
        source_movie_id="the-martian",
        title="The Martian",
        release_year=2015,
        runtime_min=141,
        genres=("Adventure", "Comedy", "Sci-Fi"),
        tone="Optimistic, nerdy, propulsive",
        reason="A stranded astronaut tries to science his way home while everyone else races to solve the impossible.",
        top_cast=("Matt Damon", "Jessica Chastain", "Chiwetel Ejiofor"),
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
        source_movie_id="ocean-s-eleven",
        title="Ocean's Eleven",
        release_year=2001,
        runtime_min=116,
        genres=("Comedy", "Crime"),
        tone="Slick, breezy, stylish",
        reason="A relaxed crew of experts tries to rob three Las Vegas casinos with charm, timing, and very little visible panic.",
        top_cast=("George Clooney", "Brad Pitt", "Julia Roberts"),
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
        source_movie_id="source-code",
        title="Source Code",
        release_year=2011,
        runtime_min=94,
        genres=("Mystery", "Sci-Fi", "Thriller"),
        tone="Tense, compact, puzzle-box",
        reason="A soldier wakes up in someone else's body and has minutes to solve a train bombing before the loop resets.",
        top_cast=("Jake Gyllenhaal", "Michelle Monaghan", "Vera Farmiga"),
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
        source_movie_id="school-of-rock",
        title="School of Rock",
        release_year=2003,
        runtime_min=110,
        genres=("Comedy", "Music"),
        tone="Loose, goofy, high-energy",
        reason="A broke musician fakes his way into a substitute teaching job and turns a class into a rock band.",
        top_cast=("Jack Black", "Joan Cusack", "Mike White"),
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
)

INITIAL_DEMO_CANDIDATE_FIXTURES = DEMO_CANDIDATE_FIXTURES[:8]

DEMO_CANDIDATES = fixture_candidates_to_domain(
    DEMO_CANDIDATE_FIXTURES,
    session=DEMO_SHARED_SESSION,
    household_defaults=DEMO_HOUSEHOLD_DEFAULTS,
)

INITIAL_DEMO_CANDIDATES = fixture_candidates_to_domain(
    INITIAL_DEMO_CANDIDATE_FIXTURES,
    session=DEMO_SHARED_SESSION,
    household_defaults=DEMO_HOUSEHOLD_DEFAULTS,
)


def demo_scoring_request(
    candidates: tuple[Candidate, ...] = INITIAL_DEMO_CANDIDATES,
) -> ScoringRequest:
    return ScoringRequest(
        session=DEMO_SHARED_SESSION,
        household_defaults=DEMO_HOUSEHOLD_DEFAULTS,
        users=(DEMO_HUSBAND_PROFILE, DEMO_WIFE_PROFILE),
        candidates=candidates,
    )


def demo_candidate_shortlist(limit: int = 5) -> tuple[RankedCandidate, ...]:
    return fixture_candidates_to_shortlist(
        INITIAL_DEMO_CANDIDATE_FIXTURES,
        session=DEMO_SHARED_SESSION,
        household_defaults=DEMO_HOUSEHOLD_DEFAULTS,
        users=(DEMO_HUSBAND_PROFILE, DEMO_WIFE_PROFILE),
        limit=limit,
    )
