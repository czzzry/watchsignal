from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Protocol
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from movie_night_mediator.app.safe_pick import SafePickClassifier
from movie_night_mediator.domain.models import (
    Candidate,
    HouseholdDefaults,
    MediaType,
    ProviderAccessType,
    ProviderAvailability,
    SessionContext,
)

TMDB_API_KEY_ENV_VAR = "TMDB_API_KEY"
TMDB_READ_ACCESS_TOKEN_ENV_VAR = "TMDB_READ_ACCESS_TOKEN"
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w342"
TMDB_PRIME_VIDEO_PROVIDER_ID = "9"


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
    default_provider_id: str = TMDB_PRIME_VIDEO_PROVIDER_ID
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
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))

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
        provider_id = self._provider_id_for_session(session, household_defaults)
        discover_params = {
            "include_adult": "false",
            "include_video": "false",
            "language": language,
            "page": "1",
            "sort_by": "popularity.desc",
            "watch_region": region,
            "with_watch_monetization_types": ProviderAccessType.FLATRATE.value,
        }
        if provider_id:
            discover_params["with_watch_providers"] = provider_id

        discover_payload = self._client.get_json(
            "/discover/movie",
            params=discover_params,
        )
        candidates: list[Candidate] = []
        for result in _objects(discover_payload.get("results")):
            tmdb_id = _int_value(result.get("id"))
            if tmdb_id is None:
                continue

            details_payload = self._client.get_json(
                f"/movie/{tmdb_id}",
                params={"language": language},
            )
            providers_payload = self._client.get_json(
                f"/movie/{tmdb_id}/watch/providers",
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

        return tuple(candidates)

    def _provider_id_for_session(
        self,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
    ) -> str:
        service = session.service_constraint or household_defaults.default_service
        if not service:
            return ""
        if "prime" in service.casefold():
            return self._config.default_provider_id
        return ""

    def _candidate_from_payloads(
        self,
        result: Mapping[str, object],
        details: Mapping[str, object],
        providers: Mapping[str, object],
        *,
        region: str,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
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


def _genre_names(details: Mapping[str, object]) -> tuple[str, ...]:
    return tuple(
        name
        for genre in _objects(details.get("genres"))
        if (name := _string_value(genre.get("name"))) is not None
    )


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
