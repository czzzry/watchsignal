from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from movie_night_mediator.domain import (
    MediaType,
    OnboardingCompletion,
    OnboardingConstraints,
    ParticipantOnboarding,
    SeedPreferenceLabel,
    TitleResolutionCandidate,
    TitleResolutionEntry,
    TitleResolutionStatus,
)
from movie_night_mediator.storage import SQLiteSettings
from movie_night_mediator.storage.database import DatabaseConnection, connect_database


class SQLiteOnboardingStore:
    def __init__(
        self,
        database_path: str | Path | None = None,
        settings: SQLiteSettings | None = None,
    ) -> None:
        if database_path is not None and settings is not None:
            raise ValueError("Pass database_path or settings, not both.")

        if database_path is not None:
            self.database_path = Path(database_path)
        else:
            resolved_settings = settings or SQLiteSettings.from_env()
            self.database_path = resolved_settings.database_path

    def save_profile_onboarding(
        self,
        onboarding: ParticipantOnboarding,
    ) -> ParticipantOnboarding:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO onboarding_profiles (
                        profile_id,
                        horror_exclusion,
                        subtitle_intolerance
                    )
                    VALUES (?, ?, ?)
                    ON CONFLICT(profile_id) DO UPDATE SET
                        horror_exclusion = excluded.horror_exclusion,
                        subtitle_intolerance = excluded.subtitle_intolerance,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (
                        onboarding.profile_id,
                        int(onboarding.constraints.horror_exclusion),
                        int(onboarding.constraints.subtitle_intolerance),
                    ),
                )
                connection.execute(
                    "DELETE FROM onboarding_seed_titles WHERE profile_id = ?",
                    (onboarding.profile_id,),
                )
                connection.executemany(
                    """
                    INSERT INTO onboarding_seed_titles (
                        profile_id,
                        preference_label,
                        sort_order,
                        raw_title,
                        resolution_status,
                        unresolved_reason,
                        candidate_source,
                        candidate_source_id,
                        candidate_title,
                        candidate_media_type,
                        candidate_release_year,
                        candidate_overview,
                        candidate_original_language,
                        candidate_popularity
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    list(_seed_rows(onboarding)),
                )

        loaded = self.load_profile_onboarding(onboarding.profile_id)
        if loaded is None:
            raise RuntimeError("Saved onboarding profile could not be reloaded.")

        return loaded

    def load_profile_onboarding(self, profile_id: str) -> ParticipantOnboarding | None:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            profile_row = connection.execute(
                """
                SELECT profile_id, horror_exclusion, subtitle_intolerance
                FROM onboarding_profiles
                WHERE profile_id = ?
                """,
                (profile_id,),
            ).fetchone()

            if profile_row is None:
                return None

            seed_rows = connection.execute(
                """
                SELECT
                    preference_label,
                    raw_title,
                    resolution_status,
                    unresolved_reason,
                    candidate_source,
                    candidate_source_id,
                    candidate_title,
                    candidate_media_type,
                    candidate_release_year,
                    candidate_overview,
                    candidate_original_language,
                    candidate_popularity
                FROM onboarding_seed_titles
                WHERE profile_id = ?
                ORDER BY preference_label ASC, sort_order ASC, seed_id ASC
                """,
                (profile_id,),
            ).fetchall()

        entries_by_label = {
            SeedPreferenceLabel.LOVED: [],
            SeedPreferenceLabel.FINE: [],
            SeedPreferenceLabel.NO: [],
        }
        for row in seed_rows:
            label = SeedPreferenceLabel(row["preference_label"])
            entries_by_label[label].append(_row_to_title_entry(row))

        return ParticipantOnboarding(
            profile_id=profile_row["profile_id"],
            loved_title_entries=tuple(entries_by_label[SeedPreferenceLabel.LOVED]),
            fine_title_entries=tuple(entries_by_label[SeedPreferenceLabel.FINE]),
            no_title_entries=tuple(entries_by_label[SeedPreferenceLabel.NO]),
            constraints=OnboardingConstraints(
                horror_exclusion=bool(profile_row["horror_exclusion"]),
                subtitle_intolerance=bool(profile_row["subtitle_intolerance"]),
            ),
        )

    def load_completion(
        self,
        required_profile_ids: tuple[str, ...],
    ) -> OnboardingCompletion:
        profiles = tuple(
            self.load_profile_onboarding(profile_id)
            or ParticipantOnboarding(profile_id=profile_id)
            for profile_id in required_profile_ids
        )
        return OnboardingCompletion(
            required_profile_ids=required_profile_ids,
            profiles=profiles,
        )

    def initialize_schema(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS onboarding_profiles (
                        profile_id TEXT PRIMARY KEY,
                        horror_exclusion INTEGER NOT NULL CHECK (
                            horror_exclusion IN (0, 1)
                        ),
                        subtitle_intolerance INTEGER NOT NULL CHECK (
                            subtitle_intolerance IN (0, 1)
                        ),
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS onboarding_seed_titles (
                        seed_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        profile_id TEXT NOT NULL REFERENCES onboarding_profiles(profile_id)
                            ON DELETE CASCADE,
                        preference_label TEXT NOT NULL CHECK (
                            preference_label IN ('loved', 'fine', 'no')
                        ),
                        sort_order INTEGER NOT NULL,
                        raw_title TEXT NOT NULL,
                        resolution_status TEXT NOT NULL CHECK (
                            resolution_status IN ('resolved', 'unresolved')
                        ),
                        unresolved_reason TEXT,
                        candidate_source TEXT,
                        candidate_source_id TEXT,
                        candidate_title TEXT,
                        candidate_media_type TEXT,
                        candidate_release_year INTEGER,
                        candidate_overview TEXT,
                        candidate_original_language TEXT,
                        candidate_popularity REAL
                    );
                    """
                )

    def _connect(self) -> DatabaseConnection:
        return connect_database(self.database_path)


def _seed_rows(onboarding: ParticipantOnboarding):
    for preference_label in SeedPreferenceLabel:
        for sort_order, entry in enumerate(
            onboarding.entries_for(preference_label),
            start=1,
        ):
            candidate = entry.candidate
            yield (
                onboarding.profile_id,
                preference_label.value,
                sort_order,
                entry.raw_title,
                entry.status.value,
                entry.unresolved_reason,
                candidate.source if candidate is not None else None,
                candidate.source_id if candidate is not None else None,
                candidate.title if candidate is not None else None,
                candidate.media_type.value if candidate is not None else None,
                candidate.release_year if candidate is not None else None,
                candidate.overview if candidate is not None else None,
                candidate.original_language if candidate is not None else None,
                candidate.popularity if candidate is not None else None,
            )


def _row_to_title_entry(row: sqlite3.Row) -> TitleResolutionEntry:
    status = TitleResolutionStatus(row["resolution_status"])
    if status == TitleResolutionStatus.UNRESOLVED:
        return TitleResolutionEntry.unresolved(
            row["raw_title"],
            reason=row["unresolved_reason"],
        )

    candidate = TitleResolutionCandidate(
        source=row["candidate_source"],
        source_id=row["candidate_source_id"],
        title=row["candidate_title"],
        media_type=MediaType(row["candidate_media_type"]),
        release_year=row["candidate_release_year"],
        overview=row["candidate_overview"] or "",
        original_language=row["candidate_original_language"],
        popularity=row["candidate_popularity"],
    )
    return TitleResolutionEntry.resolved(row["raw_title"], candidate)
