#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
REPORT_JSON = REPO_ROOT / "docs" / "validation" / "scoring-v2-v1-baseline.json"
REPORT_MD = REPO_ROOT / "docs" / "validation" / "scoring-v2-v1-baseline.md"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.domain import (  # noqa: E402
    AudienceMode,
    Candidate,
    HouseholdDefaults,
    MediaType,
    ProfileTasteEvidence,
    ProviderAccessType,
    ProviderAvailability,
    ScoringRequest,
    SessionContext,
    SessionMode,
    UserProfile,
)
from movie_night_mediator.scoring import HeuristicScorer  # noqa: E402


@dataclass(frozen=True)
class BaselineScenario:
    name: str
    category: str
    user_story: str
    expected_behavior: str
    expected_positive_concepts: tuple[str, ...]
    expected_penalties: tuple[str, ...]
    expected_confidence_behavior: str
    preferred_title: str | None
    avoided_title: str | None
    request: ScoringRequest


def main() -> None:
    report = build_report()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    REPORT_MD.write_text(_markdown_report(report))
    print(json.dumps(report, indent=2, sort_keys=True))


def build_report() -> dict[str, Any]:
    results = [_run_scenario(scenario) for scenario in _scenarios()]
    status_counts = {
        "success": sum(1 for result in results if result["v1_status"] == "success"),
        "partial": sum(1 for result in results if result["v1_status"] == "partial"),
        "miss": sum(1 for result in results if result["v1_status"] == "miss"),
    }
    required_categories = {
        "negative_preference",
        "actor_driven",
        "subtle_tone",
        "solo_favorite",
        "mismatch_suppression",
        "household_bridge",
        "no_strong_match",
    }
    present_categories = {result["category"] for result in results}

    return {
        "phase": "Scoring V2: Evaluation Corpus And V1 Baseline",
        "report_date": "2026-07-09",
        "command": "pnpm eval:scoring-v2:v1",
        "scenario_count": len(results),
        "required_categories_present": required_categories <= present_categories,
        "results": results,
        "summary": {
            "status_counts": status_counts,
            "known_v1_misses": [
                result["name"] for result in results if result["v1_status"] == "miss"
            ],
            "known_v1_partials": [
                result["name"] for result in results if result["v1_status"] == "partial"
            ],
            "harness_passed": len(results) >= 7
            and required_categories <= present_categories
            and all(result["top_five_titles"] for result in results),
        },
        "risk_notes": [
            "This is a deterministic V1 baseline, not a claim that V1 should pass every V2 scenario.",
            "The report captures title ordering, signal families, expected concepts, expected penalties, and confidence expectations before V2 scorer semantics change.",
            "Known misses are useful because they define what V2 should improve without tuning against hidden behavior.",
            "Live TMDb latency and phone-sized dogfood remain later acceptance gates.",
        ],
    }


def _run_scenario(scenario: BaselineScenario) -> dict[str, Any]:
    result = HeuristicScorer().score(scenario.request)
    ranked = result.ranked_candidates
    preferred = _ranked_by_title(ranked, scenario.preferred_title)
    avoided = _ranked_by_title(ranked, scenario.avoided_title)
    top_pick = ranked[0] if ranked else None
    preferred_rank = preferred.candidate_rank if preferred is not None else None
    avoided_rank = avoided.candidate_rank if avoided is not None else None
    ordering_met = _ordering_met(preferred_rank, avoided_rank)
    signal_families = _signal_families(preferred or top_pick)
    evidence_labels = _evidence_labels(preferred or top_pick)
    concept_hits = [
        concept
        for concept in scenario.expected_positive_concepts
        if _contains_casefold(evidence_labels, concept)
    ]
    penalty_hits = [
        penalty
        for penalty in scenario.expected_penalties
        if _contains_casefold(evidence_labels, penalty)
    ]
    confidence_met = _confidence_met(
        expected=scenario.expected_confidence_behavior,
        is_uncertain=result.is_uncertain,
        ranked_count=len(ranked),
    )
    v1_status = _v1_status(
        ordering_met=ordering_met,
        concept_hits=concept_hits,
        expected_positive_concepts=scenario.expected_positive_concepts,
        penalty_hits=penalty_hits,
        expected_penalties=scenario.expected_penalties,
        confidence_met=confidence_met,
        expected_confidence_behavior=scenario.expected_confidence_behavior,
    )

    return {
        "name": scenario.name,
        "category": scenario.category,
        "user_story": scenario.user_story,
        "expected_behavior": scenario.expected_behavior,
        "expected_positive_concepts": list(scenario.expected_positive_concepts),
        "expected_penalties": list(scenario.expected_penalties),
        "expected_confidence_behavior": scenario.expected_confidence_behavior,
        "top_five_titles": [candidate.title for candidate in ranked[:5]],
        "preferred_title": scenario.preferred_title,
        "preferred_rank": preferred_rank,
        "avoided_title": scenario.avoided_title,
        "avoided_rank": avoided_rank,
        "top_pick_title": top_pick.title if top_pick is not None else None,
        "top_pick_explanation": top_pick.why_short if top_pick is not None else None,
        "preferred_explanation": preferred.why_short if preferred is not None else None,
        "signal_families": signal_families,
        "evidence_labels": evidence_labels,
        "concept_hits": concept_hits,
        "penalty_hits": penalty_hits,
        "is_uncertain": result.is_uncertain,
        "uncertainty_reason": result.uncertainty_reason,
        "recommended_follow_up": result.recommended_follow_up,
        "v1_status": v1_status,
        "v2_gap": _v2_gap(
            scenario=scenario,
            ordering_met=ordering_met,
            concept_hits=concept_hits,
            penalty_hits=penalty_hits,
            confidence_met=confidence_met,
        ),
    }


def _ordering_met(preferred_rank: int | None, avoided_rank: int | None) -> bool:
    if preferred_rank is None and avoided_rank is None:
        return True
    if preferred_rank is None:
        return False
    if avoided_rank is None:
        return True
    return preferred_rank < avoided_rank


def _confidence_met(
    *,
    expected: str,
    is_uncertain: bool,
    ranked_count: int,
) -> bool:
    if expected == "high_confidence":
        return not is_uncertain and ranked_count >= 5
    if expected == "low_confidence_or_no_strong_match":
        return is_uncertain or ranked_count == 0
    if expected == "over_constraint_honesty":
        return ranked_count == 0
    return True


def _v1_status(
    *,
    ordering_met: bool,
    concept_hits: list[str],
    expected_positive_concepts: tuple[str, ...],
    penalty_hits: list[str],
    expected_penalties: tuple[str, ...],
    confidence_met: bool,
    expected_confidence_behavior: str,
) -> str:
    concepts_met = not expected_positive_concepts or len(concept_hits) == len(
        expected_positive_concepts
    )
    penalties_met = not expected_penalties or len(penalty_hits) == len(expected_penalties)
    confidence_is_material = expected_confidence_behavior != "not_required"
    if ordering_met and concepts_met and penalties_met and confidence_met:
        return "success"
    if ordering_met or bool(concept_hits) or bool(penalty_hits) or (
        confidence_is_material and confidence_met
    ):
        return "partial"
    return "miss"


def _v2_gap(
    *,
    scenario: BaselineScenario,
    ordering_met: bool,
    concept_hits: list[str],
    penalty_hits: list[str],
    confidence_met: bool,
) -> str:
    gaps = []
    if not ordering_met:
        gaps.append("ordering")
    missing_concepts = [
        concept
        for concept in scenario.expected_positive_concepts
        if concept not in concept_hits
    ]
    if missing_concepts:
        gaps.append("positive concepts: " + ", ".join(missing_concepts))
    missing_penalties = [
        penalty for penalty in scenario.expected_penalties if penalty not in penalty_hits
    ]
    if missing_penalties:
        gaps.append("penalties: " + ", ".join(missing_penalties))
    if not confidence_met:
        gaps.append("confidence behavior")
    if not gaps:
        return "No major V1 gap for this scenario."
    return "V2 should improve " + "; ".join(gaps) + "."


def _ranked_by_title(ranked, title: str | None):
    if title is None:
        return None
    return next((candidate for candidate in ranked if candidate.title == title), None)


def _signal_families(candidate) -> list[str]:
    if candidate is None or not candidate.scoring_evidence:
        return []
    return list(candidate.scoring_evidence[0].signal_families)


def _evidence_labels(candidate) -> list[str]:
    if candidate is None or not candidate.scoring_evidence:
        return []
    labels = []
    for evidence in candidate.scoring_evidence:
        for contribution in evidence.contributions:
            labels.append(f"{contribution.family}:{contribution.label}")
    return labels


def _contains_casefold(values: list[str], needle: str) -> bool:
    folded = needle.casefold()
    return any(folded in value.casefold() for value in values)


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Scoring V2 V1 Baseline",
        "",
        f"Date: {report['report_date']}",
        f"Phase: {report['phase']}",
        f"Command: `{report['command']}`",
        "",
        "## Summary",
        "",
        f"- Scenario count: {report['scenario_count']}",
        f"- Harness passed: {report['summary']['harness_passed']}",
        f"- V1 successes: {report['summary']['status_counts']['success']}",
        f"- V1 partials: {report['summary']['status_counts']['partial']}",
        f"- V1 misses: {report['summary']['status_counts']['miss']}",
        "",
        "## Scenario Results",
        "",
    ]
    for result in report["results"]:
        lines.extend(
            [
                f"### {result['name']}",
                "",
                f"- Category: {result['category']}",
                f"- User story: {result['user_story']}",
                f"- Expected behavior: {result['expected_behavior']}",
                f"- Top five: {', '.join(result['top_five_titles'])}",
                f"- Preferred: {result['preferred_title']} at rank {result['preferred_rank']}",
                f"- Avoided: {result['avoided_title']} at rank {result['avoided_rank']}",
                f"- Signal families: {', '.join(result['signal_families']) or 'none'}",
                f"- Concept hits: {', '.join(result['concept_hits']) or 'none'}",
                f"- Penalty hits: {', '.join(result['penalty_hits']) or 'none'}",
                f"- V1 status: {result['v1_status']}",
                f"- V2 gap: {result['v2_gap']}",
                "",
            ]
        )
    lines.extend(["## Risk Notes", ""])
    lines.extend(f"- {note}" for note in report["risk_notes"])
    lines.append("")
    return "\n".join(lines)


def _scenarios() -> tuple[BaselineScenario, ...]:
    return (
        BaselineScenario(
            name="negative_kid_animation_request",
            category="negative_preference",
            user_story="As a user, I can say no kids movies and no cartoonish stuff.",
            expected_behavior="Adult mystery should rank above family animation.",
            expected_positive_concepts=("whodunit", "witty"),
            expected_penalties=("animation", "family", "kids"),
            expected_confidence_behavior="not_required",
            preferred_title="Knives Out",
            avoided_title="Spider-Man: Into the Spider-Verse",
            request=_solo_request(
                session_id="scoring-v2-negative-kid-animation",
                mood_text="no kids movies, no cartoonish stuff, something clever",
                user=_tester(
                    evidence=(
                        _evidence("taste_lab", "Knives Out", ("Mystery", "Comedy"), 1.0),
                    ),
                ),
                candidates=(
                    _candidate(
                        "Knives Out",
                        genres=("Mystery", "Comedy"),
                        overview="A witty whodunit about a family inheritance fight.",
                        feature_scores={"whodunit": 0.96, "witty": 0.88},
                    ),
                    _candidate(
                        "Spider-Man: Into the Spider-Verse",
                        genres=("Animation", "Action", "Family"),
                        overview="A teenager becomes a hero in a colorful animated multiverse.",
                        feature_scores={"animation": 0.95, "family": 0.82},
                    ),
                    _candidate(
                        "Paddington",
                        genres=("Comedy", "Family"),
                        overview="A warm family comedy about a gentle bear.",
                        feature_scores={"family": 0.91, "cozy": 0.86},
                    ),
                ),
            ),
        ),
        BaselineScenario(
            name="actor_driven_josh_brolin_request",
            category="actor_driven",
            user_story="As a user, I can ask for a named actor and have that matter.",
            expected_behavior="A Josh Brolin match should outrank a generic action title.",
            expected_positive_concepts=("Josh Brolin", "person"),
            expected_penalties=(),
            expected_confidence_behavior="not_required",
            preferred_title="Sicario",
            avoided_title="Generic Siege",
            request=_solo_request(
                session_id="scoring-v2-actor-driven",
                mood_text="something tense with Josh Brolin",
                user=_tester(
                    evidence=(
                        _evidence("taste_lab", "No Country for Old Men", ("Thriller",), 1.0),
                    ),
                ),
                candidates=(
                    _candidate(
                        "Sicario",
                        genres=("Thriller", "Crime"),
                        overview="A tense border thriller with a hard-edged team.",
                        top_cast=("Emily Blunt", "Benicio del Toro", "Josh Brolin"),
                        matched_person_names=("Josh Brolin",),
                    ),
                    _candidate(
                        "Generic Siege",
                        genres=("Action", "Thriller"),
                        overview="A generic action siege with explosions.",
                    ),
                ),
            ),
        ),
        BaselineScenario(
            name="subtle_tone_cozy_not_saccharine",
            category="subtle_tone",
            user_story="As a user, I can ask for cozy but not saccharine.",
            expected_behavior="A warm grown-up comedy should beat a sweeter family pick.",
            expected_positive_concepts=("cozy", "witty"),
            expected_penalties=("saccharine", "family"),
            expected_confidence_behavior="not_required",
            preferred_title="The Grand Budapest Hotel",
            avoided_title="Paddington",
            request=_solo_request(
                session_id="scoring-v2-cozy-not-saccharine",
                mood_text="cozy but not saccharine",
                user=_tester(
                    evidence=(
                        _evidence("taste_lab", "The Grand Budapest Hotel", ("Comedy",), 1.0),
                    ),
                ),
                candidates=(
                    _candidate(
                        "The Grand Budapest Hotel",
                        genres=("Comedy", "Adventure"),
                        overview="A stylized witty comedy with brisk charm.",
                        feature_scores={"cozy": 0.76, "witty": 0.72, "stylized": 0.95},
                    ),
                    _candidate(
                        "Paddington",
                        genres=("Comedy", "Family"),
                        overview="A very sweet family comedy with gentle lessons.",
                        feature_scores={"cozy": 0.86, "saccharine": 0.74, "family": 0.91},
                    ),
                ),
            ),
        ),
        BaselineScenario(
            name="high_confidence_solo_favorite",
            category="solo_favorite",
            user_story="As a solo user, strong repeated evidence should produce a confident favorite.",
            expected_behavior="Arrival should rank first for a cerebral first-contact profile.",
            expected_positive_concepts=("cerebral", "first-contact", "Taste Lab"),
            expected_penalties=(),
            expected_confidence_behavior="high_confidence",
            preferred_title="Arrival",
            avoided_title="Loud Space Battle",
            request=_solo_request(
                session_id="scoring-v2-high-confidence-solo",
                user=_tester(
                    evidence=(
                        _evidence("taste_lab", "Arrival", ("Sci-Fi", "Drama"), 1.0),
                        _evidence("memory:post_watch_feedback", "Contact", ("Sci-Fi", "Drama"), 1.0),
                        _evidence("memory:post_watch_feedback", "Transformers", ("Action",), -1.0),
                    ),
                ),
                candidates=(
                    _candidate(
                        "Arrival",
                        genres=("Sci-Fi", "Drama"),
                        overview="A cerebral first-contact drama.",
                        feature_scores={"cerebral": 0.91, "first-contact": 0.94},
                    ),
                    _candidate(
                        "Loud Space Battle",
                        genres=("Action", "Sci-Fi"),
                        overview="A loud space battle with little reflection.",
                        feature_scores={"action": 0.86},
                    ),
                    _candidate("Quiet Legal Drama", genres=("Drama",)),
                    _candidate("Witty Mystery", genres=("Mystery", "Comedy")),
                    _candidate("Reflective Romance", genres=("Romance", "Drama")),
                ),
            ),
        ),
        BaselineScenario(
            name="repeated_mismatch_suppression",
            category="mismatch_suppression",
            user_story="As a couple, repeated bad fits should stop resurfacing.",
            expected_behavior="Shared comedy should beat one-sided action after repeated no signals.",
            expected_positive_concepts=("shared", "comedy"),
            expected_penalties=("repeated mismatch", "action"),
            expected_confidence_behavior="not_required",
            preferred_title="Shared Laugh",
            avoided_title="One-Sided Action",
            request=_shared_request(
                session_id="scoring-v2-repeated-mismatch",
                user_a=_tester(
                    label="Husband",
                    evidence=(
                        _evidence("taste_lab", "The Raid", ("Action", "Thriller"), 1.0),
                        _evidence("taste_lab", "Back to the Future", ("Comedy",), 0.5),
                    ),
                ),
                user_b=_tester(
                    user_id="wife",
                    label="Wife",
                    evidence=(
                        _evidence("memory:post_watch_feedback", "John Wick", ("Action",), -1.0),
                        _evidence("memory:post_watch_feedback", "The Raid", ("Action",), -1.0),
                        _evidence("taste_lab", "Back to the Future", ("Comedy",), 1.0),
                    ),
                ),
                candidates=(
                    _candidate("One-Sided Action", genres=("Action", "Thriller")),
                    _candidate("Shared Laugh", genres=("Comedy",)),
                ),
            ),
        ),
        BaselineScenario(
            name="household_bridge_pick",
            category="household_bridge",
            user_story="As a couple, we can get a bridge pick instead of a bland middle.",
            expected_behavior="A cerebral mystery bridge should beat one-sided favorites.",
            expected_positive_concepts=("bridge", "overlap", "cerebral", "mystery"),
            expected_penalties=("veto risk",),
            expected_confidence_behavior="not_required",
            preferred_title="Arrival",
            avoided_title="Pure Action Night",
            request=_shared_request(
                session_id="scoring-v2-household-bridge",
                user_a=_tester(
                    label="Husband",
                    evidence=(
                        _evidence("taste_lab", "Blade Runner 2049", ("Sci-Fi", "Drama"), 1.0),
                        _evidence("taste_lab", "Before Sunrise", ("Romance",), -1.0),
                    ),
                ),
                user_b=_tester(
                    user_id="wife",
                    label="Wife",
                    evidence=(
                        _evidence("taste_lab", "Knives Out", ("Mystery", "Comedy"), 1.0),
                        _evidence("taste_lab", "John Wick", ("Action",), -1.0),
                    ),
                ),
                candidates=(
                    _candidate(
                        "Arrival",
                        genres=("Sci-Fi", "Drama", "Mystery"),
                        overview="A cerebral first-contact mystery about language and grief.",
                        feature_scores={"cerebral": 0.91, "first-contact": 0.94},
                    ),
                    _candidate("Pure Action Night", genres=("Action", "Thriller")),
                    _candidate("Pure Romance Night", genres=("Romance", "Drama")),
                ),
            ),
        ),
        BaselineScenario(
            name="legitimate_no_strong_match",
            category="no_strong_match",
            user_story="As a user, I get an honest no-strong-match state when the request is over-constrained.",
            expected_behavior="The scorer should be uncertain or explicitly say no strong match.",
            expected_positive_concepts=("courtroom", "cozy", "short runtime"),
            expected_penalties=("over constrained",),
            expected_confidence_behavior="over_constraint_honesty",
            preferred_title=None,
            avoided_title=None,
            request=ScoringRequest(
                session=SessionContext(
                    session_id="scoring-v2-no-strong-match",
                    audience_mode=AudienceMode.SOLO,
                    mood_text="cozy courtroom musical under 80 minutes with no subtitles",
                ),
                household_defaults=HouseholdDefaults(),
                users=(UserProfile(user_id="solo", role="solo", display_label="Solo"),),
                candidates=(
                    _candidate("Long Legal Drama", genres=("Drama",), runtime_min=142),
                    _candidate("Foreign Musical", genres=("Music", "Drama"), original_language="fr"),
                ),
            ),
        ),
    )


def _solo_request(
    *,
    session_id: str,
    user: UserProfile,
    candidates: tuple[Candidate, ...],
    mood_text: str | None = None,
) -> ScoringRequest:
    return ScoringRequest(
        session=SessionContext(
            session_id=session_id,
            audience_mode=AudienceMode.SOLO,
            mood_text=mood_text,
        ),
        household_defaults=HouseholdDefaults(),
        users=(user,),
        candidates=candidates,
    )


def _shared_request(
    *,
    session_id: str,
    user_a: UserProfile,
    user_b: UserProfile,
    candidates: tuple[Candidate, ...],
) -> ScoringRequest:
    return ScoringRequest(
        session=SessionContext(
            session_id=session_id,
            audience_mode=AudienceMode.SHARED,
            session_mode=SessionMode.COMPROMISE,
            viewer_user_ids=(user_a.user_id, user_b.user_id),
        ),
        household_defaults=HouseholdDefaults(),
        users=(user_a, user_b),
        candidates=candidates,
    )


def _tester(
    *,
    user_id: str = "cezary-tester",
    label: str = "Cezary - tester",
    evidence: tuple[ProfileTasteEvidence, ...] = (),
) -> UserProfile:
    return UserProfile(
        user_id=user_id,
        role="solo" if user_id == "cezary-tester" else "partner",
        display_label=label,
        taste_profile_evidence=evidence,
    )


def _evidence(
    source: str,
    title: str,
    genres: tuple[str, ...],
    preference_value: float,
) -> ProfileTasteEvidence:
    return ProfileTasteEvidence(
        source=source,
        source_movie_id=f"fixture:{title.casefold().replace(' ', '-')}",
        title=title,
        genres=genres,
        preference_value=preference_value,
        source_label="fixture",
        rated_at="2026-07-09T00:00:00Z",
    )


def _candidate(
    title: str,
    *,
    genres: tuple[str, ...],
    overview: str = "",
    runtime_min: int = 110,
    original_language: str = "en",
    top_cast: tuple[str, ...] = (),
    matched_person_names: tuple[str, ...] = (),
    feature_scores: dict[str, float] | None = None,
) -> Candidate:
    return Candidate(
        source_movie_id=f"fixture:{title.casefold().replace(' ', '-')}",
        title=title,
        media_type=MediaType.MOVIE,
        release_year=2020,
        runtime_min=runtime_min,
        genres=genres,
        overview=overview,
        top_cast=top_cast,
        providers=("Prime Video",),
        provider_availability=(
            ProviderAvailability(
                provider_name="Prime Video",
                access_type=ProviderAccessType.FLATRATE,
                region="DE",
            ),
        ),
        original_language=original_language,
        spoken_languages=(original_language,),
        enrichment_status="enriched" if feature_scores else "fallback",
        enrichment_provider=(
            "movielens-tag-genome-fixture"
            if feature_scores
            else "tmdb-metadata-fallback"
        ),
        enrichment_feature_scores=feature_scores or {},
        matched_person_names=matched_person_names,
    )


if __name__ == "__main__":
    main()
