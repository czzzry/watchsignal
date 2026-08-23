from __future__ import annotations

from dataclasses import dataclass
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from movie_night_mediator.app.personalized_recommendation import (
    MovieLensCatalogEntry,
    PersonalizedCandidateSource,
    PersonalizedCandidateRetriever,
    _semantic_rejection_penalties,
    build_default_personalized_retriever,
)
from movie_night_mediator.domain import (
    AudienceMode,
    Candidate,
    HouseholdDefaults,
    MediaType,
    ProfileTasteEvidence,
    ScoringSessionReaction,
    SessionContext,
    UserProfile,
)
from movie_night_mediator.scoring.learned_taste import MovieLensLinkMap
from movie_night_mediator.scoring.runtime_artifacts import runtime_artifact_paths


@dataclass(frozen=True)
class _ModelConfig:
    regularization: float = 1.0
    bias_regularization: float = 5.0


@dataclass(frozen=True)
class _Model:
    config: _ModelConfig
    global_mean: float
    item_ids: np.ndarray
    item_biases: np.ndarray
    item_factors: np.ndarray
    collaborative_support: np.ndarray | None = None
    family_factors: dict[str, np.ndarray] | None = None

    @property
    def item_index(self) -> dict[int, int]:
        return {int(movie_id): index for index, movie_id in enumerate(self.item_ids)}


class _Provider:
    model_name = "collaborative"

    def __init__(
        self,
        *,
        factors: np.ndarray | None = None,
        item_ids: np.ndarray | None = None,
        support: np.ndarray | None = None,
        family_factors: dict[str, np.ndarray] | None = None,
    ) -> None:
        self.model = _Model(
            config=_ModelConfig(),
            global_mean=3.0,
            item_ids=item_ids
            if item_ids is not None
            else np.asarray([1, 2, 3, 4], dtype=np.int32),
            item_biases=np.zeros(
                len(item_ids) if item_ids is not None else 4,
                dtype=np.float32,
            ),
            item_factors=factors
            if factors is not None
            else np.asarray(
                [[0.95, 0.0], [0.05, 0.0], [0.0, 0.95], [0.0, 0.05]],
                dtype=np.float32,
            ),
            collaborative_support=support,
            family_factors=family_factors,
        )


class _HydratingSource:
    def fetch_candidates_for_source_ids(self, *, source_movie_ids, **_kwargs):
        return tuple(
            Candidate(
                source_movie_id=source_id,
                title=f"Learned {source_id}",
                media_type=MediaType.MOVIE,
            )
            for source_id in source_movie_ids
        )


class _PartialHydratingSource(_HydratingSource):
    def fetch_candidates_for_source_ids(self, *, source_movie_ids, **_kwargs):
        return super().fetch_candidates_for_source_ids(
            source_movie_ids=source_movie_ids[:1]
        )

    def fetch_candidates(self, *, limit, **_kwargs):
        raise AssertionError("A personalized run must not ask for popularity exploration.")


class PersonalizedRecommendationEngineTest(unittest.TestCase):
    def test_vercel_function_explicitly_includes_runtime_model_bundle(self) -> None:
        api_root = Path(__file__).resolve().parents[1]
        config = json.loads((api_root / "vercel.json").read_text())

        self.assertEqual(
            config["functions"]["app.py"]["includeFiles"],
            "runtime/models/**",
        )

    def test_runtime_bundle_paths_are_relative_to_deployed_api_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            api_root = Path(directory) / "api"
            paths = runtime_artifact_paths(api_root=api_root)

        self.assertEqual(
            paths.hybrid_model,
            api_root / "runtime" / "models" / "hybrid-v1.zip",
        )
        self.assertEqual(
            paths.links,
            api_root / "runtime" / "models" / "movielens-tmdb-links-v1.json.gz",
        )

    def test_retrieval_is_profile_driven_and_merges_content_lane(self) -> None:
        provider = _Provider()
        content_provider = _Provider(
            item_ids=np.asarray([1, 3, 4, 5], dtype=np.int32),
            factors=np.asarray(
                [[0.1, 0.0], [0.95, 0.0], [0.05, 0.0], [0.9, 0.0]],
                dtype=np.float32,
            )
        )
        catalog = (
            MovieLensCatalogEntry(1, "tmdb:101", "Profile bridge", 1995, ("Crime",)),
            MovieLensCatalogEntry(2, "tmdb:102", "Popular decoy", 2024, ("Action",)),
            MovieLensCatalogEntry(3, "tmdb:103", "Content bridge", 2001, ("Drama",)),
            MovieLensCatalogEntry(4, "tmdb:104", "Weak decoy", 2024, ("Action",)),
            MovieLensCatalogEntry(5, "tmdb:105", "Content-only bridge", 2003, ("Drama",)),
        )
        user = UserProfile(
            user_id="cezary",
            role="user_a",
            display_label="Cezary",
            taste_profile_evidence=(
                ProfileTasteEvidence(
                    source="taste_lab",
                    source_movie_id="movielens:1",
                    title="Profile seed",
                    preference_value=1.0,
                ),
            ),
        )

        retriever = PersonalizedCandidateRetriever(
            collaborative_provider=provider,
            content_provider=content_provider,
            catalog=catalog,
            minimum_profile_matches=1,
        )

        result = retriever.retrieve(users=(user,), limit=3)

        self.assertEqual(result[0].source_movie_id, "tmdb:101")
        self.assertIn("collaborative", result[0].lane)
        self.assertTrue(any("content" in row.lane for row in result))
        self.assertGreater(result[0].retrieval_score, result[-1].retrieval_score)

    def test_exclusions_and_minimum_profile_evidence_are_hard_retrieval_guards(self) -> None:
        provider = _Provider()
        catalog = (
            MovieLensCatalogEntry(1, "tmdb:101", "Profile bridge", 1995, ("Crime",)),
            MovieLensCatalogEntry(2, "tmdb:102", "Popular decoy", 2024, ("Action",)),
        )
        user = UserProfile(
            user_id="cold",
            role="user_a",
            display_label="Cold",
        )
        retriever = PersonalizedCandidateRetriever(
            collaborative_provider=provider,
            content_provider=provider,
            catalog=catalog,
            minimum_profile_matches=2,
        )

        self.assertEqual(retriever.retrieve(users=(user,), limit=5), ())
        warm_user = UserProfile(
            user_id="warm",
            role="user_a",
            display_label="Warm",
            taste_profile_evidence=(
                ProfileTasteEvidence(
                    source="taste_lab",
                    source_movie_id="movielens:1",
                    title="Profile seed",
                    preference_value=1.0,
                ),
                ProfileTasteEvidence(
                    source="taste_lab",
                    source_movie_id="movielens:2",
                    title="Second seed",
                    preference_value=0.65,
                ),
            ),
        )
        rows = retriever.retrieve(
            users=(warm_user,),
            limit=5,
            excluded_source_movie_ids=("tmdb:101",),
        )
        self.assertNotIn("tmdb:101", {row.source_movie_id for row in rows})
        self.assertTrue(rows)

    def test_curator_inspiration_uses_verified_anchor_neighbours_not_support_popularity(
        self,
    ) -> None:
        provider = _Provider(
            item_ids=np.asarray([1, 2, 3, 4, 5], dtype=np.int32),
            factors=np.asarray(
                [
                    [1.0, 0.0],
                    [0.999, 0.0],
                    [0.92, 0.0],
                    [0.9, 0.1],
                    [0.98, 0.0],
                ],
                dtype=np.float32,
            ),
            support=np.asarray([20, 10_000, 25, 20, 1], dtype=np.int32),
        )
        retriever = PersonalizedCandidateRetriever(
            collaborative_provider=provider,
            catalog=(
                MovieLensCatalogEntry(1, "tmdb:101", "Verified anchor", genres=("Crime",)),
                MovieLensCatalogEntry(2, "tmdb:102", "Highly supported decoy", genres=("Comedy",)),
                MovieLensCatalogEntry(3, "tmdb:103", "Supported neighbour", genres=("Crime", "Drama")),
                MovieLensCatalogEntry(4, "tmdb:104", "Second verified anchor", genres=("Drama",)),
                MovieLensCatalogEntry(5, "tmdb:105", "Obscure tail", genres=("Crime", "Drama")),
            ),
            minimum_item_support=0,
        )

        result = retriever.retrieve_curator_inspiration(
            anchor_source_movie_ids=("movielens:1", "tmdb:104", "tmdb:unmapped"),
            limit=2,
        )

        self.assertEqual(
            result.mapped_anchor_source_movie_ids,
            ("tmdb:101", "tmdb:104"),
        )
        self.assertTrue(result.ran)
        self.assertNotIn("tmdb:101", {row.source_movie_id for row in result.candidates})
        self.assertEqual(result.candidates[0].source_movie_id, "tmdb:103")
        self.assertNotIn("tmdb:102", {row.source_movie_id for row in result.candidates})
        self.assertNotIn("tmdb:105", {row.source_movie_id for row in result.candidates})
        self.assertIn("support_balanced", result.candidates[0].reasons)

    def test_curator_inspiration_fuses_hybrid_content_over_a_collaborative_only_decoy(
        self,
    ) -> None:
        item_ids = np.asarray([1, 2, 3, 4], dtype=np.int32)
        collaborative = _Provider(
            item_ids=item_ids,
            factors=np.asarray(
                [[1.0, 0.0], [0.9, 0.1], [0.99, 0.0], [0.8, 0.2]],
                dtype=np.float32,
            ),
        )
        content = _Provider(
            item_ids=item_ids,
            factors=np.asarray(
                [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [1.0, 0.0]],
                dtype=np.float32,
            ),
            support=np.asarray([20, 20, 20, 20], dtype=np.int32),
            family_factors={
                "tag": np.asarray(
                    [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [1.0, 0.0]],
                    dtype=np.float32,
                ),
                "genre": np.asarray(
                    [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0], [1.0, 0.0]],
                    dtype=np.float32,
                ),
            },
        )
        retriever = PersonalizedCandidateRetriever(
            collaborative_provider=collaborative,
            content_provider=content,
            catalog=(
                MovieLensCatalogEntry(1, "tmdb:101", "Anchor one", genres=("Crime",)),
                MovieLensCatalogEntry(2, "tmdb:102", "Anchor two", genres=("Drama",)),
                MovieLensCatalogEntry(3, "tmdb:103", "Collaborative decoy", genres=("Crime", "Drama")),
                MovieLensCatalogEntry(4, "tmdb:104", "Content bridge", genres=("Crime", "Drama")),
            ),
            minimum_item_support=0,
        )

        result = retriever.retrieve_curator_inspiration(
            anchor_source_movie_ids=("tmdb:101", "tmdb:102"),
            limit=2,
        )

        self.assertTrue(result.ran)
        self.assertEqual(result.candidates[0].source_movie_id, "tmdb:104")
        self.assertEqual(result.candidates[0].lane, "curator_hybrid_fusion")
        self.assertIn("content_fusion:tag+genre", result.candidates[0].reasons)

    def test_verified_runtime_artifacts_produce_a_credible_multi_anchor_curator_pool(
        self,
    ) -> None:
        retriever = build_default_personalized_retriever()
        self.assertIsNotNone(retriever)
        assert retriever is not None

        result = retriever.retrieve_curator_inspiration(
            anchor_source_movie_ids=(
                "tmdb:539",  # Psycho
                "tmdb:1578",  # Raging Bull
                "tmdb:1949",  # Zodiac
                "tmdb:36095",  # Cure
            ),
            limit=15,
        )
        titles = tuple(
            retriever._catalog[row.movie_id].title for row in result.candidates
        )

        self.assertEqual(len(result.candidates), 15)
        self.assertTrue(
            all(row.lane == "curator_hybrid_fusion" for row in result.candidates)
        )
        self.assertIn("Dog Day Afternoon (1975)", titles)
        self.assertIn("Taxi Driver (1976)", titles)
        self.assertIn("Nightcrawler (2014)", titles)
        self.assertFalse(
            {
                "Lez Bomb (2018)",
                "Chuck Berry Hail! Hail! Rock 'n' Roll (1987)",
                "Mobile Suit Gundam F91 (1991)",
            }
            & set(titles)
        )

    def test_source_adapter_hydrates_learned_ids(self) -> None:
        provider = _Provider()
        retriever = PersonalizedCandidateRetriever(
            collaborative_provider=provider,
            catalog=(
                MovieLensCatalogEntry(1, "tmdb:101", "Profile bridge"),
                MovieLensCatalogEntry(2, "tmdb:102", "Second bridge"),
            ),
            minimum_profile_matches=1,
        )
        source = PersonalizedCandidateSource(
            base_source=_HydratingSource(),
            retriever=retriever,
        )
        user = UserProfile(
            user_id="warm",
            role="user_a",
            display_label="Warm",
            taste_profile_evidence=(
                ProfileTasteEvidence(
                    source="taste_lab",
                    source_movie_id="movielens:1",
                    title="Profile seed",
                    preference_value=1.0,
                ),
            ),
        )

        candidates = source.fetch_personalized_candidates(
            session=SessionContext(
                session_id="source",
                audience_mode=AudienceMode.SOLO,
            ),
            household_defaults=HouseholdDefaults(),
            users=(user,),
            limit=2,
        )

        self.assertTrue(candidates)
        self.assertTrue(candidates[0].source_movie_id.startswith("tmdb:10"))

    def test_personalized_source_does_not_silently_fill_from_popularity(self) -> None:
        provider = _Provider()
        retriever = PersonalizedCandidateRetriever(
            collaborative_provider=provider,
            catalog=(
                MovieLensCatalogEntry(1, "tmdb:101", "Profile bridge"),
                MovieLensCatalogEntry(2, "tmdb:102", "Second bridge"),
            ),
            minimum_profile_matches=1,
        )
        source = PersonalizedCandidateSource(
            base_source=_PartialHydratingSource(),
            retriever=retriever,
        )
        user = UserProfile(
            user_id="warm",
            role="user_a",
            display_label="Warm",
            taste_profile_evidence=(
                ProfileTasteEvidence(
                    source="taste_lab",
                    source_movie_id="movielens:1",
                    title="Profile seed",
                    preference_value=1.0,
                ),
            ),
        )

        candidates = source.fetch_personalized_candidates(
            session=SessionContext(session_id="strict-source"),
            household_defaults=HouseholdDefaults(),
            users=(user,),
            limit=2,
        )

        self.assertEqual(len(candidates), 1)
        self.assertNotIn("Exploration", candidates[0].title)

    def test_multiple_no_reactions_penalize_the_same_latent_lane(self) -> None:
        provider = _Provider(
            factors=np.asarray(
                [[1.0, 0.0], [0.9, 0.0], [0.8, 0.0], [0.0, 1.0]],
                dtype=np.float32,
            )
        )
        provider.links = MovieLensLinkMap({"101": 1, "102": 2})

        penalties = _semantic_rejection_penalties(
            provider=provider,
            candidate_movie_ids=np.asarray([3, 4], dtype=np.int32),
            session_reactions=(
                ScoringSessionReaction("tmdb:101", "no", "First rejected"),
                ScoringSessionReaction("tmdb:102", "no", "Second rejected"),
            ),
        )

        self.assertGreater(penalties.get(3, 0.0), 0.2)
        self.assertNotIn(4, penalties)


if __name__ == "__main__":
    unittest.main()
