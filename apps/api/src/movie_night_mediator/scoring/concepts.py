from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re

from movie_night_mediator.domain import (
    Candidate,
    OnboardingSeed,
    ProfileTasteEvidence,
    TonightIntentContract,
    UserProfile,
)


@dataclass(frozen=True)
class ScoringConceptEvidence:
    concept: str
    polarity: str
    source: str
    label: str
    weight: float = 1.0

    @property
    def explanation_label(self) -> str:
        return f"concept:{self.concept}"


@dataclass(frozen=True)
class ProfileConceptAffinity:
    concept: str
    value: float
    source: str
    label: str

    @property
    def explanation_label(self) -> str:
        prefix = "likes" if self.value >= 0 else "dislikes"
        return f"profile_concept:{prefix}:{self.concept}"


class ScoringConceptRegistry:
    """Small V2 concept vocabulary for the first tracer bullet."""

    def concepts_for_candidate(
        self,
        candidate: Candidate,
        *,
        nudge_text: str | None = None,
        tonight_intents: tuple[TonightIntentContract, ...] = (),
    ) -> tuple[ScoringConceptEvidence, ...]:
        evidence: list[ScoringConceptEvidence] = []
        evidence.extend(_genre_concepts(candidate.genres))
        evidence.extend(_feature_concepts(candidate.enrichment_feature_scores))
        evidence.extend(_text_concepts(candidate.overview, source="overview"))
        evidence.extend(_runtime_concepts(candidate.runtime_min))
        if tonight_intents:
            evidence.extend(_structured_nudge_concepts(tonight_intents, candidate=candidate))
        else:
            evidence.extend(_nudge_concepts(nudge_text or "", candidate=candidate))
        return tuple(_dedupe_evidence(evidence))

    def affinities_for_user(
        self,
        user: UserProfile,
    ) -> tuple[ProfileConceptAffinity, ...]:
        affinities: list[ProfileConceptAffinity] = []
        for seed in user.onboarding_seeds:
            affinities.extend(_seed_affinities(seed))
        newest_profile_evidence_at = _newest_rated_at(user.taste_profile_evidence)
        for evidence in user.taste_profile_evidence:
            affinities.extend(
                _profile_evidence_affinities(
                    evidence,
                    newest_profile_evidence_at=newest_profile_evidence_at,
                )
            )
        return tuple(_merge_affinities(affinities))


GENRE_CONCEPTS = {
    "animation": ("animation", "family"),
    "family": ("family",),
    "comedy": ("witty",),
    "mystery": ("mystery", "procedural"),
    "crime": ("procedural",),
    "sci fi": ("cerebral", "first-contact"),
    "science fiction": ("cerebral", "first-contact"),
    "romance": ("romantic",),
    "drama": ("reflective",),
    "action": ("high-energy",),
    "thriller": ("tense",),
    "horror": ("scary",),
}

KEYWORD_CONCEPTS = {
    "animation": ("animation",),
    "cartoon": ("animation",),
    "cartoonish": ("animation",),
    "family": ("family",),
    "kids": ("family",),
    "kid": ("family",),
    "bleak": ("bleak",),
    "cozy": ("cozy",),
    "cerebral": ("cerebral",),
    "romantic": ("romantic",),
    "procedural": ("procedural",),
    "manhunt": ("manhunt",),
    "ensemble": ("ensemble",),
    "courtroom": ("courtroom",),
    "first contact": ("first-contact",),
    "first-contact": ("first-contact",),
    "revenge": ("revenge",),
    "thriller": ("tense",),
    "scary": ("scary",),
    "intense": ("tense",),
    "whodunit": ("mystery", "procedural"),
    "witty": ("witty",),
    "saccharine": ("saccharine",),
    "slow": ("slow",),
    "slow burn": ("slow",),
    "slow-burn": ("slow",),
}

NEGATIVE_NUDGE_PATTERNS = (
    (re.compile(r"\b(?:no|avoid|not|without)\s+(?:kids?|children|family)\b"), "family"),
    (re.compile(r"\b(?:no|avoid|not|without)\s+(?:cartoonish|cartoons?|animation|animated)\b"), "animation"),
    (re.compile(r"\b(?:no|avoid|not|without)\s+bleak\b"), "bleak"),
    (re.compile(r"\b(?:no|avoid|not|without)\s+saccharine\b"), "saccharine"),
    (re.compile(r"\b(?:no|avoid|not|without)\s+slow\b"), "slow"),
)

POSITIVE_NUDGE_PATTERNS = (
    (re.compile(r"\bcozy\b"), "cozy"),
    (re.compile(r"\bcerebral\b"), "cerebral"),
    (re.compile(r"\bromantic\b"), "romantic"),
    (re.compile(r"\bprocedural\b"), "procedural"),
    (re.compile(r"\bcourtroom\b"), "courtroom"),
    (re.compile(r"\bfirst[- ]contact\b"), "first-contact"),
    (re.compile(r"\brevenge\b"), "revenge"),
    (re.compile(r"\bwhodunit\b"), "mystery"),
    (re.compile(r"\bwitty|clever\b"), "witty"),
)


def _genre_concepts(genres: tuple[str, ...]) -> tuple[ScoringConceptEvidence, ...]:
    evidence = []
    for genre in genres:
        for concept in GENRE_CONCEPTS.get(_normalize(genre), ()):
            evidence.append(
                ScoringConceptEvidence(
                    concept=concept,
                    polarity="positive",
                    source="genre",
                    label=genre,
                    weight=0.6,
                )
            )
    return tuple(evidence)


def _seed_affinities(seed: OnboardingSeed) -> tuple[ProfileConceptAffinity, ...]:
    value = {"loved": 0.7, "fine": 0.25, "no": -0.8}.get(seed.label, 0.0)
    if value == 0.0:
        return ()
    evidence = [
        *_genre_concepts(seed.genres),
        *_text_concepts(seed.notes or "", source="seed_note"),
        *_text_concepts(seed.title, source="seed_title"),
    ]
    return tuple(
        ProfileConceptAffinity(
            concept=item.concept,
            value=value * item.weight,
            source="onboarding_seed",
            label=seed.title,
        )
        for item in evidence
    )


def _profile_evidence_affinities(
    evidence: ProfileTasteEvidence,
    *,
    newest_profile_evidence_at: datetime | None,
) -> tuple[ProfileConceptAffinity, ...]:
    if evidence.preference_value is None:
        return ()
    reliability = _source_reliability(evidence.source)
    recency = _recency_weight(evidence.rated_at, newest_profile_evidence_at)
    concept_evidence = [
        *_genre_concepts(evidence.genres),
        *_text_concepts(evidence.title, source="profile_title"),
    ]
    return tuple(
        ProfileConceptAffinity(
            concept=item.concept,
            value=evidence.preference_value * reliability * recency * item.weight,
            source=evidence.source,
            label=evidence.title,
        )
        for item in concept_evidence
    )


def _feature_concepts(feature_scores) -> tuple[ScoringConceptEvidence, ...]:
    evidence = []
    for feature, score in feature_scores.items():
        for concept in _concepts_for_keyword(feature):
            evidence.append(
                ScoringConceptEvidence(
                    concept=concept,
                    polarity="positive",
                    source="feature_tag",
                    label=feature,
                    weight=float(score),
                )
            )
    return tuple(evidence)


def _text_concepts(
    text: str,
    *,
    source: str,
) -> tuple[ScoringConceptEvidence, ...]:
    normalized = _normalize(text)
    evidence = []
    for keyword, concepts in KEYWORD_CONCEPTS.items():
        if keyword in normalized:
            for concept in concepts:
                evidence.append(
                    ScoringConceptEvidence(
                        concept=concept,
                        polarity="positive",
                        source=source,
                        label=keyword,
                        weight=0.5,
                    )
                )
    return tuple(evidence)


def _runtime_concepts(runtime_min: int | None) -> tuple[ScoringConceptEvidence, ...]:
    if runtime_min is None:
        return ()
    if runtime_min <= 95:
        return (
            ScoringConceptEvidence(
                concept="short-runtime",
                polarity="positive",
                source="runtime",
                label=str(runtime_min),
                weight=0.4,
            ),
        )
    if runtime_min >= 140:
        return (
            ScoringConceptEvidence(
                concept="long-runtime",
                polarity="positive",
                source="runtime",
                label=str(runtime_min),
                weight=0.4,
            ),
        )
    return ()


def _nudge_concepts(
    nudge_text: str,
    *,
    candidate: Candidate,
) -> tuple[ScoringConceptEvidence, ...]:
    if not nudge_text.strip():
        return ()
    normalized = _normalize(nudge_text)
    candidate_concepts = {
        evidence.concept
        for evidence in (
            *_genre_concepts(candidate.genres),
            *_feature_concepts(candidate.enrichment_feature_scores),
            *_text_concepts(candidate.overview, source="overview"),
        )
    }
    evidence = []
    for pattern, concept in NEGATIVE_NUDGE_PATTERNS:
        if pattern.search(normalized) and concept in candidate_concepts:
            evidence.append(
                ScoringConceptEvidence(
                    concept=concept,
                    polarity="negative",
                    source="nudge_exclusion",
                    label=pattern.pattern,
                    weight=-1.0,
                )
            )
    for pattern, concept in POSITIVE_NUDGE_PATTERNS:
        if pattern.search(normalized) and concept in candidate_concepts:
            evidence.append(
                ScoringConceptEvidence(
                    concept=concept,
                    polarity="positive",
                    source="nudge_inclusion",
                    label=pattern.pattern,
                    weight=0.8,
                )
            )
    return tuple(evidence)


def _structured_nudge_concepts(
    tonight_intents: tuple[TonightIntentContract, ...],
    *,
    candidate: Candidate,
) -> tuple[ScoringConceptEvidence, ...]:
    candidate_concepts = {
        evidence.concept
        for evidence in (
            *_genre_concepts(candidate.genres),
            *_feature_concepts(candidate.enrichment_feature_scores),
            *_text_concepts(candidate.overview, source="overview"),
        )
    }
    evidence = []
    for intent in tonight_intents:
        for signal in intent.signals:
            for concept in _concepts_for_signal(signal.concept):
                if concept not in candidate_concepts:
                    continue
                evidence.append(
                    ScoringConceptEvidence(
                        concept=concept,
                        polarity=signal.polarity,
                        source=f"nudge_{signal.polarity}",
                        label=signal.label or signal.concept,
                        weight=_confidence_weight(signal.confidence) * signal.intensity,
                    )
                )
    return tuple(evidence)


def _concepts_for_keyword(keyword: str) -> tuple[str, ...]:
    normalized = _normalize(keyword)
    concepts = []
    for known_keyword, known_concepts in KEYWORD_CONCEPTS.items():
        if known_keyword in normalized:
            concepts.extend(known_concepts)
    return tuple(dict.fromkeys(concepts))


def _concepts_for_signal(signal: str) -> tuple[str, ...]:
    normalized = _normalize(signal)
    concepts = [normalized]
    concepts.extend(_concepts_for_keyword(normalized))
    concepts.extend(
        concept
        for genre, genre_concepts in GENRE_CONCEPTS.items()
        if genre in normalized
        for concept in genre_concepts
    )
    return tuple(dict.fromkeys(concepts))


def _confidence_weight(confidence: str) -> float:
    return {"high": 1.0, "medium": 0.7, "low": 0.45}.get(
        confidence.casefold(),
        0.7,
    )


def _dedupe_evidence(
    evidence: list[ScoringConceptEvidence],
) -> tuple[ScoringConceptEvidence, ...]:
    by_key = {}
    for item in evidence:
        key = (item.concept, item.polarity, item.source)
        existing = by_key.get(key)
        if existing is None or abs(item.weight) > abs(existing.weight):
            by_key[key] = item
    return tuple(by_key.values())


def _merge_affinities(
    affinities: list[ProfileConceptAffinity],
) -> tuple[ProfileConceptAffinity, ...]:
    totals: dict[str, float] = {}
    labels: dict[str, list[str]] = {}
    sources: dict[str, list[str]] = {}
    for affinity in affinities:
        totals[affinity.concept] = totals.get(affinity.concept, 0.0) + affinity.value
        labels.setdefault(affinity.concept, []).append(affinity.label)
        sources.setdefault(affinity.concept, []).append(affinity.source)
    return tuple(
        ProfileConceptAffinity(
            concept=concept,
            value=max(-1.0, min(1.0, value)),
            source=", ".join(dict.fromkeys(sources[concept])),
            label=", ".join(dict.fromkeys(labels[concept])),
        )
        for concept, value in sorted(totals.items())
        if abs(value) >= 0.05
    )


def _source_reliability(source: str) -> float:
    if source == "memory:post_watch_feedback":
        return 1.0
    if source == "taste_lab":
        return 0.85
    if source.startswith("memory:"):
        return 0.75
    if source == "app_memory":
        return 0.7
    return 0.55


def _newest_rated_at(
    evidence_items: tuple[ProfileTasteEvidence, ...],
) -> datetime | None:
    timestamps = tuple(
        parsed
        for evidence in evidence_items
        if evidence.rated_at is not None
        for parsed in (_parse_timestamp(evidence.rated_at),)
        if parsed is not None
    )
    if not timestamps:
        return None
    return max(timestamps)


def _recency_weight(
    rated_at: str | None,
    newest_profile_evidence_at: datetime | None,
) -> float:
    if rated_at is None or newest_profile_evidence_at is None:
        return 0.9
    parsed = _parse_timestamp(rated_at)
    if parsed is None:
        return 0.75
    age_days = max(0, (newest_profile_evidence_at - parsed).days)
    if age_days <= 30:
        return 1.0
    if age_days <= 180:
        return 0.85
    if age_days <= 365:
        return 0.7
    return 0.55


def _parse_timestamp(value: str) -> datetime | None:
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").split())
