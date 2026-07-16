from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from movie_night_mediator.app.safe_pick import SafePickClassifier
from movie_night_mediator.domain.models import (
    Candidate,
    HouseholdDefaults,
    MediaType,
    PersonCandidateConstraint,
    ProviderAccessType,
    ProviderAvailability,
    SessionContext,
)

TMDB_API_KEY_ENV_VAR = "TMDB_API_KEY"
TMDB_READ_ACCESS_TOKEN_ENV_VAR = "TMDB_READ_ACCESS_TOKEN"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w342"
TMDB_PRIME_VIDEO_PROVIDER_IDS = ("9", "10")
TMDB_DISCOVER_PAGE_SIZE = 20
TMDB_REQUEST_TIMEOUT_SECONDS = 8
TMDB_GENRE_IDS = {
    "action": "28",
    "adventure": "12",
    "animation": "16",
    "comedy": "35",
    "crime": "80",
    "documentary": "99",
    "drama": "18",
    "family": "10751",
    "fantasy": "14",
    "history": "36",
    "horror": "27",
    "music": "10402",
    "mystery": "9648",
    "romance": "10749",
    "sci-fi": "878",
    "science fiction": "878",
    "thriller": "53",
    "war": "10752",
    "western": "37",
}
TMDB_THEME_QUERY_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("oil", "petrol", "oil money", "oil field", "oilfield"), ("oil", "petrol", "oil industry")),
    (("greed", "greedy"), ("greed",)),
    (("capitalism", "anti-capitalist", "anti capitalist"), ("capitalism",)),
    (("money", "wealth", "tycoon"), ("money", "american dream")),
    (("religion", "church", "pastor", "preacher", "baptism"), ("religion", "church", "pastor", "baptism")),
    (("desert", "west texas", "borderland"), ("desert",)),
    (("manhunt", "hunter", "chase"), ("manhunt",)),
    (("killer", "hitman"), ("killer",)),
    (("sheriff", "lawman"), ("sheriff",)),
)


class TmdbCandidateSourceError(RuntimeError):
    pass


class TmdbCredentialsMissingError(TmdbCandidateSourceError):
    pass


class TmdbHttpClient(Protocol):
    def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
    ) -> Mapping[str, object]:
        ...


@dataclass(frozen=True)
class TmdbCandidateSourceConfig:
    api_key: str | None = None
    read_access_token: str | None = None
    base_url: str = TMDB_BASE_URL
    image_base_url: str = TMDB_IMAGE_BASE_URL
    default_provider_ids: tuple[str, ...] = TMDB_PRIME_VIDEO_PROVIDER_IDS
    default_provider_name: str = "Prime Video"
    default_region: str = "DE"
    default_language: str = "en-US"

    @classmethod
    def from_env(cls) -> TmdbCandidateSourceConfig:
        return cls(
            api_key=os.environ.get(TMDB_API_KEY_ENV_VAR),
            read_access_token=os.environ.get(TMDB_READ_ACCESS_TOKEN_ENV_VAR),
        )


class UrlopenTmdbHttpClient:
    def __init__(self, config: TmdbCandidateSourceConfig | None = None) -> None:
        self._config = config or TmdbCandidateSourceConfig.from_env()
        if not self._config.api_key and not self._config.read_access_token:
            raise TmdbCredentialsMissingError(
                "Set TMDB_READ_ACCESS_TOKEN or TMDB_API_KEY before using live TMDb."
            )

    def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
    ) -> Mapping[str, object]:
        query = dict(params or {})
        headers = {"accept": "application/json"}
        if self._config.read_access_token:
            headers["Authorization"] = f"Bearer {self._config.read_access_token}"
        else:
            query["api_key"] = self._config.api_key or ""

        url = f"{self._config.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"

        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=TMDB_REQUEST_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            raise TmdbCandidateSourceError(
                f"TMDb request failed for {path}."
            ) from error

        if not isinstance(payload, Mapping):
            raise TmdbCandidateSourceError("TMDb returned a non-object response.")
        return payload


class TmdbCandidateSource:
    def __init__(
        self,
        *,
        client: TmdbHttpClient | None = None,
        config: TmdbCandidateSourceConfig | None = None,
        classifier: SafePickClassifier | None = None,
    ) -> None:
        self._config = config or TmdbCandidateSourceConfig.from_env()
        self._client = client or UrlopenTmdbHttpClient(self._config)
        self._classifier = classifier or SafePickClassifier()
        self._movie_details_cache: dict[tuple[int, str, bool], Mapping[str, object]] = {}
        self._movie_providers_cache: dict[int, Mapping[str, object]] = {}
        self._person_id_cache: dict[tuple[str, str, str], int | None] = {}
        self._person_credits_cache: dict[tuple[int, str], tuple[Mapping[str, object], ...]] = {}
        self._keyword_id_cache: dict[str, int | None] = {}

    def fetch_candidates(
        self,
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        limit: int = 20,
    ) -> tuple[Candidate, ...]:
        if limit < 1:
            return ()

        region = (session.region or household_defaults.default_region or self._config.default_region).upper()
        language = self._config.default_language
        if session.person_constraints:
            return self._fetch_person_constrained_candidates(
                session=session,
                household_defaults=household_defaults,
                limit=limit,
                region=region,
                language=language,
            )

        provider_ids = self._provider_ids_for_session(session, household_defaults)
        discover_params = {
            "include_adult": "false",
            "include_video": "false",
            "language": language,
            "sort_by": "popularity.desc",
            "watch_region": region,
            "with_watch_monetization_types": self._watch_monetization_types_for_session(
                session,
                household_defaults,
            ),
        }
        if provider_ids:
            discover_params["with_watch_providers"] = "|".join(provider_ids)
        if genre_id := _genre_id_for_hint(session.genre_hint):
            discover_params["with_genres"] = genre_id

        candidates: list[Candidate] = []
        seen_tmdb_ids: set[int] = set()
        self._append_keyword_discover_candidates(
            candidates,
            seen_tmdb_ids,
            session=session,
            household_defaults=household_defaults,
            region=region,
            language=language,
            base_discover_params=discover_params,
            limit=limit,
        )
        if len(candidates) < limit:
            self._append_discover_candidates(
                candidates,
                seen_tmdb_ids,
                session=session,
                household_defaults=household_defaults,
                region=region,
                language=language,
                discover_params=discover_params,
                limit=limit,
            )

        return tuple(candidates)

    def _append_discover_candidates(
        self,
        candidates: list[Candidate],
        seen_tmdb_ids: set[int],
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        region: str,
        language: str,
        discover_params: Mapping[str, str],
        limit: int,
    ) -> None:
        page = 1
        while len(candidates) < limit:
            discover_payload = self._client.get_json(
                "/discover/movie",
                params={
                    **discover_params,
                    "page": str(page),
                },
            )
            results = _objects(discover_payload.get("results"))
            if not results:
                break

            for result in results:
                tmdb_id = _int_value(result.get("id"))
                if tmdb_id is None or tmdb_id in seen_tmdb_ids:
                    continue
                seen_tmdb_ids.add(tmdb_id)

                details_payload = self._movie_details(
                    tmdb_id,
                    language=language,
                    include_credits=True,
                )
                providers_payload = self._movie_providers_for_details(
                    tmdb_id,
                    details_payload,
                    session=session,
                    household_defaults=household_defaults,
                )
                candidate = self._candidate_from_payloads(
                    result,
                    details_payload,
                    providers_payload,
                    region=region,
                    session=session,
                    household_defaults=household_defaults,
                )
                if candidate is not None:
                    candidates.append(candidate)
                if len(candidates) >= limit:
                    break

            total_pages = _int_value(discover_payload.get("total_pages")) or 1
            if page >= total_pages or len(results) < TMDB_DISCOVER_PAGE_SIZE:
                break
            page += 1

    def _append_keyword_discover_candidates(
        self,
        candidates: list[Candidate],
        seen_tmdb_ids: set[int],
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        base_discover_params: Mapping[str, str],
        region: str,
        language: str,
        limit: int,
    ) -> None:
        seen_keyword_ids: set[int] = set()
        for query in _theme_keyword_queries(session.mood_text):
            if len(candidates) >= limit:
                return

            keyword_id = self._keyword_id_for_query(
                query,
                region=region,
                language=language,
            )
            if keyword_id is None or keyword_id in seen_keyword_ids:
                continue

            seen_keyword_ids.add(keyword_id)
            self._append_discover_candidates(
                candidates,
                seen_tmdb_ids,
                session=session,
                household_defaults=household_defaults,
                region=region,
                language=language,
                discover_params={
                    key: value
                    for key, value in {
                        **base_discover_params,
                        "with_keywords": str(keyword_id),
                        "with_genres": None,
                    }.items()
                    if value is not None
                },
                limit=limit,
            )

    def _fetch_person_constrained_candidates(
        self,
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        limit: int,
        region: str,
        language: str,
    ) -> tuple[Candidate, ...]:
        candidates: list[Candidate] = []
        matched_names_by_movie_id: dict[int, list[str]] = {}
        movie_ids: list[int] = []

        for constraint in session.person_constraints:
            person_id = self._person_id_for_constraint(
                constraint,
                region=region,
                language=language,
            )
            if person_id is None:
                continue

            for credit in self._person_movie_credits_for_person(
                person_id,
                language=language,
            ):
                movie_id = _int_value(credit.get("id"))
                if movie_id is None:
                    continue

                matched_names_by_movie_id.setdefault(movie_id, []).append(
                    constraint.raw_name
                )
                if movie_id not in movie_ids:
                    movie_ids.append(movie_id)

        for movie_id in movie_ids:
            details_payload = self._movie_details(
                movie_id,
                language=language,
                include_credits=False,
            )
            providers_payload = self._movie_providers_for_details(
                movie_id,
                details_payload,
                session=session,
                household_defaults=household_defaults,
            )
            candidate = self._candidate_from_payloads(
                details_payload,
                details_payload,
                providers_payload,
                region=region,
                session=session,
                household_defaults=household_defaults,
                matched_person_names=tuple(
                    dict.fromkeys(matched_names_by_movie_id.get(movie_id, ()))
                ),
            )
            if candidate is not None:
                candidates.append(candidate)
            if len(candidates) >= limit:
                break

        return tuple(candidates)

    def _person_id_for_constraint(
        self,
        constraint: PersonCandidateConstraint,
        *,
        region: str,
        language: str,
    ) -> int | None:
        if constraint.provider_person_id is not None:
            return _int_value(constraint.provider_person_id)

        cache_key = (
            constraint.raw_name.casefold(),
            region.upper(),
            language,
        )
        if cache_key in self._person_id_cache:
            return self._person_id_cache[cache_key]

        search_payload = self._client.get_json(
            "/search/person",
            params={
                "include_adult": "false",
                "language": language,
                "query": constraint.raw_name,
                "region": region,
            },
        )
        for result in _objects(search_payload.get("results")):
            person_id = _int_value(result.get("id"))
            self._person_id_cache[cache_key] = person_id
            return person_id

        self._person_id_cache[cache_key] = None
        return None

    def _keyword_id_for_query(
        self,
        query: str,
        *,
        region: str,
        language: str,
    ) -> int | None:
        cache_key = query.casefold()
        if cache_key in self._keyword_id_cache:
            return self._keyword_id_cache[cache_key]

        search_payload = self._client.get_json(
            "/search/keyword",
            params={
                "query": query,
                "page": "1",
            },
        )
        exact_match_id: int | None = None
        for result in _objects(search_payload.get("results")):
            keyword_id = _int_value(result.get("id"))
            keyword_name = _string_value(result.get("name"))
            if keyword_id is None or keyword_name is None:
                continue
            if keyword_name.casefold() == query.casefold():
                self._keyword_id_cache[cache_key] = keyword_id
                return keyword_id
            if exact_match_id is None:
                exact_match_id = keyword_id
        self._keyword_id_cache[cache_key] = exact_match_id
        return exact_match_id

    def _movie_details(
        self,
        movie_id: int,
        *,
        language: str,
        include_credits: bool,
    ) -> Mapping[str, object]:
        cache_key = (movie_id, language, include_credits)
        cached = self._movie_details_cache.get(cache_key)
        if cached is not None:
            return cached

        params = {
            "language": language,
            "append_to_response": (
                "credits,watch/providers" if include_credits else "watch/providers"
            ),
        }
        payload = self._client.get_json(
            f"/movie/{movie_id}",
            params=params,
        )
        self._movie_details_cache[cache_key] = payload
        return payload

    def _movie_providers(
        self,
        movie_id: int,
    ) -> Mapping[str, object]:
        cached = self._movie_providers_cache.get(movie_id)
        if cached is not None:
            return cached

        payload = self._client.get_json(
            f"/movie/{movie_id}/watch/providers",
        )
        self._movie_providers_cache[movie_id] = payload
        return payload

    def _movie_providers_for_details(
        self,
        movie_id: int,
        details: Mapping[str, object],
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
    ) -> Mapping[str, object]:
        embedded = details.get("watch/providers")
        if isinstance(embedded, Mapping):
            self._movie_providers_cache[movie_id] = embedded
            return embedded

        try:
            return self._movie_providers(movie_id)
        except TmdbCandidateSourceError:
            if self._provider_ids_for_session(session, household_defaults):
                raise
            return {}

    def _person_movie_credits_for_person(
        self,
        person_id: int,
        *,
        language: str,
    ) -> tuple[Mapping[str, object], ...]:
        cache_key = (person_id, language)
        cached = self._person_credits_cache.get(cache_key)
        if cached is not None:
            return cached

        credits_payload = self._client.get_json(
            f"/person/{person_id}/movie_credits",
            params={"language": language},
        )
        credits = _person_movie_credits(credits_payload)
        self._person_credits_cache[cache_key] = credits
        return credits

    def _provider_ids_for_session(
        self,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
    ) -> tuple[str, ...]:
        service = session.service_constraint or household_defaults.default_service
        if not service:
            return ()
        if "prime" in service.casefold():
            return self._config.default_provider_ids
        return ()

    def _watch_monetization_types_for_session(
        self,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
    ) -> str:
        service = session.service_constraint or household_defaults.default_service or ""
        if "prime" in service.casefold():
            return "|".join(
                (
                    ProviderAccessType.FLATRATE.value,
                    ProviderAccessType.RENT.value,
                    ProviderAccessType.BUY.value,
                )
            )
        return ProviderAccessType.FLATRATE.value

    def _candidate_from_payloads(
        self,
        result: Mapping[str, object],
        details: Mapping[str, object],
        providers: Mapping[str, object],
        *,
        region: str,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        matched_person_names: tuple[str, ...] = (),
    ) -> Candidate | None:
        tmdb_id = _int_value(details.get("id")) or _int_value(result.get("id"))
        title = _string_value(details.get("title")) or _string_value(result.get("title"))
        if tmdb_id is None or title is None:
            return None

        provider_availability = _provider_availability_for_region(providers, region=region)
        candidate = Candidate(
            source_movie_id=f"tmdb:{tmdb_id}",
            title=title,
            media_type=MediaType.MOVIE,
            release_year=_release_year(
                _string_value(details.get("release_date"))
                or _string_value(result.get("release_date"))
            ),
            runtime_min=_int_value(details.get("runtime")),
            poster_url=_poster_url(
                self._config.image_base_url,
                _string_value(details.get("poster_path"))
                or _string_value(result.get("poster_path")),
            ),
            genres=_genre_names(details),
            overview=_string_value(details.get("overview"))
            or _string_value(result.get("overview"))
            or "",
            top_cast=_top_cast_names(details.get("credits")),
            providers=tuple(
                dict.fromkeys(
                    availability.provider_name for availability in provider_availability
                )
            ),
            provider_availability=provider_availability,
            original_language=_string_value(details.get("original_language"))
            or _string_value(result.get("original_language"))
            or "und",
            spoken_languages=_spoken_language_codes(details),
            english_subtitles_verified=False,
            matched_person_names=matched_person_names,
        )
        classification = self._classifier.classify(
            candidate,
            session=session,
            household_defaults=household_defaults,
        )
        return replace(candidate, safety_status=classification.status)

def _provider_availability_for_region(
    providers: Mapping[str, object],
    *,
    region: str,
) -> tuple[ProviderAvailability, ...]:
    results = providers.get("results")
    if not isinstance(results, Mapping):
        return ()

    region_payload = results.get(region.upper())
    if not isinstance(region_payload, Mapping):
        return ()

    availability: list[ProviderAvailability] = []
    seen: set[tuple[str, ProviderAccessType, str]] = set()
    for bucket, access_type in (
        ("flatrate", ProviderAccessType.FLATRATE),
        ("rent", ProviderAccessType.RENT),
        ("buy", ProviderAccessType.BUY),
    ):
        for provider in _objects(region_payload.get(bucket)):
            provider_name = _string_value(provider.get("provider_name"))
            if provider_name is None:
                continue
            key = (provider_name, access_type, region.upper())
            if key in seen:
                continue
            seen.add(key)
            availability.append(
                ProviderAvailability(
                    provider_name=provider_name,
                    access_type=access_type,
                    region=region.upper(),
                )
            )
    return tuple(availability)


def _genre_id_for_hint(genre_hint: str | None) -> str | None:
    if not genre_hint:
        return None
    return TMDB_GENRE_IDS.get(genre_hint.strip().casefold())


def _theme_keyword_queries(mood_text: str | None) -> tuple[str, ...]:
    if not mood_text:
        return ()
    lowered = mood_text.casefold()
    queries: list[str] = []
    for cues, keyword_queries in TMDB_THEME_QUERY_RULES:
        if any(cue in lowered for cue in cues):
            queries.extend(keyword_queries)
    return tuple(dict.fromkeys(queries))


def _genre_names(details: Mapping[str, object]) -> tuple[str, ...]:
    return tuple(
        name
        for genre in _objects(details.get("genres"))
        if (name := _string_value(genre.get("name"))) is not None
    )


def _person_movie_credits(
    credits: Mapping[str, object],
) -> tuple[Mapping[str, object], ...]:
    results: list[Mapping[str, object]] = []
    seen_movie_ids: set[int] = set()
    for credit in (*_objects(credits.get("cast")), *_objects(credits.get("crew"))):
        movie_id = _int_value(credit.get("id"))
        if movie_id is None or movie_id in seen_movie_ids:
            continue
        seen_movie_ids.add(movie_id)
        results.append(credit)

    return tuple(results)


def _top_cast_names(credits: object) -> tuple[str, ...]:
    if not isinstance(credits, Mapping):
        return ()

    names: list[str] = []
    for credit in _objects(credits.get("cast")):
        name = _string_value(credit.get("name"))
        if name is None:
            continue
        names.append(name)
        if len(names) >= 3:
            break

    return tuple(names)


def _spoken_language_codes(details: Mapping[str, object]) -> tuple[str, ...]:
    codes = tuple(
        code
        for language in _objects(details.get("spoken_languages"))
        if (code := _string_value(language.get("iso_639_1"))) is not None
    )
    return codes or ("und",)


def _poster_url(image_base_url: str, poster_path: str | None) -> str | None:
    if poster_path is None:
        return None
    normalized_path = poster_path.strip()
    if not normalized_path:
        return None
    if normalized_path.startswith("http://") or normalized_path.startswith("https://"):
        return normalized_path
    return f"{image_base_url.rstrip('/')}/{normalized_path.lstrip('/')}"


def _objects(value: object) -> tuple[Mapping[str, object], ...]:
    if not isinstance(value, list):
        return ()
    return tuple(item for item in value if isinstance(item, Mapping))


def _string_value(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _int_value(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _release_year(release_date: str | None) -> int | None:
    if release_date is None or len(release_date) < 4:
        return None
    year = release_date[:4]
    if not year.isdigit():
        return None
    return int(year)
