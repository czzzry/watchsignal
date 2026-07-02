from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from movie_night_mediator.mvp_plus_2 import (
    IntentInterpretation,
    IntentInterpretationStatus,
)


class TonightIntentProvider(Protocol):
    def interpret(self, text: str) -> IntentInterpretation:
        """Return structured tonight intent without ranking candidate movies."""


@dataclass(frozen=True)
class TonightIntentInterpreter:
    live_provider: TonightIntentProvider | None = None

    def interpret(self, text: str) -> IntentInterpretation:
        if self.live_provider is not None:
            return self.live_provider.interpret(text)

        return DeterministicTonightIntentProvider().interpret(text)


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
    match = re.search(
        r"\b(?:with|starring|by|from|a)\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){1,3})\b",
        text,
    )
    if match is None:
        return None

    name = match.group(1).strip()
    blocked_trailing_words = ("movie", "film", "show")
    for word in blocked_trailing_words:
        if name.casefold().endswith(f" {word}"):
            name = name[: -len(word)].strip()

    return name or None


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


def _genre_signals(text: str) -> tuple[str, ...]:
    genres: list[str] = []
    if any(word in text for word in ("laugh", "funny", "silly", "comedy", "comedies")):
        genres.append("Comedy")
    if any(word in text for word in ("scary", "horror", "spooky")):
        genres.append("Horror")
    if any(word in text for word in ("action", "explosive", "fight")):
        genres.append("Action")
    if any(word in text for word in ("romantic", "romance", "date night")):
        genres.append("Romance")
    if any(word in text for word in ("mystery", "detective", "whodunit")):
        genres.append("Mystery")
    if any(word in text for word in ("sci-fi", "science fiction", "space")):
        genres.append("Sci-Fi")

    return tuple(_dedupe(genres))


def _tone_signals(text: str) -> tuple[str, ...]:
    signals: list[str] = []
    if any(word in text for word in ("light", "easy", "cozy", "comfort")):
        signals.append("comforting")
    if any(word in text for word in ("dark", "intense", "serious")):
        signals.append("intense")
    if any(word in text for word in ("weird", "strange", "offbeat")):
        signals.append("offbeat")
    if "tonight" in text:
        signals.append("tonight")

    return tuple(_dedupe(signals))


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


def _dedupe(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))
