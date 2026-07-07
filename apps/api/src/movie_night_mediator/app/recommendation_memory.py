from __future__ import annotations

from movie_night_mediator.app.backfill import ManualBackfillService
from movie_night_mediator.domain import (
    BackfillTasteLabel,
    ProfileTasteEvidence,
    TitleResolutionStatus,
    WatchedStatusScope,
)


PREFERENCE_VALUES = {
    BackfillTasteLabel.LOVED: 1.0,
    BackfillTasteLabel.FINE: 0.35,
    BackfillTasteLabel.NO: -1.0,
}


def profile_memory_evidence(
    *,
    backfill_service: ManualBackfillService,
    household_id: str,
    profile_id: str,
) -> tuple[ProfileTasteEvidence, ...]:
    records = backfill_service.list_watched_titles(household_id)
    evidence = []
    for record in records:
        if (
            record.scope != WatchedStatusScope.PARTICIPANT
            or record.participant_id != profile_id
            or not record.watched
        ):
            continue

        source_movie_id = _source_movie_id(record)
        if source_movie_id is None:
            continue

        if record.taste_label is None:
            evidence.append(
                ProfileTasteEvidence(
                    source="seen_before",
                    source_movie_id=source_movie_id,
                    title=record.entry.raw_title,
                    preference_value=-0.35,
                    familiarity="seen",
                    source_label="seen_before",
                )
            )
            continue

        evidence.append(
            ProfileTasteEvidence(
                source="app_memory",
                source_movie_id=source_movie_id,
                title=record.entry.raw_title,
                preference_value=PREFERENCE_VALUES[record.taste_label],
                familiarity="seen",
                source_label=record.taste_label.value,
            )
        )

    return tuple(evidence)


def watched_source_movie_ids(
    *,
    backfill_service: ManualBackfillService,
    household_id: str,
    profile_ids: tuple[str, ...],
) -> tuple[str, ...]:
    profile_id_set = set(profile_ids)
    watched_ids = []
    for record in backfill_service.list_watched_titles(household_id):
        if not record.watched:
            continue
        if record.scope == WatchedStatusScope.PARTICIPANT and record.participant_id not in profile_id_set:
            continue

        source_movie_id = _source_movie_id(record)
        if source_movie_id is not None:
            watched_ids.append(source_movie_id)

    return tuple(dict.fromkeys(watched_ids))


def _source_movie_id(record) -> str | None:
    if record.entry.status != TitleResolutionStatus.RESOLVED:
        return None
    assert record.entry.candidate is not None
    return record.entry.candidate.source_movie_id
