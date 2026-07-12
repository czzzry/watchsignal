from __future__ import annotations

import sqlite3
import re
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path

from movie_night_mediator.storage import SQLiteSettings

CURRENT_SETUP_ID = "current"
DEFAULT_HUSBAND_PROFILE_ID = "profile-1"
DEFAULT_WIFE_PROFILE_ID = "profile-2"
TESTER_PROFILE_ID = "alex-tester"
TESTER_PROFILE_LABEL = "Alex - tester"
TESTER_PROFILE_AVATAR_KEY = "comet"
TESTER_PROFILE_COLOR_KEY = "amber"
SOPHIE_TESTER_PROFILE_ID = "sophie-tester"
SOPHIE_TESTER_PROFILE_LABEL = "Sophie - tester"
SOPHIE_TESTER_PROFILE_AVATAR_KEY = "moon"
SOPHIE_TESTER_PROFILE_COLOR_KEY = "rose"
AVATAR_KEYS = ("spark", "moon", "comet", "ticket")
COLOR_KEYS = ("cyan", "rose", "amber", "violet")


@dataclass(frozen=True)
class SetupProfile:
    id: str
    label: str
    order: int
    avatar_key: str
    color_key: str


@dataclass(frozen=True)
class SetupDefaults:
    session_type: str
    input_mode: str
    availability_region: str
    language_access: str
    shortlist_size: int
    avoid_already_watched: bool


@dataclass(frozen=True)
class SetupState:
    household_label: str
    profiles: tuple[SetupProfile, ...]
    defaults: SetupDefaults
    active_profile_id: str
    partner_profile_id: str


def default_setup_state() -> SetupState:
    return SetupState(
        household_label="Household",
        profiles=(
            SetupProfile(
                id="profile-1",
                label="Husband",
                order=1,
                avatar_key="spark",
                color_key="cyan",
            ),
            SetupProfile(
                id="profile-2",
                label="Wife",
                order=2,
                avatar_key="moon",
                color_key="rose",
            ),
        ),
        defaults=SetupDefaults(
            session_type="Movie night",
            input_mode="Pass the phone",
            availability_region="Prime Video Germany",
            language_access="English audio or foreign audio with verified English subtitles",
            shortlist_size=5,
            avoid_already_watched=True,
        ),
        active_profile_id=DEFAULT_HUSBAND_PROFILE_ID,
        partner_profile_id=DEFAULT_WIFE_PROFILE_ID,
    )


class SQLiteSetupStore:
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

    def load_setup(self) -> SetupState:
        self.initialize_schema()
        with closing(self._connect()) as connection:
            setup_row = connection.execute(
                """
                SELECT
                    household_label,
                    active_profile_id,
                    partner_profile_id,
                    session_type,
                    input_mode,
                    availability_region,
                    language_access,
                    shortlist_size,
                    avoid_already_watched
                FROM setup_state
                WHERE setup_id = ?
                """,
                (CURRENT_SETUP_ID,),
            ).fetchone()

            if setup_row is None:
                return default_setup_state()

            profile_rows = connection.execute(
                """
                SELECT profile_id, display_label, sort_order, avatar_key, color_key
                FROM setup_profiles
                WHERE setup_id = ?
                ORDER BY sort_order ASC, profile_id ASC
                """,
                (CURRENT_SETUP_ID,),
            ).fetchall()

        profiles = tuple(
            SetupProfile(
                id=row["profile_id"],
                label=row["display_label"],
                order=row["sort_order"],
                avatar_key=row["avatar_key"],
                color_key=row["color_key"],
            )
            for row in profile_rows
        )

        if len(profiles) < 2:
            return default_setup_state()

        active_profile_id, partner_profile_id = _resolve_pairing(
            profiles,
            active_profile_id=setup_row["active_profile_id"],
            partner_profile_id=setup_row["partner_profile_id"],
        )

        return SetupState(
            household_label=setup_row["household_label"],
            profiles=profiles,
            defaults=SetupDefaults(
                session_type=setup_row["session_type"],
                input_mode=setup_row["input_mode"],
                availability_region=setup_row["availability_region"],
                language_access=setup_row["language_access"],
                shortlist_size=setup_row["shortlist_size"],
                avoid_already_watched=bool(setup_row["avoid_already_watched"]),
            ),
            active_profile_id=active_profile_id,
            partner_profile_id=partner_profile_id,
        )

    def save_setup(self, setup: SetupState) -> SetupState:
        if len(setup.profiles) < 2:
            raise ValueError("A setup must include at least two participant profiles.")
        active_profile_id, partner_profile_id = _resolve_pairing(
            setup.profiles,
            active_profile_id=setup.active_profile_id,
            partner_profile_id=setup.partner_profile_id,
        )

        self.initialize_schema()
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO setup_state (
                        setup_id,
                        household_label,
                        active_profile_id,
                        partner_profile_id,
                        session_type,
                        input_mode,
                        availability_region,
                        language_access,
                        shortlist_size,
                        avoid_already_watched
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(setup_id) DO UPDATE SET
                        household_label = excluded.household_label,
                        active_profile_id = excluded.active_profile_id,
                        partner_profile_id = excluded.partner_profile_id,
                        session_type = excluded.session_type,
                        input_mode = excluded.input_mode,
                        availability_region = excluded.availability_region,
                        language_access = excluded.language_access,
                        shortlist_size = excluded.shortlist_size,
                        avoid_already_watched = excluded.avoid_already_watched
                    """,
                    (
                        CURRENT_SETUP_ID,
                        setup.household_label,
                        active_profile_id,
                        partner_profile_id,
                        setup.defaults.session_type,
                        setup.defaults.input_mode,
                        setup.defaults.availability_region,
                        setup.defaults.language_access,
                        setup.defaults.shortlist_size,
                        int(setup.defaults.avoid_already_watched),
                    ),
                )
                connection.execute(
                    "DELETE FROM setup_profiles WHERE setup_id = ?",
                    (CURRENT_SETUP_ID,),
                )
                connection.executemany(
                    """
                    INSERT INTO setup_profiles (
                        profile_id,
                        setup_id,
                        display_label,
                        sort_order,
                        avatar_key,
                        color_key
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            profile.id,
                            CURRENT_SETUP_ID,
                            profile.label,
                            profile.order,
                            profile.avatar_key,
                            profile.color_key,
                        )
                        for profile in setup.profiles
                    ],
                )

        return self.load_setup()

    def ensure_tester_profile(self) -> SetupState:
        setup = self.load_setup()
        protected_testers = (
            SetupProfile(
                id=TESTER_PROFILE_ID,
                label=TESTER_PROFILE_LABEL,
                order=1,
                avatar_key=TESTER_PROFILE_AVATAR_KEY,
                color_key=TESTER_PROFILE_COLOR_KEY,
            ),
            SetupProfile(
                id=SOPHIE_TESTER_PROFILE_ID,
                label=SOPHIE_TESTER_PROFILE_LABEL,
                order=2,
                avatar_key=SOPHIE_TESTER_PROFILE_AVATAR_KEY,
                color_key=SOPHIE_TESTER_PROFILE_COLOR_KEY,
            ),
        )
        existing_by_id = {profile.id: profile for profile in setup.profiles}
        tester_profiles = tuple(
            existing_by_id.get(profile.id, profile) for profile in protected_testers
        )
        protected_ids = {profile.id for profile in protected_testers}
        remaining_profiles = tuple(
            profile for profile in setup.profiles if profile.id not in protected_ids
        )

        reordered_profiles = (
            *(
                SetupProfile(
                    id=profile.id,
                    label=profile.label,
                    order=index,
                    avatar_key=profile.avatar_key,
                    color_key=profile.color_key,
                )
                for index, profile in enumerate(tester_profiles, start=1)
            ),
            *(
                SetupProfile(
                    id=profile.id,
                    label=profile.label,
                    order=index,
                    avatar_key=profile.avatar_key,
                    color_key=profile.color_key,
                )
                for index, profile in enumerate(
                    sorted(remaining_profiles, key=lambda profile: profile.order),
                    start=len(tester_profiles) + 1,
                )
            ),
        )

        if reordered_profiles == setup.profiles:
            return setup

        return self.save_setup(
            SetupState(
                household_label=setup.household_label,
                profiles=reordered_profiles,
                defaults=setup.defaults,
                active_profile_id=TESTER_PROFILE_ID,
                partner_profile_id=next(
                    profile.id
                    for profile in reordered_profiles
                    if profile.id not in protected_ids
                ),
            )
        )

    def create_profile(self, display_label: str) -> SetupState:
        normalized_display_label = display_label.strip()
        if not normalized_display_label:
            raise ValueError("Profile creation requires a display label.")

        setup = self.load_setup()
        existing_ids = {profile.id for profile in setup.profiles}
        profile_id = _unique_profile_id(normalized_display_label, existing_ids)
        next_order = max((profile.order for profile in setup.profiles), default=0) + 1
        created_profile = SetupProfile(
            id=profile_id,
            label=normalized_display_label,
            order=next_order,
            avatar_key=AVATAR_KEYS[(next_order - 1) % len(AVATAR_KEYS)],
            color_key=COLOR_KEYS[(next_order - 1) % len(COLOR_KEYS)],
        )
        next_profiles = (*setup.profiles, created_profile)
        partner_profile_id = next(
            profile.id for profile in next_profiles if profile.id != profile_id
        )

        return self.save_setup(
            SetupState(
                household_label=setup.household_label,
                profiles=next_profiles,
                defaults=setup.defaults,
                active_profile_id=profile_id,
                partner_profile_id=partner_profile_id,
            )
        )

    def rename_profile(self, profile_id: str, display_label: str) -> SetupState:
        normalized_profile_id = profile_id.strip()
        normalized_display_label = display_label.strip()
        if not normalized_profile_id:
            raise ValueError("Profile rename requires a profile id.")
        if not normalized_display_label:
            raise ValueError("Profile rename requires a display label.")

        setup = self.load_setup()
        renamed_profiles = tuple(
            SetupProfile(
                id=profile.id,
                label=(
                    normalized_display_label
                    if profile.id == normalized_profile_id
                    else profile.label
                ),
                order=profile.order,
                avatar_key=profile.avatar_key,
                color_key=profile.color_key,
            )
            for profile in setup.profiles
        )

        if renamed_profiles == setup.profiles:
            raise LookupError("Profile not found.")

        return self.save_setup(
            SetupState(
                household_label=setup.household_label,
                profiles=renamed_profiles,
                defaults=setup.defaults,
                active_profile_id=setup.active_profile_id,
                partner_profile_id=setup.partner_profile_id,
            )
        )

    def initialize_schema(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            with connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS setup_state (
                        setup_id TEXT PRIMARY KEY,
                        household_label TEXT NOT NULL,
                        active_profile_id TEXT,
                        partner_profile_id TEXT,
                        session_type TEXT NOT NULL,
                        input_mode TEXT NOT NULL,
                        availability_region TEXT NOT NULL,
                        language_access TEXT NOT NULL,
                        shortlist_size INTEGER NOT NULL CHECK (shortlist_size > 0),
                        avoid_already_watched INTEGER NOT NULL CHECK (
                            avoid_already_watched IN (0, 1)
                        ),
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS setup_profiles (
                        profile_id TEXT PRIMARY KEY,
                        setup_id TEXT NOT NULL REFERENCES setup_state(setup_id)
                            ON DELETE CASCADE,
                        display_label TEXT NOT NULL,
                        sort_order INTEGER NOT NULL,
                        avatar_key TEXT NOT NULL DEFAULT 'spark',
                        color_key TEXT NOT NULL DEFAULT 'cyan'
                    );
                    """
                )
                columns = {
                    row["name"]
                    for row in connection.execute("PRAGMA table_info(setup_state)")
                }
                if "active_profile_id" not in columns:
                    connection.execute(
                        "ALTER TABLE setup_state ADD COLUMN active_profile_id TEXT"
                    )
                if "partner_profile_id" not in columns:
                    connection.execute(
                        "ALTER TABLE setup_state ADD COLUMN partner_profile_id TEXT"
                    )

                profile_columns = {
                    row["name"]
                    for row in connection.execute("PRAGMA table_info(setup_profiles)")
                }
                added_avatar_key = False
                added_color_key = False
                if "avatar_key" not in profile_columns:
                    connection.execute(
                        "ALTER TABLE setup_profiles ADD COLUMN avatar_key TEXT NOT NULL DEFAULT 'spark'"
                    )
                    added_avatar_key = True
                if "color_key" not in profile_columns:
                    connection.execute(
                        "ALTER TABLE setup_profiles ADD COLUMN color_key TEXT NOT NULL DEFAULT 'cyan'"
                    )
                    added_color_key = True
                if added_avatar_key:
                    connection.execute(
                        """
                        UPDATE setup_profiles
                        SET avatar_key = 'moon'
                        WHERE sort_order = 2
                        """
                    )
                if added_color_key:
                    connection.execute(
                        """
                        UPDATE setup_profiles
                        SET color_key = 'rose'
                        WHERE sort_order = 2
                        """
                    )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _resolve_pairing(
    profiles: tuple[SetupProfile, ...],
    *,
    active_profile_id: str | None,
    partner_profile_id: str | None,
) -> tuple[str, str]:
    profile_ids = tuple(profile.id for profile in profiles)
    profile_id_set = set(profile_ids)
    if len(profile_id_set) < 2:
        raise ValueError("Household mode requires two distinct profiles.")

    resolved_active_profile_id = (
        active_profile_id.strip()
        if active_profile_id is not None and active_profile_id.strip()
        else profile_ids[0]
    )
    if resolved_active_profile_id not in profile_id_set:
        resolved_active_profile_id = profile_ids[0]

    resolved_partner_profile_id = (
        partner_profile_id.strip()
        if partner_profile_id is not None and partner_profile_id.strip()
        else ""
    )
    if (
        resolved_partner_profile_id not in profile_id_set
        or resolved_partner_profile_id == resolved_active_profile_id
    ):
        resolved_partner_profile_id = next(
            profile_id
            for profile_id in profile_ids
            if profile_id != resolved_active_profile_id
        )

    return resolved_active_profile_id, resolved_partner_profile_id


def _unique_profile_id(display_label: str, existing_ids: set[str]) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", display_label.lower()).strip("-")
    base_id = slug or "profile"
    profile_id = base_id
    suffix = 2
    while profile_id in existing_ids:
        profile_id = f"{base_id}-{suffix}"
        suffix += 1
    return profile_id
