#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
API_SRC = REPO_ROOT / "apps" / "api" / "src"
REPORT_JSON = REPO_ROOT / "docs" / "validation" / "mvp-plus-4-recommendation-evaluation.json"
REPORT_MD = REPO_ROOT / "docs" / "validation" / "mvp-plus-4-recommendation-evaluation.md"
sys.path.insert(0, str(API_SRC))

from movie_night_mediator.domain import (  # noqa: E402
    AudienceMode,
    Candidate,
    HouseholdDefaults,
    MediaType,
    PersonCandidateConstraint,
    ProfileTasteEvidence,
    ProviderAccessType,
    ProviderAvailability,
    RankedCandidate,
    ScoringRequest,
    ScoringSessionReaction,
    SessionContext,
    SessionMode,
    UserProfile,
)
from movie_night_mediator.scoring import HeuristicScorer  # noqa: E402


ScenarioCheck = Callable[[dict[str, Any]], bool]


@dataclass(frozen=True)
class EvaluationScenario:
    name: str
    category: str
    target_title: str
    expected_movement: str
    before: ScoringRequest
    after: ScoringRequest
    check: ScenarioCheck


def main() -> None:
    report = build_report()
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    REPORT_MD.write_text(_markdown_report(report))
    print(json.dumps(report, indent=2, sort_keys=True))


def build_report() -> dict[str, Any]:
    results = [_run_scenario(scenario) for scenario in _scenarios()]
    attribution_results = [
        result for result in results if result["category"] == "attribution"
    ]
    recommendation_results = [
        result for result in results if result["category"] == "recommendation"
    ]
    attribution_passed = all(result["passed"] for result in attribution_results)
    recommendation_passed = sum(
        1 for result in recommendation_results if result["passed"]
    )

    return {
        "phase": "MVP+4: Recommendation Memory And Evaluation",
        "report_date": "2026-07-07",
        "command": "pnpm eval:mvp4",
        "scenario_count": len(results),
        "results": results,
        "summary": {
            "attribution_scenarios": len(attribution_results),
            "attribution_passed": attribution_passed,
            "recommendation_scenarios": len(recommendation_results),
            "recommendation_passed": recommendation_passed,
            "recommendation_pass_rate": round(
                recommendation_passed / len(recommendation_results),
                4,
            )
            if recommendation_results
            else 0,
            "known_gaps": [
                result["name"]
                for result in recommendation_results
                if not result["passed"]
            ],
            "mvp_plus_4_evaluation_harness_passed": (
                len(results) >= 10 and attribution_passed
            ),
        },
        "risk_notes": [
            "This is a deterministic local harness, not a live TMDb acceptance run.",
            "Recommendation scenarios use directional movement so useful tuning does not depend on exact ranks.",
            "Attribution scenarios are strict because profile ownership and repeat avoidance must not drift.",
            "Known recommendation gaps are reported without failing the command so later MVP+4 slices have a visible baseline.",
        ],
    }


def _run_scenario(scenario: EvaluationScenario) -> dict[str, Any]:
    before = _score(scenario.before)
    after = _score(scenario.after)
    target_before = _find_ranked(before, scenario.target_title)
    target_after = _find_ranked(after, scenario.target_title)
    target_candidate_before = _find_candidate(scenario.before, scenario.target_title)
    target_candidate_after = _find_candidate(scenario.after, scenario.target_title)
    result = {
        "name": scenario.name,
        "category": scenario.category,
        "target_title": scenario.target_title,
        "top_five_before": [candidate.title for candidate in before[:5]],
        "top_five_after": [candidate.title for candidate in after[:5]],
        "target_rank_before": target_before.candidate_rank
        if target_before is not None
        else None,
        "target_rank_after": target_after.candidate_rank
        if target_after is not None
        else None,
        "expected_movement": scenario.expected_movement,
        "actual_movement": _movement(target_before, target_after),
        "before_explanation": target_before.why_short
        if target_before is not None
        else None,
        "after_explanation": target_after.why_short
        if target_after is not None
        else None,
        "before_signal_families": _signal_families(target_before),
        "after_signal_families": _signal_families(target_after),
        "target_enrichment_provider_before": target_candidate_before.enrichment_provider
        if target_candidate_before is not None
        else None,
        "target_enrichment_provider_after": target_candidate_after.enrichment_provider
        if target_candidate_after is not None
        else None,
        "target_matched_person_names_after": list(
            target_candidate_after.matched_person_names
            if target_candidate_after is not None
            else (),
        ),
    }
    return {
        **result,
        "passed": scenario.check(result),
    }


def _score(request: ScoringRequest) -> tuple[RankedCandidate, ...]:
    return HeuristicScorer().score(request).ranked_candidates


def _find_ranked(
    ranked_candidates: tuple[RankedCandidate, ...],
    title: str,
) -> RankedCandidate | None:
    return next(
        (candidate for candidate in ranked_candidates if candidate.title == title),
        None,
    )


def _find_candidate(request: ScoringRequest, title: str) -> Candidate | None:
    return next(
        (candidate for candidate in request.candidates if candidate.title == title),
        None,
    )


def _movement(
    before: RankedCandidate | None,
    after: RankedCandidate | None,
) -> str:
    if before is None and after is None:
        return "absent"
    if before is None:
        return "appeared"
    if after is None:
        return "removed"
    if after.candidate_rank < before.candidate_rank:
        return "up"
    if after.candidate_rank > before.candidate_rank:
        return "down"
    return "same"


def _signal_families(candidate: RankedCandidate | None) -> list[str]:
    if candidate is None or not candidate.scoring_evidence:
        return []
    return list(candidate.scoring_evidence[0].signal_families)


def _scenarios() -> tuple[EvaluationScenario, ...]:
    return (
        EvaluationScenario(
            name="profile_attribution_pairing_uses_both_household_profiles",
            category="attribution",
            target_title="Arrival",
            expected_movement="same",
            before=_request(
                session_id="mvp4-profile-attribution-before",
                users=(_cezary_tester(), _wife_profile()),
            ),
            after=_request(
                session_id="mvp4-profile-attribution-after",
                users=(_cezary_tester(), _wife_profile()),
                viewer_user_ids=("cezary-tester", "profile-2"),
            ),
            check=lambda result: (
                "Cezary - tester" in (result["after_explanation"] or "")
                and "Wife" in (result["after_explanation"] or "")
            ),
        ),
        EvaluationScenario(
            name="active_profile_taste_lab_isolation",
            category="attribution",
            target_title="The Shining",
            expected_movement="up",
            before=_request(
                session_id="mvp4-active-isolation-before",
                users=(_wife_profile(),),
                audience_mode=AudienceMode.SOLO,
            ),
            after=_request(
                session_id="mvp4-active-isolation-after",
                users=(_horror_profile(),),
                audience_mode=AudienceMode.SOLO,
                viewer_user_ids=("cezary-tester",),
            ),
            check=lambda result: (
                result["actual_movement"] == "up"
                and "Taste Lab signals" in (result["after_explanation"] or "")
            ),
        ),
        EvaluationScenario(
            name="avoid_repeat_removes_already_watched_title",
            category="attribution",
            target_title="Arrival",
            expected_movement="removed",
            before=_request(
                session_id="mvp4-avoid-repeat-before",
                candidates=_candidate_pool(),
            ),
            after=_request(
                session_id="mvp4-avoid-repeat-after",
                candidates=_candidate_pool(already_watched=("tmdb:arrival",)),
            ),
            check=lambda result: result["actual_movement"] == "removed",
        ),
        EvaluationScenario(
            name="scary_steer_moves_horror_pick_up",
            category="recommendation",
            target_title="The Shining",
            expected_movement="up",
            before=_request(session_id="mvp4-scary-before"),
            after=_request(
                session_id="mvp4-scary-after",
                mood_text="scary psychological horror",
            ),
            check=lambda result: (
                result["actual_movement"] == "up"
                and "tonight_intent" in result["after_signal_families"]
            ),
        ),
        EvaluationScenario(
            name="sad_steer_moves_melancholy_drama_up",
            category="recommendation",
            target_title="Manchester by the Sea",
            expected_movement="up",
            before=_request(session_id="mvp4-sad-before"),
            after=_request(
                session_id="mvp4-sad-after",
                mood_text="sad emotional drama",
            ),
            check=lambda result: (
                result["actual_movement"] == "up"
                and "tonight_intent" in result["after_signal_families"]
            ),
        ),
        EvaluationScenario(
            name="named_actor_steer_surfaces_matching_cast",
            category="recommendation",
            target_title="Mission: Impossible - Fallout",
            expected_movement="up",
            before=_request(session_id="mvp4-actor-before"),
            after=_request(
                session_id="mvp4-actor-after",
                mood_text="something with Tom Cruise in it",
                person_constraints=(
                    PersonCandidateConstraint(
                        raw_name="Tom Cruise",
                        normalized_name="tom cruise",
                    ),
                ),
            ),
            check=lambda result: (
                result["actual_movement"] == "up"
                and "tonight_intent" in result["after_signal_families"]
            ),
        ),
        EvaluationScenario(
            name="comfort_movie_steer_moves_warm_comedy_up",
            category="recommendation",
            target_title="Paddington 2",
            expected_movement="up",
            before=_request(session_id="mvp4-comfort-before"),
            after=_request(
                session_id="mvp4-comfort-after",
                mood_text="comfort movie playful warm",
            ),
            check=lambda result: (
                result["actual_movement"] == "up"
                and "tonight_intent" in result["after_signal_families"]
            ),
        ),
        EvaluationScenario(
            name="post_watch_no_moves_similar_title_down",
            category="recommendation",
            target_title="Edge of Tomorrow Again",
            expected_movement="down",
            before=_request(
                session_id="mvp4-post-watch-no-before",
                users=(_action_profile(),),
                audience_mode=AudienceMode.SOLO,
            ),
            after=_request(
                session_id="mvp4-post-watch-no-after",
                users=(_action_profile_with_post_watch_no(),),
                audience_mode=AudienceMode.SOLO,
            ),
            check=lambda result: (
                result["actual_movement"] == "down"
                and "title_similarity" in result["after_signal_families"]
            ),
        ),
        EvaluationScenario(
            name="watchlist_loved_moves_saved_style_up",
            category="recommendation",
            target_title="Dinner Party Mystery",
            expected_movement="up",
            before=_request(
                session_id="mvp4-watchlist-loved-before",
                users=(_cezary_tester(),),
                audience_mode=AudienceMode.SOLO,
            ),
            after=_request(
                session_id="mvp4-watchlist-loved-after",
                users=(_watchlist_mystery_profile(),),
                audience_mode=AudienceMode.SOLO,
            ),
            check=lambda result: (
                result["actual_movement"] == "up"
                and (
                    "genre" in result["after_signal_families"]
                    or "feature_tag" in result["after_signal_families"]
                )
            ),
        ),
        EvaluationScenario(
            name="partner_compromise_prefers_shared_fit_over_one_sided_pick",
            category="recommendation",
            target_title="Dinner Party Mystery",
            expected_movement="shared fit stays first while one-sided action drops",
            before=_request(
                session_id="mvp4-compromise-before",
                users=(_action_and_mystery_profile(), _mystery_and_action_skeptic_profile()),
                session_mode=SessionMode.HUSBAND_FIRST,
            ),
            after=_request(
                session_id="mvp4-compromise-after",
                users=(_action_and_mystery_profile(), _mystery_and_action_skeptic_profile()),
                session_mode=SessionMode.COMPROMISE,
            ),
            check=lambda result: (
                result["target_rank_after"] == 1
                and "Mission: Impossible - Fallout" in result["top_five_before"]
                and "Mission: Impossible - Fallout" not in result["top_five_after"]
            ),
        ),
        EvaluationScenario(
            name="live_tmdb_candidate_shape_keeps_provider_evidence_visible",
            category="attribution",
            target_title="Arrival",
            expected_movement="same",
            before=_request(
                session_id="mvp4-live-shape-before",
                candidates=_candidate_pool(enrichment_provider="fixed-live-tmdb-eval"),
            ),
            after=_request(
                session_id="mvp4-live-shape-after",
                candidates=_candidate_pool(enrichment_provider="fixed-live-tmdb-eval"),
                mood_text="cerebral sci-fi",
            ),
            check=lambda result: (
                result["target_rank_after"] is not None
                and "tonight_intent" in result["after_signal_families"]
            ),
        ),
    )


def _request(
    *,
    session_id: str,
    users: tuple[UserProfile, ...] | None = None,
    candidates: tuple[Candidate, ...] | None = None,
    mood_text: str | None = None,
    audience_mode: AudienceMode = AudienceMode.SHARED,
    session_mode: SessionMode = SessionMode.COMPROMISE,
    viewer_user_ids: tuple[str, ...] = (),
    person_constraints: tuple[PersonCandidateConstraint, ...] = (),
    session_reactions: tuple[ScoringSessionReaction, ...] = (),
) -> ScoringRequest:
    return ScoringRequest(
        session=SessionContext(
            session_id=session_id,
            audience_mode=audience_mode,
            session_mode=session_mode,
            viewer_user_ids=viewer_user_ids,
            mood_text=mood_text,
            person_constraints=person_constraints,
        ),
        household_defaults=HouseholdDefaults(),
        users=users or (_cezary_tester(), _wife_profile()),
        candidates=candidates or _candidate_pool(),
        session_reactions=session_reactions,
    )


def _cezary_tester() -> UserProfile:
    return UserProfile(
        user_id="cezary-tester",
        role="founder",
        display_label="Cezary - tester",
        taste_profile_evidence=(
            _evidence("taste_lab", "tmdb:arrival-seed", "Arrival", ("Sci-Fi",), 1.0),
        ),
    )


def _wife_profile() -> UserProfile:
    return UserProfile(
        user_id="profile-2",
        role="partner",
        display_label="Wife",
        taste_profile_evidence=(
            _evidence("taste_lab", "tmdb:paddington-seed", "Paddington", ("Comedy",), 1.0),
        ),
    )


def _horror_profile() -> UserProfile:
    return UserProfile(
        user_id="cezary-tester",
        role="founder",
        display_label="Cezary - tester",
        taste_profile_evidence=(
            _evidence("taste_lab", "tmdb:shining-seed", "The Shining", ("Horror", "Thriller"), 1.0),
        ),
    )


def _action_profile() -> UserProfile:
    return UserProfile(
        user_id="profile-action",
        role="founder",
        display_label="Action profile",
        taste_profile_evidence=(
            _evidence("taste_lab", "tmdb:edge-original", "Edge of Tomorrow", ("Action", "Sci-Fi"), 1.0),
        ),
    )


def _action_profile_with_post_watch_no() -> UserProfile:
    return UserProfile(
        user_id="profile-action",
        role="founder",
        display_label="Action profile",
        taste_profile_evidence=(
            _evidence("taste_lab", "tmdb:edge-original", "Edge of Tomorrow", ("Action", "Sci-Fi"), 1.0),
            _evidence("app_memory", "tmdb:edge-original", "Edge of Tomorrow", (), -1.0),
        ),
    )


def _watchlist_mystery_profile() -> UserProfile:
    return UserProfile(
        user_id="profile-watchlist",
        role="founder",
        display_label="Watchlist rater",
        taste_profile_evidence=(
            _evidence("watchlist_rating", "tmdb:knives-out", "Knives Out", ("Mystery", "Comedy"), 1.0),
        ),
    )


def _action_and_mystery_profile() -> UserProfile:
    return UserProfile(
        user_id="profile-action-mystery",
        role="founder",
        display_label="Action and mystery",
        taste_profile_evidence=(
            _evidence("taste_lab", "tmdb:mission", "Mission: Impossible", ("Action",), 1.0),
            _evidence("taste_lab", "tmdb:knives-out", "Knives Out", ("Mystery", "Comedy"), 1.0),
        ),
    )


def _mystery_and_action_skeptic_profile() -> UserProfile:
    return UserProfile(
        user_id="profile-mystery-action-no",
        role="partner",
        display_label="Mystery fan",
        taste_profile_evidence=(
            _evidence("taste_lab", "tmdb:knives-out", "Knives Out", ("Mystery", "Comedy"), 1.0),
            _evidence("taste_lab", "tmdb:action-no", "Loud Action", ("Action", "Thriller"), -1.0),
        ),
    )


def _evidence(
    source: str,
    source_movie_id: str,
    title: str,
    genres: tuple[str, ...],
    preference_value: float,
) -> ProfileTasteEvidence:
    return ProfileTasteEvidence(
        source=source,
        source_movie_id=source_movie_id,
        title=title,
        genres=genres,
        preference_value=preference_value,
        source_label="loved" if preference_value > 0 else "no",
    )


def _candidate_pool(
    *,
    already_watched: tuple[str, ...] = (),
    enrichment_provider: str = "fixed-mvp-plus-4-eval",
) -> tuple[Candidate, ...]:
    watched_ids = set(already_watched)
    return (
        _candidate(
            "tmdb:arrival",
            "Arrival",
            ("Sci-Fi", "Drama"),
            {"cerebral": 0.95, "reflective": 0.7},
            already_watched="tmdb:arrival" in watched_ids,
            enrichment_provider=enrichment_provider,
        ),
        _candidate(
            "tmdb:dinner-party",
            "Dinner Party Mystery",
            ("Mystery", "Comedy"),
            {"whodunit": 0.92, "witty": 0.84},
            enrichment_provider=enrichment_provider,
        ),
        _candidate(
            "tmdb:shining",
            "The Shining",
            ("Horror", "Thriller"),
            {"scary": 0.97, "psychological": 0.94, "horror": 0.96},
            matched_person_names=("Jack Nicholson",),
            enrichment_provider=enrichment_provider,
        ),
        _candidate(
            "tmdb:manchester",
            "Manchester by the Sea",
            ("Drama",),
            {"sad": 0.98, "emotional": 0.91, "quiet": 0.72},
            enrichment_provider=enrichment_provider,
        ),
        _candidate(
            "tmdb:mission-fallout",
            "Mission: Impossible - Fallout",
            ("Action", "Thriller"),
            {"action": 0.96, "high-energy": 0.88},
            matched_person_names=("Tom Cruise",),
            enrichment_provider=enrichment_provider,
        ),
        _candidate(
            "tmdb:paddington-2",
            "Paddington 2",
            ("Comedy", "Adventure"),
            {"playful": 0.93, "warm": 0.94, "comfort": 0.95},
            enrichment_provider=enrichment_provider,
        ),
        _candidate(
            "tmdb:edge-again",
            "Edge of Tomorrow Again",
            ("Action", "Sci-Fi"),
            {"time-loop": 0.98, "action": 0.86},
            enrichment_provider=enrichment_provider,
        ),
        _candidate(
            "tmdb:past-lives",
            "Past Lives",
            ("Romance", "Drama"),
            {"romantic": 0.92, "bittersweet": 0.88, "reflective": 0.7},
            enrichment_provider=enrichment_provider,
        ),
    )


def _candidate(
    source_movie_id: str,
    title: str,
    genres: tuple[str, ...],
    feature_scores: dict[str, float],
    *,
    matched_person_names: tuple[str, ...] = (),
    already_watched: bool = False,
    enrichment_provider: str = "fixed-mvp-plus-4-eval",
) -> Candidate:
    return Candidate(
        source_movie_id=source_movie_id,
        title=title,
        media_type=MediaType.MOVIE,
        release_year=2020,
        runtime_min=112,
        genres=genres,
        providers=("Prime Video",),
        provider_availability=(
            ProviderAvailability(
                provider_name="Prime Video",
                access_type=ProviderAccessType.FLATRATE,
                region="DE",
            ),
        ),
        already_watched=already_watched,
        enrichment_status="enriched",
        enrichment_provider=enrichment_provider,
        enrichment_feature_scores=feature_scores,
        matched_person_names=matched_person_names,
    )


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# MVP Plus 4 Recommendation Evaluation",
        "",
        f"Date: {report['report_date']}",
        "",
        f"Phase: {report['phase']}",
        "",
        f"Command: `{report['command']}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in report["summary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Scenario Results", ""])
    for result in report["results"]:
        lines.extend(
            [
                f"### {result['name']}",
                "",
                f"- Category: {result['category']}",
                f"- Passed: {result['passed']}",
                f"- Target: {result['target_title']}",
                f"- Top five before: {', '.join(result['top_five_before'])}",
                f"- Top five after: {', '.join(result['top_five_after'])}",
                f"- Expected movement: {result['expected_movement']}",
                f"- Actual movement: {result['actual_movement']}",
                f"- Target rank before: {result['target_rank_before']}",
                f"- Target rank after: {result['target_rank_after']}",
                f"- Before signals: {', '.join(result['before_signal_families']) or 'none'}",
                f"- After signals: {', '.join(result['after_signal_families']) or 'none'}",
                f"- Target enrichment provider after: {result['target_enrichment_provider_after']}",
                f"- Target matched person names after: {', '.join(result['target_matched_person_names_after']) or 'none'}",
                f"- Before explanation: {result['before_explanation']}",
                f"- After explanation: {result['after_explanation']}",
                "",
            ]
        )
    lines.extend(["## Caveats", ""])
    for note in report["risk_notes"]:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
