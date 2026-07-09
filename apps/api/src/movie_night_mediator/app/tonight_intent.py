from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from movie_night_mediator.mvp_plus_3 import (
    DirectedNudge,
    DirectedNudgeResolution,
    DirectedNudgeStatus,
    PersonCandidateIntent,
)
from movie_night_mediator.mvp_plus_2 import (
    IntentInterpretation,
    IntentInterpretationStatus,
)


class TonightIntentProvider(Protocol):
    def interpret(self, text: str) -> IntentInterpretation:
        """Return structured tonight intent without ranking candidate movies."""


class DirectedNudgeProvider(Protocol):
    def interpret_directed_nudge(self, text: str) -> DirectedNudge:
        """Return a structured active nudge without ranking candidate movies."""


@dataclass(frozen=True)
class TonightIntentInterpreter:
    deterministic_provider: DeterministicTonightIntentProvider = field(
        default_factory=lambda: DeterministicTonightIntentProvider()
    )
    directed_nudge_provider: DirectedNudgeProvider | None = None

    def interpret(self, text: str) -> IntentInterpretation:
        return self.deterministic_provider.interpret(text)

    def interpret_directed_nudge(self, text: str) -> DirectedNudge:
        deterministic = self.deterministic_provider.interpret_directed_nudge(text)
        if self.directed_nudge_provider is not None:
            try:
                live_nudge = self.directed_nudge_provider.interpret_directed_nudge(text)
                return _merge_directed_nudges(
                    raw_text=text,
                    deterministic=deterministic,
                    live_nudge=live_nudge,
                )
            except ValueError:
                pass

        return deterministic


@dataclass(frozen=True)
class DeterministicTonightIntentProvider:
    def interpret(self, text: str) -> IntentInterpretation:
        normalized_text = _require_text(text)
        lowered_text = normalized_text.casefold()

        filters: dict[str, object] = {}
        soft_signals: list[str] = []

        if _needs_emotional_clarification(lowered_text):
            return IntentInterpretation(
                raw_text=normalized_text,
                status=IntentInterpretationStatus.CLARIFICATION_REQUIRED,
                clarification_question=(
                    "Do you want something comforting, or something that matches the mood?"
                ),
                soft_signals=tuple(_dedupe(soft_signals + ["emotional"])),
                confidence="medium",
            )

        year_range = _year_range(lowered_text)
        if year_range is not None:
            filters["release_year_min"] = year_range[0]
            filters["release_year_max"] = year_range[1]
            soft_signals.append(f"{year_range[0]}s")

        person_name = _person_request(normalized_text)
        if person_name is not None:
            filters["people"] = [person_name]
            soft_signals.append("person-request")

        franchise = _franchise_request(lowered_text)
        if franchise is not None:
            filters["franchise"] = franchise
            soft_signals.append("franchise-request")

        if _asks_to_avoid_seen(lowered_text):
            filters["exclude_watched"] = True
            soft_signals.append("not-seen")

        genre_signals = _genre_signals(lowered_text)
        if genre_signals:
            filters["genres"] = list(genre_signals)
            soft_signals.extend(signal.casefold() for signal in genre_signals)

        tone_signals = _tone_signals(lowered_text)
        soft_signals.extend(tone_signals)

        if not filters and not soft_signals:
            soft_signals.append("open-ended")

        return IntentInterpretation(
            raw_text=normalized_text,
            status=IntentInterpretationStatus.CONFIRMATION_REQUIRED,
            confirmation_text=_confirmation_text(filters, tuple(_dedupe(soft_signals))),
            filters=filters,
            soft_signals=tuple(_dedupe(soft_signals)),
            confidence="high" if filters else "medium",
        )

    def interpret_directed_nudge(self, text: str) -> DirectedNudge:
        normalized_text = _require_text(text)
        lowered_text = normalized_text.casefold()

        filters: dict[str, object] = {}
        soft_signals: list[str] = []
        excluded_signals: list[str] = []

        year_range = _year_range(lowered_text)
        if year_range is not None:
            filters["release_year_min"] = year_range[0]
            filters["release_year_max"] = year_range[1]
            soft_signals.append(f"{year_range[0]}s")

        if _asks_to_avoid_seen(lowered_text):
            filters["exclude_watched"] = True
            soft_signals.append("not-seen")

        if _asks_to_avoid_subtitles(lowered_text):
            filters["exclude_subtitled"] = True
            excluded_signals.append("subtitles")

        genre_signals = _genre_signals(lowered_text)
        if genre_signals:
            filters["genres"] = list(genre_signals)
            soft_signals.extend(signal.casefold() for signal in genre_signals)

        tone_signals = _tone_signals(lowered_text)
        soft_signals.extend(tone_signals)
        soft_signals.extend(_directed_mood_signals(lowered_text))
        excluded_signals.extend(_excluded_signals(lowered_text))

        person_intents = _person_intents(normalized_text)
        if person_intents:
            filters["people"] = [intent.raw_name for intent in person_intents]
            soft_signals.append("person-request")

        excluded_signals = list(_dedupe(excluded_signals))
        soft_signals = [
            signal
            for signal in _dedupe(soft_signals)
            if signal not in excluded_signals
        ]

        if _needs_directed_clarification(
            lowered_text=lowered_text,
            filters=filters,
            soft_signals=soft_signals,
            excluded_signals=excluded_signals,
            person_intents=person_intents,
        ):
            return DirectedNudge(
                raw_text=normalized_text,
                status=DirectedNudgeStatus.CLARIFICATION_REQUIRED,
                clarification_question=(
                    "Do you want something comforting, or something that matches the mood?"
                ),
                soft_signals=tuple(_dedupe(soft_signals + ["emotional"])),
                excluded_signals=tuple(excluded_signals),
                person_intents=person_intents,
                confidence="medium",
            )

        resolution = _directed_resolution(
            normalized_text=normalized_text,
            lowered_text=lowered_text,
            filters=filters,
            soft_signals=soft_signals,
            excluded_signals=excluded_signals,
            person_intents=person_intents,
        )
        if resolution == DirectedNudgeResolution.UNSUPPORTED:
            return DirectedNudge(
                raw_text=normalized_text,
                status=DirectedNudgeStatus.CONFIRMATION_REQUIRED,
                resolution=resolution,
                user_facing_summary=(
                    f'I cannot filter directly on "{normalized_text}" yet.'
                ),
                unsupported_reason=(
                    "I can currently steer by person, genre, decade, subtitle rules, and a few concrete mood cues."
                ),
                filters={},
                soft_signals=(),
                excluded_signals=(),
                person_intents=(),
                confidence="low",
            )

        if not filters and not soft_signals and not excluded_signals:
            soft_signals.append("open-ended")

        return DirectedNudge(
            raw_text=normalized_text,
            status=DirectedNudgeStatus.CONFIRMATION_REQUIRED,
            resolution=resolution,
            user_facing_summary=_directed_summary(
                filters=filters,
                soft_signals=tuple(_dedupe(soft_signals)),
                excluded_signals=tuple(_dedupe(excluded_signals)),
                person_intents=person_intents,
            ),
            filters=filters,
            soft_signals=tuple(_dedupe(soft_signals)),
            excluded_signals=tuple(_dedupe(excluded_signals)),
            person_intents=person_intents,
            confidence=(
                "high"
                if filters or excluded_signals or person_intents
                else "medium"
            ),
        )


def _require_text(text: str) -> str:
    normalized_text = text.strip()
    if not normalized_text:
        raise ValueError("Tonight intent requires text.")

    return normalized_text


def _needs_emotional_clarification(text: str) -> bool:
    emotional_patterns = (
        "sad",
        "down",
        "rough day",
        "bad day",
        "depressed",
        "miserable",
        "ugh",
    )
    concrete_patterns = (
        "comfort",
        "cozy",
        "laugh",
        "funny",
        "silly",
        "light",
        "cheer",
    )
    return any(pattern in text for pattern in emotional_patterns) and not any(
        pattern in text for pattern in concrete_patterns
    )


def _year_range(text: str) -> tuple[int, int] | None:
    if re.search(r"\b(90s|1990s|nineties)\b", text):
        return (1990, 1999)
    if re.search(r"\b(80s|1980s|eighties)\b", text):
        return (1980, 1989)
    if re.search(r"\b(70s|1970s|seventies)\b", text):
        return (1970, 1979)

    match = re.search(r"\b(19|20)\d{2}\b", text)
    if match is None:
        return None

    year = int(match.group(0))
    return (year, year)


def _person_request(text: str) -> str | None:
    for pattern in (
        r"\binclude\s+([A-Za-z]+(?:\s+[A-Za-z]+){1,3})\b",
        r"\ba\s+([A-Za-z]+(?:\s+[A-Za-z]+){1,3})\s+(?:movie|film|show)\b",
        r"\bwith\s+([A-Za-z]+(?:\s+[A-Za-z]+){1,3})\b",
        r"\bstarring\s+([A-Za-z]+(?:\s+[A-Za-z]+){1,3})\b",
        r"\bby\s+([A-Za-z]+(?:\s+[A-Za-z]+){1,3})\b",
        r"\bfrom\s+([A-Za-z]+(?:\s+[A-Za-z]+){1,3})\b",
    ):
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match is not None:
            candidate_name = _normalize_person_name(match.group(1))
            if _looks_like_person_name(candidate_name):
                return candidate_name

    return None


def _person_intents(text: str) -> tuple[PersonCandidateIntent, ...]:
    names: list[str] = []
    for pattern in (
        r"\binclude\s+([A-Za-z]+(?:\s+[A-Za-z]+){1,3})\b",
        r"\b([A-Za-z]+(?:\s+[A-Za-z]+){1,3}?)\s+(?:should\s+be\s+)?in it\b",
        r"\bwith\s+([A-Za-z]+(?:\s+[A-Za-z]+){1,3})\b",
        r"\bstarring\s+([A-Za-z]+(?:\s+[A-Za-z]+){1,3})\b",
    ):
        names.extend(
            _normalize_person_name(match.group(1))
            for match in re.finditer(pattern, text, flags=re.IGNORECASE)
        )

    if request_name := _person_request(text):
        names.append(request_name)

    return tuple(
        PersonCandidateIntent(raw_name=name, normalized_name=name.casefold())
        for name in _dedupe(names)
    )


def _normalize_person_name(value: str) -> str:
    return " ".join(part[:1].upper() + part[1:].lower() for part in value.strip().split())


def _looks_like_person_name(value: str) -> bool:
    blocked_tokens = {
        "very",
        "green",
        "blue",
        "red",
        "purple",
        "pink",
        "yellow",
        "movie",
        "film",
        "show",
        "scary",
        "funny",
        "sad",
        "intense",
        "weird",
        "cozy",
        "romantic",
        "action",
        "horror",
        "comedy",
        "beautiful",
        "dark",
        "light",
        "open",
        "ended",
    }
    parts = [part.casefold() for part in value.split()]
    return bool(parts) and all(part not in blocked_tokens for part in parts)


def _franchise_request(text: str) -> str | None:
    franchises = {
        "star wars": "Star Wars",
        "lord of the rings": "The Lord of the Rings",
        "harry potter": "Harry Potter",
        "mission impossible": "Mission: Impossible",
        "jurassic park": "Jurassic Park",
        "jurassic world": "Jurassic World",
        "fast and furious": "Fast & Furious",
    }
    for phrase, label in franchises.items():
        if phrase in text:
            return label

    return None


def _asks_to_avoid_seen(text: str) -> bool:
    return any(
        phrase in text
        for phrase in (
            "haven't seen",
            "have not seen",
            "not seen",
            "new to us",
            "unseen",
        )
    )


def _asks_to_avoid_subtitles(text: str) -> bool:
    return any(
        phrase in text
        for phrase in (
            "nothing with subtitles",
            "no subtitles",
            "not subtitled",
            "without subtitles",
        )
    )


def _genre_signals(text: str) -> tuple[str, ...]:
    genres: list[str] = []
    if any(word in text for word in ("laugh", "funny", "silly", "comedy", "comedies")):
        genres.append("Comedy")
    if any(word in text for word in ("scary", "horror", "spooky")):
        genres.append("Horror")
    if any(word in text for word in ("action", "explosive", "fight")):
        genres.append("Action")
    if any(
        word in text
        for word in (
            "crime",
            "criminal",
            "mob",
            "gangster",
            "hitman",
            "drug deal",
        )
    ):
        genres.append("Crime")
    if any(word in text for word in ("romantic", "romance", "date night")):
        genres.append("Romance")
    if any(word in text for word in ("mystery", "detective", "whodunit")):
        genres.append("Mystery")
    if "thriller" in text:
        genres.append("Thriller")
    if any(word in text for word in ("sci-fi", "science fiction", "space")):
        genres.append("Sci-Fi")
    if any(word in text for word in ("western", "neo-western", "cowboy", "frontier", "sheriff")):
        genres.append("Western")
    if any(word in text for word in ("drama", "dramatic")):
        genres.append("Drama")

    excluded = _normalized_excluded_signals(_excluded_signals(text))
    return tuple(
        genre for genre in _dedupe(genres) if _normalize_signal(genre) not in excluded
    )


def _tone_signals(text: str) -> tuple[str, ...]:
    signals: list[str] = []
    if any(word in text for word in ("light", "easy", "cozy", "comfort")):
        signals.append("comforting")
    if any(word in text for word in ("dark", "intense", "serious", "tense", "ruthless")):
        signals.append("intense")
    if "bleak" in text:
        signals.append("bleak")
    if "beautiful" in text:
        signals.append("beautiful")
    if any(word in text for word in ("weird", "strange", "offbeat")):
        signals.append("offbeat")
    if any(word in text for word in ("slow-burn", "slow burn", "patient")):
        signals.append("slow-burn")
    if any(word in text for word in ("desert", "borderland", "west texas")):
        signals.append("desert")
    if any(word in text for word in ("manhunt", "cat-and-mouse", "cat and mouse", "hunter", "chase")):
        signals.append("manhunt")
    if "sheriff" in text:
        signals.append("lawman")
    if any(word in text for word in ("killer", "hitman")):
        signals.append("killer")
    if "tonight" in text:
        signals.append("tonight")

    return tuple(_dedupe(signals))


def _directed_mood_signals(text: str) -> tuple[str, ...]:
    signals: list[str] = []
    if "sad" in text:
        signals.append("sad")

    return tuple(_dedupe(signals))


def _excluded_signals(text: str) -> tuple[str, ...]:
    exclusions: list[str] = []
    for match in re.finditer(
        r"\b(?:not|no|nothing with|without)\s+([a-z][a-z-]+)\b",
        text,
    ):
        excluded_signal = match.group(1)
        if excluded_signal not in {"seen", "subtitles", "subtitled"}:
            exclusions.append(excluded_signal)

    return tuple(_dedupe(exclusions))


def _normalize_signal(value: str) -> str:
    lowered = value.strip().casefold()
    aliases = {
        "science fiction": "sci-fi",
        "sci fi": "sci-fi",
        "scifi": "sci-fi",
        "romantic": "romance",
        "comedies": "comedy",
        "subtitled": "subtitles",
    }
    return aliases.get(lowered, lowered)


def _normalized_excluded_signals(excluded_signals: tuple[str, ...]) -> set[str]:
    return {_normalize_signal(signal) for signal in excluded_signals}


def _needs_directed_clarification(
    *,
    lowered_text: str,
    filters: dict[str, object],
    soft_signals: list[str],
    excluded_signals: list[str],
    person_intents: tuple[PersonCandidateIntent, ...],
) -> bool:
    if not _needs_emotional_clarification(lowered_text):
        return False

    if filters or excluded_signals or person_intents:
        return False

    concrete_mood_signals = {"beautiful", "comforting", "offbeat", "intense"}
    return not concrete_mood_signals.intersection(soft_signals)


def _confirmation_text(filters: dict[str, object], soft_signals: tuple[str, ...]) -> str:
    pieces: list[str] = []
    if "release_year_min" in filters and "release_year_max" in filters:
        start = filters["release_year_min"]
        end = filters["release_year_max"]
        pieces.append(f"from {start}" if start == end else f"from {start}-{end}")
    if people := filters.get("people"):
        pieces.append(f"with {', '.join(str(person) for person in people)}")
    if franchise := filters.get("franchise"):
        pieces.append(f"in the {franchise} lane")
    if genres := filters.get("genres"):
        pieces.append(f"leaning {', '.join(str(genre) for genre in genres)}")
    if filters.get("exclude_watched"):
        pieces.append("skipping movies you have already seen")
    if not pieces and soft_signals:
        pieces.append(f"with a {soft_signals[0]} feel")

    return f"Got it: I will look for something {' and '.join(pieces)}."


def _directed_summary(
    *,
    filters: dict[str, object],
    soft_signals: tuple[str, ...],
    excluded_signals: tuple[str, ...],
    person_intents: tuple[PersonCandidateIntent, ...],
) -> str:
    pieces: list[str] = []
    if "release_year_min" in filters and "release_year_max" in filters:
        start = filters["release_year_min"]
        end = filters["release_year_max"]
        pieces.append(f"from {start}" if start == end else f"from {start}-{end}")
    if genres := filters.get("genres"):
        pieces.append(f"leaning {', '.join(str(genre) for genre in genres)}")
    if person_intents:
        pieces.append(
            "with "
            + ", ".join(intent.raw_name for intent in person_intents)
        )
    if filters.get("exclude_watched"):
        pieces.append("skipping movies you have already seen")
    if filters.get("exclude_subtitled"):
        pieces.append("without subtitles")
    if soft_signals:
        tone_signals = [
            signal.replace("-", " ")
            for signal in soft_signals
            if signal
            not in {
                "person-request",
                "tonight",
            }
            and signal.casefold()
            not in {
                str(genre).casefold()
                for genre in filters.get("genres", [])
            }
        ]
        if tone_signals:
            pieces.append(f"with a {' / '.join(tone_signals[:4])} feel")
    if excluded_signals:
        pieces.append(f"not {', '.join(excluded_signals)}")
    if not pieces and soft_signals:
        pieces.append(f"with a {soft_signals[0]} feel")

    return f"Got it: I will keep an active nudge for something {' and '.join(pieces)}."


def _directed_resolution(
    *,
    normalized_text: str,
    lowered_text: str,
    filters: dict[str, object],
    soft_signals: list[str],
    excluded_signals: list[str],
    person_intents: tuple[PersonCandidateIntent, ...],
) -> DirectedNudgeResolution:
    if filters or excluded_signals or person_intents:
        return DirectedNudgeResolution.EXACT

    if soft_signals and any(
        signal in {"comforting", "intense", "bleak", "beautiful", "offbeat"}
        for signal in soft_signals
    ):
        return DirectedNudgeResolution.GUESS

    if _contains_unsupported_aesthetic_prompt(normalized_text, lowered_text):
        return DirectedNudgeResolution.UNSUPPORTED

    return DirectedNudgeResolution.UNSUPPORTED


def _contains_unsupported_aesthetic_prompt(
    normalized_text: str,
    lowered_text: str,
) -> bool:
    unsupported_cues = (
        "green",
        "blue",
        "red",
        "purple",
        "pink",
        "yellow",
        "vibe",
        "aesthetic",
        "energy",
        "feel like a painting",
        "look like a painting",
    )
    return any(cue in lowered_text for cue in unsupported_cues) or bool(normalized_text)


def _merge_directed_nudges(
    *,
    raw_text: str,
    deterministic: DirectedNudge,
    live_nudge: DirectedNudge,
) -> DirectedNudge:
    if live_nudge.status == DirectedNudgeStatus.CLARIFICATION_REQUIRED:
        return live_nudge
    if live_nudge.resolution == DirectedNudgeResolution.UNSUPPORTED:
        return deterministic

    merged_filters: dict[str, object] = dict(live_nudge.filters)
    for key, value in deterministic.filters.items():
        if key not in merged_filters:
            merged_filters[key] = value
            continue
        existing = merged_filters[key]
        if isinstance(existing, list) and isinstance(value, list):
            merged_filters[key] = list(
                dict.fromkeys(
                    [
                        *(item for item in existing if isinstance(item, str)),
                        *(item for item in value if isinstance(item, str)),
                    ]
                )
            )

    merged_soft_signals = _dedupe(
        [*live_nudge.soft_signals, *deterministic.soft_signals]
    )
    merged_excluded_signals = _dedupe(
        [*live_nudge.excluded_signals, *deterministic.excluded_signals]
    )
    normalized_exclusions = _normalized_excluded_signals(merged_excluded_signals)
    if genres := merged_filters.get("genres"):
        merged_filters["genres"] = [
            genre
            for genre in genres
            if isinstance(genre, str)
            and _normalize_signal(genre) not in normalized_exclusions
        ]
        if not merged_filters["genres"]:
            merged_filters.pop("genres")
    merged_soft_signals = _dedupe(
        [
            signal
            for signal in merged_soft_signals
            if _normalize_signal(signal) not in normalized_exclusions
        ]
    )
    merged_person_intents = tuple(
        {
            intent.normalized_name: intent
            for intent in (
                *live_nudge.person_intents,
                *deterministic.person_intents,
            )
        }.values()
    )
    resolution = live_nudge.resolution
    if deterministic.resolution == DirectedNudgeResolution.EXACT:
        resolution = DirectedNudgeResolution.EXACT

    return DirectedNudge(
        raw_text=raw_text,
        status=DirectedNudgeStatus.CONFIRMATION_REQUIRED,
        resolution=resolution,
        user_facing_summary=_directed_summary(
            filters=merged_filters,
            soft_signals=merged_soft_signals,
            excluded_signals=merged_excluded_signals,
            person_intents=merged_person_intents,
        ),
        filters=merged_filters,
        soft_signals=merged_soft_signals,
        excluded_signals=merged_excluded_signals,
        person_intents=merged_person_intents,
        confidence=live_nudge.confidence or deterministic.confidence,
    )


def _dedupe(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))
