from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from movie_night_mediator.app.setup import (
    SQLiteSetupStore,
    SetupDefaults,
    SetupProfile,
    SetupState,
)


class SetupProfilePayload(BaseModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    order: int
    avatarKey: str = Field(default="spark", min_length=1)
    colorKey: str = Field(default="cyan", min_length=1)


class SetupDefaultsPayload(BaseModel):
    sessionType: str = Field(min_length=1)
    inputMode: str = Field(min_length=1)
    availabilityRegion: str = Field(min_length=1)
    languageAccess: str = Field(min_length=1)
    shortlistSize: int = Field(ge=1)
    avoidAlreadyWatched: bool


class SetupStatePayload(BaseModel):
    householdLabel: str = Field(min_length=1)
    profiles: list[SetupProfilePayload] = Field(min_length=2)
    defaults: SetupDefaultsPayload


class SetupProfileRenamePayload(BaseModel):
    label: str = Field(min_length=1)


def register_setup_routes(
    app: FastAPI,
    *,
    setup_store: SQLiteSetupStore,
) -> None:
    @app.get("/setup", response_model=SetupStatePayload, tags=["setup"])
    def get_setup() -> SetupStatePayload:
        return _setup_state_to_payload(setup_store.load_setup())

    @app.put("/setup", response_model=SetupStatePayload, tags=["setup"])
    def put_setup(payload: SetupStatePayload) -> SetupStatePayload:
        _validate_profile_uniqueness(payload.profiles)
        saved_setup = setup_store.save_setup(_payload_to_setup_state(payload))
        return _setup_state_to_payload(saved_setup)

    @app.post(
        "/setup/profiles/tester",
        response_model=SetupStatePayload,
        tags=["setup"],
    )
    def post_tester_profile() -> SetupStatePayload:
        return _setup_state_to_payload(setup_store.ensure_tester_profile())

    @app.patch(
        "/setup/profiles/{profile_id}",
        response_model=SetupStatePayload,
        tags=["setup"],
    )
    def patch_profile(
        profile_id: str,
        payload: SetupProfileRenamePayload,
    ) -> SetupStatePayload:
        try:
            return _setup_state_to_payload(
                setup_store.rename_profile(profile_id, payload.label)
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


def _validate_profile_uniqueness(profiles: list[SetupProfilePayload]) -> None:
    profile_ids = [profile.id for profile in profiles]
    if len(set(profile_ids)) != len(profile_ids):
        raise HTTPException(status_code=400, detail="Profile ids must be unique.")


def _payload_to_setup_state(payload: SetupStatePayload) -> SetupState:
    return SetupState(
        household_label=payload.householdLabel,
        profiles=tuple(
            SetupProfile(
                id=profile.id,
                label=profile.label,
                order=profile.order,
                avatar_key=profile.avatarKey,
                color_key=profile.colorKey,
            )
            for profile in payload.profiles
        ),
        defaults=SetupDefaults(
            session_type=payload.defaults.sessionType,
            input_mode=payload.defaults.inputMode,
            availability_region=payload.defaults.availabilityRegion,
            language_access=payload.defaults.languageAccess,
            shortlist_size=payload.defaults.shortlistSize,
            avoid_already_watched=payload.defaults.avoidAlreadyWatched,
        ),
    )


def _setup_state_to_payload(setup: SetupState) -> SetupStatePayload:
    return SetupStatePayload(
        householdLabel=setup.household_label,
        profiles=[
            SetupProfilePayload(
                id=profile.id,
                label=profile.label,
                order=profile.order,
                avatarKey=profile.avatar_key,
                colorKey=profile.color_key,
            )
            for profile in setup.profiles
        ],
        defaults=SetupDefaultsPayload(
            sessionType=setup.defaults.session_type,
            inputMode=setup.defaults.input_mode,
            availabilityRegion=setup.defaults.availability_region,
            languageAccess=setup.defaults.language_access,
            shortlistSize=setup.defaults.shortlist_size,
            avoidAlreadyWatched=setup.defaults.avoid_already_watched,
        ),
    )
