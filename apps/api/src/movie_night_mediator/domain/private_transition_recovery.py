from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from movie_night_mediator.domain.models import SessionReaction, SessionReactionLabel


MAX_RECOVERY_SOURCE_MOVIE_ID_LENGTH = 128
MAX_RECOVERY_TITLE_LENGTH = 200
MAX_RECOVERY_POSTER_URL_LENGTH = 2_048
MAX_RECOVERY_SESSION_ID_LENGTH = 128


class RecoveryStage(StrEnum):
    FOUNDER_SEALED = "founder_sealed"
    HANDOFF_READY = "handoff_ready"
    SECOND_PASS_READY = "second_pass_ready"
    FINAL_SEALED = "final_sealed"
    MATCHING_FAILED = "matching_failed"
    RESULT_READY = "result_ready"


class RecoveryActor(StrEnum):
    FOUNDER = "founder"
    WIFE = "wife"


class RecoveryCommandKind(StrEnum):
    SEAL_FOUNDER_BALLOT = "seal_founder_ballot"
    OPEN_SECOND_PASS = "open_second_pass"
    SEAL_FINAL_BALLOT = "seal_final_ballot"
    USE_LOCAL_RESULT = "use_local_result"


class RecoveryCommandStatus(StrEnum):
    SEALED = "sealed"
    COMPLETED = "completed"


@dataclass(frozen=True)
class RecoveryBallotItem:
    source_movie_id: str
    reaction_label: SessionReactionLabel

    def __post_init__(self) -> None:
        source_movie_id = _bounded_text(
            self.source_movie_id,
            "Recovery ballot movie id",
            MAX_RECOVERY_SOURCE_MOVIE_ID_LENGTH,
        )
        if not isinstance(self.reaction_label, SessionReactionLabel):
            raise ValueError("Recovery ballot reactions are invalid.")
        object.__setattr__(self, "source_movie_id", source_movie_id)


@dataclass(frozen=True)
class RecoveryCastMember:
    name: str
    character: str | None = None
    profile_url: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _bounded_text(self.name, "Cast name", 100))
        object.__setattr__(
            self,
            "character",
            _optional_bounded_text(self.character, "Cast role", 120),
        )
        object.__setattr__(
            self,
            "profile_url",
            _optional_https_url(self.profile_url, "Cast profile URL"),
        )


@dataclass(frozen=True)
class RecoveryProviderAvailability:
    provider_name: str
    access_type: str
    region: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "provider_name",
            _bounded_text(self.provider_name, "Provider name", 100),
        )
        object.__setattr__(
            self,
            "access_type",
            _bounded_text(self.access_type, "Provider access type", 40),
        )
        object.__setattr__(
            self,
            "region",
            _bounded_text(self.region, "Provider region", 8),
        )


@dataclass(frozen=True)
class RecoveryMovieDisplay:
    source_movie_id: str
    title: str
    year: int | None = None
    runtime_label: str = "Runtime check needed"
    poster_url: str | None = None
    backdrop_url: str | None = None
    provider_url: str | None = None
    synopsis: str = ""
    genres: tuple[str, ...] = ()
    cast: tuple[RecoveryCastMember, ...] = ()
    providers: tuple[RecoveryProviderAvailability, ...] = ()
    matched_person_names: tuple[str, ...] = ()
    safe_pick_status: str = "Safe Pick"
    availability: str = "Availability check needed"
    language_access: str = "Audio and subtitle details need a quick check"
    tone: str = "Balanced pick"
    positive_evidence: tuple[str, ...] = ()
    penalties: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.source_movie_id, str) or not isinstance(
            self.title, str
        ):
            raise ValueError("Recovery movie display text fields must be strings.")
        if self.poster_url is not None and not isinstance(self.poster_url, str):
            raise ValueError("Recovery movie poster URLs must be strings.")
        source_movie_id = self.source_movie_id.strip()
        title = self.title.strip()
        poster_url = self.poster_url.strip() if self.poster_url is not None else None
        if not source_movie_id:
            raise ValueError("Recovery movie displays require a source movie id.")
        if len(source_movie_id) > MAX_RECOVERY_SOURCE_MOVIE_ID_LENGTH:
            raise ValueError("Recovery movie source ids are too long.")
        if not title:
            raise ValueError("Recovery movie displays require a title.")
        if len(title) > MAX_RECOVERY_TITLE_LENGTH:
            raise ValueError("Recovery movie titles are too long.")
        if self.year is not None and (
            isinstance(self.year, bool)
            or not isinstance(self.year, int)
            or not 1888 <= self.year <= 2200
        ):
            raise ValueError("Recovery movie display years are out of range.")
        if poster_url is not None and not poster_url.startswith("https://"):
            raise ValueError("Recovery movie poster URLs must use HTTPS.")
        if poster_url is not None and len(poster_url) > MAX_RECOVERY_POSTER_URL_LENGTH:
            raise ValueError("Recovery movie poster URLs are too long.")
        runtime_label = _bounded_text(self.runtime_label, "Runtime label", 40)
        backdrop_url = _optional_https_url(self.backdrop_url, "Backdrop URL")
        provider_url = _optional_https_url(self.provider_url, "Provider URL")
        synopsis = _optional_bounded_text(self.synopsis, "Synopsis", 1_500) or ""
        genres = _bounded_text_tuple(self.genres, "Genre", count=5, length=40)
        if len(self.cast) > 3 or not all(
            isinstance(member, RecoveryCastMember) for member in self.cast
        ):
            raise ValueError("Recovery display cast must contain up to three members.")
        if len(self.providers) > 8 or not all(
            isinstance(provider, RecoveryProviderAvailability)
            for provider in self.providers
        ):
            raise ValueError(
                "Recovery display providers must contain up to eight entries."
            )
        matched_person_names = _bounded_text_tuple(
            self.matched_person_names,
            "Matched person",
            count=3,
            length=100,
        )
        if self.safe_pick_status not in {"Safe Pick", "Needs Quick Check"}:
            raise ValueError("Recovery display safe-pick status is invalid.")
        availability = _bounded_text(self.availability, "Availability", 240)
        language_access = _bounded_text(
            self.language_access,
            "Language access",
            160,
        )
        tone = _bounded_text(self.tone, "Tone", 120)
        positive_evidence = _bounded_text_tuple(
            self.positive_evidence,
            "Positive evidence",
            count=12,
            length=160,
        )
        penalties = _bounded_text_tuple(
            self.penalties,
            "Penalty evidence",
            count=12,
            length=160,
        )
        if not all(_is_public_positive_evidence(value) for value in positive_evidence):
            raise ValueError("Recovery display requires public evidence identifiers.")
        if any(
            value.startswith("nudge_person:")
            and value.removeprefix("nudge_person:").strip()
            not in matched_person_names
            for value in positive_evidence
        ):
            raise ValueError("Recovery display requires public evidence identifiers.")
        if not all(value.startswith("nudge_signal:avoid:") for value in penalties):
            raise ValueError("Recovery display requires public evidence identifiers.")
        object.__setattr__(self, "source_movie_id", source_movie_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "runtime_label", runtime_label)
        object.__setattr__(self, "poster_url", poster_url)
        object.__setattr__(self, "backdrop_url", backdrop_url)
        object.__setattr__(self, "provider_url", provider_url)
        object.__setattr__(self, "synopsis", synopsis)
        object.__setattr__(self, "genres", genres)
        object.__setattr__(self, "matched_person_names", matched_person_names)
        object.__setattr__(self, "availability", availability)
        object.__setattr__(self, "language_access", language_access)
        object.__setattr__(self, "tone", tone)
        object.__setattr__(self, "positive_evidence", positive_evidence)
        object.__setattr__(self, "penalties", penalties)


@dataclass(frozen=True)
class SealFounderBallot:
    command_id: str
    canonical_session_id: str
    ballot: tuple[RecoveryBallotItem | SessionReaction, ...]
    display_snapshot: tuple[RecoveryMovieDisplay, ...]

    def __post_init__(self) -> None:
        _validate_command_identifier_types(
            self.command_id,
            self.canonical_session_id,
        )
        command_id = self.command_id.strip()
        canonical_session_id = self.canonical_session_id.strip()
        if not re.fullmatch(r"[0-9a-f]{64}", command_id):
            raise ValueError("Recovery command ids must be lowercase 256-bit hex.")
        if not canonical_session_id:
            raise ValueError("Founder seals require a canonical session id.")
        if len(canonical_session_id) > MAX_RECOVERY_SESSION_ID_LENGTH:
            raise ValueError("Recovery session ids are too long.")
        _validate_seal_items(
            ballot=self.ballot,
            display_snapshot=self.display_snapshot,
            label="Founder seals",
        )
        object.__setattr__(self, "ballot", _normalized_ballot(self.ballot))
        object.__setattr__(self, "command_id", command_id)
        object.__setattr__(self, "canonical_session_id", canonical_session_id)


@dataclass(frozen=True)
class OpenSecondPass:
    command_id: str
    canonical_session_id: str | None = None

    def __post_init__(self) -> None:
        _validate_optional_command_identifier_types(
            self.command_id,
            self.canonical_session_id,
        )
        command_id = self.command_id.strip()
        canonical_session_id = (
            self.canonical_session_id.strip()
            if self.canonical_session_id is not None
            else None
        )
        if not re.fullmatch(r"[0-9a-f]{64}", command_id):
            raise ValueError("Recovery command ids must be lowercase 256-bit hex.")
        if canonical_session_id is not None and not canonical_session_id:
            raise ValueError("Recovery session ids cannot be blank.")
        if canonical_session_id is not None and len(canonical_session_id) > MAX_RECOVERY_SESSION_ID_LENGTH:
            raise ValueError("Recovery session ids are too long.")
        object.__setattr__(self, "command_id", command_id)
        object.__setattr__(self, "canonical_session_id", canonical_session_id)


@dataclass(frozen=True)
class SealFinalBallot:
    command_id: str
    ballot: tuple[RecoveryBallotItem | SessionReaction, ...]
    display_snapshot: tuple[RecoveryMovieDisplay, ...]
    canonical_session_id: str | None = None

    def __post_init__(self) -> None:
        _validate_optional_command_identifier_types(
            self.command_id,
            self.canonical_session_id,
        )
        command_id = self.command_id.strip()
        canonical_session_id = (
            self.canonical_session_id.strip()
            if self.canonical_session_id is not None
            else None
        )
        if not re.fullmatch(r"[0-9a-f]{64}", command_id):
            raise ValueError("Recovery command ids must be lowercase 256-bit hex.")
        if canonical_session_id is not None and not canonical_session_id:
            raise ValueError("Recovery session ids cannot be blank.")
        if canonical_session_id is not None and len(canonical_session_id) > MAX_RECOVERY_SESSION_ID_LENGTH:
            raise ValueError("Recovery session ids are too long.")
        _validate_seal_items(
            ballot=self.ballot,
            display_snapshot=self.display_snapshot,
            label="Final seals",
        )
        object.__setattr__(self, "ballot", _normalized_ballot(self.ballot))
        object.__setattr__(self, "command_id", command_id)
        object.__setattr__(self, "canonical_session_id", canonical_session_id)


@dataclass(frozen=True)
class UseLocalResult:
    command_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.command_id, str):
            raise ValueError("Recovery command ids must be text.")
        command_id = self.command_id.strip()
        if not re.fullmatch(r"[0-9a-f]{64}", command_id):
            raise ValueError("Recovery command ids must be lowercase 256-bit hex.")
        object.__setattr__(self, "command_id", command_id)


@dataclass(frozen=True)
class RecoveryHandle:
    version: int
    expires_at_ms: int


@dataclass(frozen=True)
class HandoffPending:
    recipient_label: str
    can_begin: bool = False

    def __post_init__(self) -> None:
        recipient_label = self.recipient_label.strip()
        if not recipient_label:
            raise ValueError("Handoff projections require a recipient label.")
        if self.can_begin:
            raise ValueError("Pending handoffs cannot begin yet.")
        object.__setattr__(self, "recipient_label", recipient_label)


@dataclass(frozen=True)
class HandoffReady:
    recipient_label: str
    can_begin: bool = True

    def __post_init__(self) -> None:
        recipient_label = self.recipient_label.strip()
        if not recipient_label:
            raise ValueError("Handoff projections require a recipient label.")
        if not self.can_begin:
            raise ValueError("Ready handoffs must allow the next person to begin.")
        object.__setattr__(self, "recipient_label", recipient_label)


@dataclass(frozen=True)
class SecondPassReady:
    display_snapshot: tuple[RecoveryMovieDisplay, ...]

    def __post_init__(self) -> None:
        if len(self.display_snapshot) != 5:
            raise ValueError("Second-pass recovery requires exactly five movies.")


@dataclass(frozen=True)
class MatchingPending:
    pass


@dataclass(frozen=True)
class MatchingFailed:
    can_retry: bool = True
    can_use_local: bool = True

    def __post_init__(self) -> None:
        if self.can_retry is not True or self.can_use_local is not True:
            raise ValueError("Matching-failure recovery must expose both safe choices.")


@dataclass(frozen=True)
class ResultReady:
    display_snapshot: tuple[RecoveryMovieDisplay, ...]
    canonical_session_id: str
    final_reactions: tuple[RecoveryBallotItem, ...]
    result_source: str = "shared"

    def __post_init__(self) -> None:
        if len(self.display_snapshot) != 5:
            raise ValueError("Result recovery requires exactly five movies.")
        canonical_session_id = _bounded_text(
            self.canonical_session_id,
            "Result recovery session id",
            MAX_RECOVERY_SESSION_ID_LENGTH,
        )
        object.__setattr__(self, "canonical_session_id", canonical_session_id)
        if len(self.final_reactions) != 5 or not all(
            isinstance(item, RecoveryBallotItem) for item in self.final_reactions
        ):
            raise ValueError("Result recovery requires exactly five final reactions.")
        if self.result_source not in {"shared", "local"}:
            raise ValueError("Result recovery source is invalid.")


SealCommand = SealFounderBallot | OpenSecondPass | SealFinalBallot | UseLocalResult
ResumeProjection = (
    HandoffPending
    | HandoffReady
    | SecondPassReady
    | MatchingPending
    | MatchingFailed
    | ResultReady
)


def _validate_seal_items(
    *,
    ballot: tuple[RecoveryBallotItem | SessionReaction, ...],
    display_snapshot: tuple[RecoveryMovieDisplay, ...],
    label: str,
) -> None:
    if (
        not isinstance(ballot, tuple)
        or len(ballot) != 5
        or not all(
            isinstance(reaction, (RecoveryBallotItem, SessionReaction))
            for reaction in ballot
        )
    ):
        raise ValueError(f"{label} require exactly five reactions.")
    if (
        not isinstance(display_snapshot, tuple)
        or len(display_snapshot) != 5
        or not all(
            isinstance(movie, RecoveryMovieDisplay) for movie in display_snapshot
        )
    ):
        raise ValueError(f"{label} require exactly five display movies.")


def _normalized_ballot(
    ballot: tuple[RecoveryBallotItem | SessionReaction, ...],
) -> tuple[RecoveryBallotItem, ...]:
    return tuple(
        item
        if isinstance(item, RecoveryBallotItem)
        else RecoveryBallotItem(
            source_movie_id=item.source_movie_id,
            reaction_label=item.reaction_label,
        )
        for item in ballot
    )


def _validate_command_identifier_types(
    command_id: object,
    canonical_session_id: object,
) -> None:
    if not isinstance(command_id, str):
        raise ValueError("Recovery command ids must be text.")
    if not isinstance(canonical_session_id, str):
        raise ValueError("Recovery session ids must be text.")


def _validate_optional_command_identifier_types(
    command_id: object,
    canonical_session_id: object,
) -> None:
    if not isinstance(command_id, str):
        raise ValueError("Recovery command ids must be text.")
    if canonical_session_id is not None and not isinstance(
        canonical_session_id,
        str,
    ):
        raise ValueError("Recovery session ids must be text.")


def _bounded_text(value: str, label: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text.")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{label} is required.")
    if len(normalized) > maximum:
        raise ValueError(f"{label} is too long.")
    return normalized


def _optional_bounded_text(
    value: str | None,
    label: str,
    maximum: int,
) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text.")
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > maximum:
        raise ValueError(f"{label} is too long.")
    return normalized


def _optional_https_url(value: str | None, label: str) -> str | None:
    normalized = _optional_bounded_text(
        value,
        label,
        MAX_RECOVERY_POSTER_URL_LENGTH,
    )
    if normalized is not None and not normalized.startswith("https://"):
        raise ValueError(f"{label} must use HTTPS.")
    return normalized


def _bounded_text_tuple(
    values: tuple[str, ...],
    label: str,
    *,
    count: int,
    length: int,
) -> tuple[str, ...]:
    if not isinstance(values, tuple) or len(values) > count:
        raise ValueError(f"{label} values exceed their allowed count.")
    return tuple(_bounded_text(value, label, length) for value in values)


def _is_public_positive_evidence(value: str) -> bool:
    return (
        value
        in {
            "shared:overlap_strength",
            "shared:bridge_value",
            "learned_taste:present",
            "title_similarity:present",
        }
        or value.startswith(
            (
                "nudge_person:",
                "nudge_signal:include:",
                "tonight_intent:",
                "profile_concept:likes:",
            )
        )
    )
