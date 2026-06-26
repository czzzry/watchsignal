from __future__ import annotations

import re
from datetime import date

from movie_night_mediator.domain import (
    BackfillTasteLabel,
    TitleResolutionEntry,
    TitleResolutionStatus,
    WatchedStatusScope,
    WatchedTitleBackfill,
)
from movie_night_mediator.storage import SQLiteBackfillStore


class ManualBackfillService:
    def __init__(self, store: SQLiteBackfillStore) -> None:
        self.store = store

    def add_watched_title(
        self,
        *,
        household_id: str,
        entry: TitleResolutionEntry,
        participant_ids: tuple[str, ...] = (),
        include_global: bool = False,
        watched_on: date | None = None,
        watched: bool = True,
        taste_label: BackfillTasteLabel | None = None,
    ) -> tuple[WatchedTitleBackfill, ...]:
        normalized_participant_ids = _normalize_participant_ids(participant_ids)
        if not normalized_participant_ids and not include_global:
            raise ValueError("Backfill requires at least one participant or global watched status.")

        title_key = title_key_for_entry(entry)
        records: list[WatchedTitleBackfill] = []
        if include_global:
            records.append(
                WatchedTitleBackfill(
                    household_id=household_id,
                    scope=WatchedStatusScope.GLOBAL,
                    entry=entry,
                    title_key=title_key,
                    watched_on=watched_on,
                    watched=watched,
                    taste_label=taste_label,
                )
            )

        records.extend(
            WatchedTitleBackfill(
                household_id=household_id,
                scope=WatchedStatusScope.PARTICIPANT,
                participant_id=participant_id,
                entry=entry,
                title_key=title_key,
                watched_on=watched_on,
                watched=watched,
                taste_label=taste_label,
            )
            for participant_id in normalized_participant_ids
        )

        return tuple(self.store.save_watched_title(record) for record in records)

    def list_watched_titles(
        self,
        household_id: str,
    ) -> tuple[WatchedTitleBackfill, ...]:
        return self.store.load_watched_titles(household_id)


def title_key_for_entry(entry: TitleResolutionEntry) -> str:
    if entry.status == TitleResolutionStatus.RESOLVED:
        assert entry.candidate is not None
        return entry.candidate.source_movie_id

    return f"text:{normalize_plain_title(entry.raw_title)}"


def normalize_plain_title(title: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", title.lower())).strip()


def _normalize_participant_ids(participant_ids: tuple[str, ...]) -> tuple[str, ...]:
    normalized_ids = tuple(
        participant_id.strip()
        for participant_id in participant_ids
        if participant_id.strip()
    )
    return tuple(dict.fromkeys(normalized_ids))
