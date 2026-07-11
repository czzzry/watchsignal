from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from movie_night_mediator.domain import (
    AudienceMode,
    Candidate,
    HouseholdDefaults,
    MediaType,
    ProfileTasteEvidence,
    ScoringRequest,
    SessionContext,
    SessionMode,
    UserProfile,
)
from movie_night_mediator.scoring import (
    HeuristicScorer,
    ScoringEngineId,
    V2ContractScorer,
    build_recommendation_scorer,
)
from movie_night_mediator.scoring.engine import _load_learned_taste_provider
from movie_night_mediator.scoring.learned_taste import (
    COLLABORATIVE_ARTIFACT_SHA256,
    CollaborativeTasteProvider,
    HybridTasteProvider,
    LearnedTasteBatch,
    MovieLensLinkMap,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


class LearnedTasteIntegrationTest(unittest.TestCase):
    def tearDown(self) -> None:
        _load_learned_taste_provider.cache_clear()

    def test_learned_scores_feed_existing_compromise_logic(self) -> None:
        request = _shared_request()
        scorer = V2ContractScorer(
            learned_taste_provider=_FixedTasteProvider(
                scores={
                    ("alex", "tmdb:20"): 0.94,
                    ("sam", "tmdb:20"): 0.35,
                    ("alex", "tmdb:30"): 0.66,
                    ("sam", "tmdb:30"): 0.64,
                }
            ),
            scorer_version=ScoringEngineId.V2_HYBRID.value,
        )

        result = scorer.score(request)

        self.assertEqual(result.scorer_version, "v2_hybrid")
        self.assertEqual(result.ranked_candidates[0].title, "Shared Bridge")
        self.assertEqual(result.ranked_candidates[0].fit_bucket, "compromise")
        self.assertAlmostEqual(result.ranked_candidates[0].user_a_score or 0, 0.66)
        self.assertAlmostEqual(result.ranked_candidates[0].user_b_score or 0, 0.64)
        self.assertIn(
            "learned_taste:hybrid:alex:3_profile_items",
            result.ranked_candidates[0].dominant_positive_evidence,
        )
        self.assertIn(
            "V2 household and tonight logic remain applied",
            result.ranked_candidates[0].why_short,
        )

    def test_session_mode_still_controls_household_reconciliation(self) -> None:
        provider = _FixedTasteProvider(
            scores={
                ("alex", "tmdb:20"): 0.94,
                ("sam", "tmdb:20"): 0.35,
                ("alex", "tmdb:30"): 0.66,
                ("sam", "tmdb:30"): 0.64,
            }
        )
        compromise = V2ContractScorer(learned_taste_provider=provider).score(
            _shared_request(SessionMode.COMPROMISE)
        )
        husband_first = V2ContractScorer(learned_taste_provider=provider).score(
            _shared_request(SessionMode.HUSBAND_FIRST)
        )

        self.assertEqual(compromise.ranked_candidates[0].title, "Shared Bridge")
        self.assertEqual(husband_first.ranked_candidates[0].title, "Alex Favorite")
        self.assertIn(
            "shared:husband_first_win",
            husband_first.ranked_candidates[0].dominant_positive_evidence,
        )

    def test_cold_start_falls_back_to_unchanged_v2_result(self) -> None:
        request = _shared_request()
        plain_v2 = V2ContractScorer().score(request)
        learned = V2ContractScorer(
            learned_taste_provider=_FixedTasteProvider(scores={}),
            scorer_version=ScoringEngineId.V2_HYBRID.value,
        ).score(request)

        self.assertEqual(
            [row.source_movie_id for row in learned.ranked_candidates],
            [row.source_movie_id for row in plain_v2.ranked_candidates],
        )
        self.assertEqual(learned.scorer_version, "v2_hybrid")
        self.assertEqual(
            learned.fallback_reason,
            "no_mapped_profile_and_candidate_evidence",
        )
        self.assertTrue(learned.is_uncertain)

    def test_missing_artifact_uses_deterministic_v2_rollback(self) -> None:
        request = _shared_request()
        plain_v2 = V2ContractScorer().score(request)
        with patch.dict(
            os.environ,
            {"MOVIE_NIGHT_HYBRID_MODEL_PATH": "/missing/hybrid.zip"},
            clear=False,
        ):
            scorer = build_recommendation_scorer(ScoringEngineId.V2_HYBRID)
            learned = scorer.score(request)

        self.assertEqual(
            [row.source_movie_id for row in learned.ranked_candidates],
            [row.source_movie_id for row in plain_v2.ranked_candidates],
        )
        self.assertIn("Could not load learned taste artifact", learned.fallback_reason or "")
        self.assertTrue(learned.is_uncertain)

    def test_v1_and_v2_remain_explicit_rollback_paths(self) -> None:
        self.assertIsInstance(
            build_recommendation_scorer(ScoringEngineId.V1_HEURISTIC),
            HeuristicScorer,
        )
        self.assertIsInstance(
            build_recommendation_scorer(ScoringEngineId.V2_CONTRACT),
            V2ContractScorer,
        )

    def test_collaborative_runtime_checksum_matches_sealed_offline_champion(self) -> None:
        report = json.loads(
            (
                REPO_ROOT
                / "docs/validation/movielens-replacement-sealed-benchmark.json"
            ).read_text()
        )

        self.assertEqual(
            report["decision"]["offline_quality_champion"],
            "collaborative_challenger",
        )
        self.assertEqual(
            COLLABORATIVE_ARTIFACT_SHA256,
            report["frozen_inputs"]["artifact_sha256"][
                "collaborative_challenger"
            ],
        )

    def test_collaborative_provider_uses_tmdb_mapping_and_profile_evidence(self) -> None:
        provider = CollaborativeTasteProvider(_fixture_model(), _fixture_links())

        batch = provider.score(_solo_model_request())

        self.assertEqual(batch.profile_match_counts, {"solo": 1})
        self.assertGreater(
            batch.scores[("solo", "tmdb:20")],
            batch.scores[("solo", "tmdb:30")],
        )
        self.assertNotIn(("solo", "fixture:unmapped"), batch.scores)

    def test_provider_accepts_direct_movielens_profile_evidence(self) -> None:
        request = _solo_model_request(profile_source_movie_id="movielens:1")
        provider = HybridTasteProvider(_fixture_model(), _fixture_links())

        batch = provider.score(request)

        self.assertEqual(batch.profile_match_counts, {"solo": 1})
        self.assertGreater(
            batch.scores[("solo", "tmdb:20")],
            batch.scores[("solo", "tmdb:30")],
        )

    def test_hybrid_provider_uses_same_runtime_contract(self) -> None:
        provider = HybridTasteProvider(_fixture_model(), _fixture_links())

        batch = provider.score(_solo_model_request())

        self.assertEqual(batch.model_name, "hybrid")
        self.assertEqual(batch.profile_match_counts, {"solo": 1})
        self.assertGreater(
            batch.scores[("solo", "tmdb:20")],
            batch.scores[("solo", "tmdb:30")],
        )


@dataclass(frozen=True)
class _FixedTasteProvider:
    scores: dict[tuple[str, str], float]
    model_name: str = "hybrid"

    def score(self, request: ScoringRequest) -> LearnedTasteBatch:
        return LearnedTasteBatch(
            model_name=self.model_name,
            scores=self.scores,
            profile_match_counts={user.user_id: 3 for user in request.users},
        )


@dataclass(frozen=True)
class _FixtureModel:
    global_mean: float
    item_ids: np.ndarray
    item_biases: np.ndarray
    item_factors: np.ndarray
    config: SimpleNamespace

    @cached_property
    def item_index(self) -> dict[int, int]:
        return {int(movie_id): index for index, movie_id in enumerate(self.item_ids)}


def _fixture_model() -> _FixtureModel:
    return _FixtureModel(
        global_mean=3.0,
        item_ids=np.asarray([1, 2, 3], dtype=np.int32),
        item_biases=np.zeros(3, dtype=np.float32),
        item_factors=np.asarray([[-1.0], [1.0], [-1.0]], dtype=np.float32),
        config=SimpleNamespace(regularization=1.0, bias_regularization=5.0),
    )


def _fixture_links() -> MovieLensLinkMap:
    return MovieLensLinkMap({"10": 1, "20": 2, "30": 3})


def _shared_request(
    session_mode: SessionMode = SessionMode.COMPROMISE,
) -> ScoringRequest:
    return ScoringRequest(
        session=SessionContext(
            session_id=f"learned-{session_mode.value}",
            audience_mode=AudienceMode.SHARED,
            session_mode=session_mode,
        ),
        household_defaults=HouseholdDefaults(),
        users=(
            UserProfile(user_id="alex", role="husband", display_label="Alex"),
            UserProfile(user_id="sam", role="wife", display_label="Sam"),
        ),
        candidates=(
            Candidate(
                source_movie_id="tmdb:20",
                title="Alex Favorite",
                media_type=MediaType.MOVIE,
                providers=("Prime Video",),
            ),
            Candidate(
                source_movie_id="tmdb:30",
                title="Shared Bridge",
                media_type=MediaType.MOVIE,
                providers=("Prime Video",),
            ),
        ),
    )


def _solo_model_request(
    profile_source_movie_id: str = "tmdb:10",
) -> ScoringRequest:
    return ScoringRequest(
        session=SessionContext(session_id="learned-solo"),
        household_defaults=HouseholdDefaults(),
        users=(
            UserProfile(
                user_id="solo",
                role="solo",
                display_label="Solo",
                taste_profile_evidence=(
                    ProfileTasteEvidence(
                        source="taste_lab",
                        source_movie_id=profile_source_movie_id,
                        title="Known Dislike",
                        preference_value=-1.0,
                    ),
                ),
            ),
        ),
        candidates=(
            Candidate("tmdb:20", "Opposite Factor", MediaType.MOVIE),
            Candidate("tmdb:30", "Same Factor", MediaType.MOVIE),
            Candidate("fixture:unmapped", "Unmapped", MediaType.MOVIE),
        ),
    )


if __name__ == "__main__":
    unittest.main()
