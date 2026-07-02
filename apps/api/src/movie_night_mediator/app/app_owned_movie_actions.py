from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from movie_night_mediator.app.backfill import ManualBackfillService
from movie_night_mediator.domain import (
    BackfillTasteLabel,
    MediaType,
    TitleResolutionCandidate,
    TitleResolutionEntry,
    WatchedTitleBackfill,
)


@dataclass(frozen=True)
class AppOwnedProfileRating:
    profile_id: str
    taste_label: BackfillTasteLabel


class AppOwnedMovieActionService:
    def __init__(self, backfill_service: ManualBackfillService) -> None:
        self.backfill_service = backfill_service

    def mark_watched(
        self,
        *,
        household_id: str,
        source_movie_id: str,
        title: str,
        profile_ratings: tuple[AppOwnedProfileRating, ...] = (),
        watched_on: date | None = None,
    ) -> tuple[WatchedTitleBackfill, ...]:
        entry = _entry_for_app_owned_movie(
            source_movie_id=source_movie_id,
            title=title,
        )
        records = list(
            self.backfill_service.add_watched_title(
                household_id=household_id,
                entry=entry,
                include_global=True,
                watched_on=watched_on,
            )
        )

        for rating in _dedupe_profile_ratings(profile_ratings):
            records.extend(
                self.backfill_service.add_watched_title(
                    household_id=household_id,
                    entry=entry,
                    participant_ids=(rating.profile_id,),
                    watched_on=watched_on,
                    taste_label=rating.taste_label,
                )
            )

        return tuple(records)


def _entry_for_app_owned_movie(
    *,
    source_movie_id: str,
    title: str,
) -> TitleResolutionEntry:
    normalized_title = title.strip()
    source, _, source_id = source_movie_id.strip().partition(":")
    if not source or not source_id:
        return TitleResolutionEntry.unresolved(
            normalized_title,
            reason="app_owned_movie_unknown_source",
        )

    return TitleResolutionEntry.resolved(
        normalized_title,
        TitleResolutionCandidate(
            source=source,
            source_id=source_id,
            title=normalized_title,
            media_type=MediaType.MOVIE,
        ),
    )


def _dedupe_profile_ratings(
    ratings: tuple[AppOwnedProfileRating, ...],
) -> tuple[AppOwnedProfileRating, ...]:
    deduped: dict[str, AppOwnedProfileRating] = {}
    for rating in ratings:
        profile_id = rating.profile_id.strip()
        if profile_id:
            deduped[profile_id] = AppOwnedProfileRating(
                profile_id=profile_id,
                taste_label=rating.taste_label,
            )
    return tuple(deduped.values())
