from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException
from fastapi.routing import APIRoute

from movie_night_mediator.adapters import (
    TmdbCandidateSource,
    TmdbCandidateSourceConfig,
)
from movie_night_mediator.api.main import (
    RecommendationShortlistRequestPayload,
    RecommendationShortlistItemPayload,
    _live_candidate_fetch_limit,
    create_app,
)
from movie_night_mediator.app.backfill import ManualBackfillService
from movie_night_mediator.app.taste_memory import TasteMemoryService
from movie_night_mediator.app.shortlist import get_offline_demo_shortlist
from movie_night_mediator.domain import (
    BackfillTasteLabel,
    Candidate,
    HouseholdDefaults,
    MediaType,
    ProviderAccessType,
    ProviderAvailability,
    SessionContext,
    TitleResolutionCandidate,
    TitleResolutionEntry,
)
from movie_night_mediator.storage import SQLiteBackfillStore
from movie_night_mediator.storage import SQLiteRecommendationSnapshotStore
from movie_night_mediator.storage import SQLiteTasteLabStore
from movie_night_mediator.storage import SQLiteTasteMemoryStore
from movie_night_mediator.taste_lab import (
    TasteLabMovieIdentity,
    TasteLabRatingExport,
    TasteLabRatingLabel,
)


class ShortlistApiTest(unittest.TestCase):
    def test_live_candidate_fetch_limit_scales_with_exclusions_without_exploding(
        self,
    ) -> None:
        self.assertEqual(
            _live_candidate_fetch_limit(
                shortlist_size=5,
                excluded_count=0,
                watched_count=0,
            ),
            10,
        )
        self.assertEqual(
            _live_candidate_fetch_limit(
                shortlist_size=5,
                excluded_count=20,
                watched_count=0,
            ),
            30,
        )

    def test_offline_demo_shortlist_is_stable_and_web_shaped(self) -> None:
        shortlist = get_offline_demo_shortlist()

        self.assertEqual(len(shortlist), 5)
        self.assertEqual(
            tuple(item.source_movie_id for item in shortlist),
            (
                "arrival",
                "knives-out",
                "the-grand-budapest-hotel",
                "fixture:rent-only-thriller",
                "edge-of-tomorrow",
            ),
        )
        self.assertEqual(
            tuple(item.candidate_rank for item in shortlist),
            (1, 2, 3, 4, 5),
        )
        self.assertEqual(shortlist[3].provider_names, ("Amazon Video",))
        self.assertEqual(shortlist[0].media_type, "movie")
        self.assertEqual(shortlist[0].year, 2016)
        self.assertEqual(shortlist[0].release_year, 2016)
        self.assertEqual(shortlist[0].runtime, "1h 56m")
        self.assertEqual(shortlist[0].runtime_min, 116)
        self.assertIn("Sci-Fi", shortlist[0].genres)
        self.assertEqual(shortlist[0].safe_pick_status, "Safe Pick")
        self.assertEqual(shortlist[0].availability, "Prime Video DE flatrate")
        self.assertEqual(shortlist[0].language_access, "English audio")
        self.assertTrue(shortlist[0].poster_url)
        self.assertGreater(shortlist[0].founder_score or 0, 0)
        self.assertGreater(shortlist[0].wife_score or 0, 0)
        self.assertEqual(shortlist[0].original_language, "en")
        self.assertEqual(shortlist[0].spoken_languages, ("en",))
        self.assertFalse(shortlist[0].english_subtitles_verified)
        self.assertTrue(shortlist[0].is_interesting_pick)

    def test_recommendation_shortlist_route_returns_fixture_payload(self) -> None:
        get_shortlist = recommendation_shortlist_endpoint(create_app())

        payload = get_shortlist()

        self.assertEqual(len(payload), 5)
        self.assertTrue(
            all(isinstance(item, RecommendationShortlistItemPayload) for item in payload)
        )
        self.assertEqual(
            [item.sourceMovieId for item in payload],
            [
                "arrival",
                "knives-out",
                "the-grand-budapest-hotel",
                "fixture:rent-only-thriller",
                "edge-of-tomorrow",
            ],
        )
        self.assertEqual([item.candidateRank for item in payload], [1, 2, 3, 4, 5])
        self.assertEqual(payload[0].mediaType, "movie")
        self.assertEqual(payload[0].year, 2016)
        self.assertEqual(payload[0].providerNames, ["Prime Video"])
        self.assertEqual(
            payload[0].providerAvailability[0].model_dump(mode="json"),
            {
                "providerName": "Prime Video",
                "accessType": "flatrate",
                "region": "DE",
            },
        )
        self.assertTrue(payload[0].posterUrl)
        self.assertEqual(payload[0].safePickStatus, "Safe Pick")
        self.assertEqual(payload[0].availability, "Prime Video DE flatrate")
        self.assertEqual(payload[0].languageAccess, "English audio")
        self.assertTrue(payload[0].tone)
        self.assertTrue(payload[0].reason)
        self.assertEqual(payload[0].runtime, "1h 56m")
        self.assertEqual(payload[0].releaseYear, 2016)
        self.assertEqual(payload[0].runtimeMin, 116)
        self.assertEqual(payload[0].fitBucket, "compromise")
        self.assertGreater(payload[0].founderScore or 0, 0)
        self.assertGreater(payload[0].wifeScore or 0, 0)
        self.assertGreater(payload[0].groupScore, 0)
        self.assertTrue(payload[0].whyShort)
        self.assertEqual(payload[0].originalLanguage, "en")
        self.assertEqual(payload[0].spokenLanguages, ["en"])
        self.assertFalse(payload[0].englishSubtitlesVerified)

    def test_recommendation_shortlist_route_includes_stable_language_and_score_fields(
        self,
    ) -> None:
        get_shortlist = recommendation_shortlist_endpoint(create_app())

        payload = get_shortlist()
        final_candidate = next(
            item
            for item in payload
            if item.sourceMovieId == "fixture:rent-only-thriller"
        )

        self.assertEqual(final_candidate.safePickStatus, "Safe Pick")
        self.assertEqual(
            final_candidate.languageAccess,
            "English audio",
        )
        self.assertEqual(final_candidate.originalLanguage, "en")
        self.assertEqual(final_candidate.spokenLanguages, ["en"])
        self.assertFalse(final_candidate.englishSubtitlesVerified)
        self.assertEqual(final_candidate.providerNames, ["Amazon Video"])
        self.assertEqual(final_candidate.availability, "Amazon Video DE rent")
        self.assertGreater(final_candidate.founderScore or 0, 0)
        self.assertGreater(final_candidate.wifeScore or 0, 0)

    def test_openapi_contract_includes_recommendation_shortlist_route(self) -> None:
        schema = create_app().openapi()

        self.assertIn("/recommendations/shortlist", schema["paths"])
        self.assertIn("post", schema["paths"]["/recommendations/shortlist"])
        self.assertIn(
            "RecommendationShortlistItemPayload",
            schema["components"]["schemas"],
        )
        self.assertIn(
            "RecommendationProviderAvailabilityPayload",
            schema["components"]["schemas"],
        )

    def test_post_recommendation_shortlist_saves_snapshot_for_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot_store = SQLiteRecommendationSnapshotStore(
                database_path=Path(directory) / "shortlist-snapshot.sqlite3"
            )
            post_shortlist = recommendation_shortlist_endpoint(
                create_app(recommendation_snapshot_store=snapshot_store),
                method="POST",
            )

            payload = post_shortlist(
                RecommendationShortlistRequestPayload(sessionId="tonight-session")
            )

            snapshot = snapshot_store.load_snapshot("tonight-session")

            self.assertEqual(len(payload), 5)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertEqual(snapshot.session_id, "tonight-session")
            self.assertEqual(snapshot.scorer_version, "v2_contract")
            self.assertEqual(
                snapshot.candidates[0].source_movie_id,
                payload[0].sourceMovieId,
            )
            self.assertEqual(snapshot.enrichment_coverage, (13, 5, 8, 0.3846))
            self.assertEqual(
                snapshot.candidate_inputs[0].enrichment_status,
                "enriched",
            )
            self.assertEqual(
                snapshot.candidate_inputs[0].matched_enrichment_source_movie_id,
                "movielens:122882",
            )
            self.assertGreater(
                snapshot.candidate_inputs[0].enrichment_feature_scores["cerebral"],
                0.9,
            )
            self.assertIsNone(
                snapshot_store.load_snapshot("demo-shared-session"),
            )

    def test_post_recommendation_shortlist_can_opt_into_v1_rollback_scorer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot_store = SQLiteRecommendationSnapshotStore(
                database_path=Path(directory) / "v1-shortlist-snapshot.sqlite3"
            )
            post_shortlist = recommendation_shortlist_endpoint(
                create_app(recommendation_snapshot_store=snapshot_store),
                method="POST",
            )

            payload = post_shortlist(
                RecommendationShortlistRequestPayload(
                    sessionId="tonight-session-v2",
                    scoringEngine="v1_heuristic",
                )
            )

            snapshot = snapshot_store.load_snapshot("tonight-session-v2")

            self.assertEqual(len(payload), 5)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertEqual(snapshot.scorer_version, "v1_heuristic")
            self.assertIsNone(snapshot.confidence_score)
            self.assertIsNone(
                snapshot_store.load_snapshot("demo-shared-session"),
            )

    def test_post_recommendation_shortlist_excludes_already_shown_ids(self) -> None:
        post_shortlist = recommendation_shortlist_endpoint(create_app(), method="POST")

        payload = post_shortlist(
            RecommendationShortlistRequestPayload(
                sessionId="continuation-session",
                excludedSourceMovieIds=[
                    "arrival",
                    "knives-out",
                    "the-grand-budapest-hotel",
                    "edge-of-tomorrow",
                    "past-lives",
                ],
            )
        )

        self.assertEqual(len(payload), 5)
        self.assertTrue(
            {
                "arrival",
                "knives-out",
                "the-grand-budapest-hotel",
                "edge-of-tomorrow",
                "past-lives",
            }.isdisjoint({item.sourceMovieId for item in payload})
        )

    def test_post_recommendation_shortlist_can_use_live_candidate_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot_store = SQLiteRecommendationSnapshotStore(
                database_path=Path(directory) / "live-shortlist-snapshot.sqlite3"
            )
            post_shortlist = recommendation_shortlist_endpoint(
                create_app(
                    recommendation_snapshot_store=snapshot_store,
                    backfill_store=SQLiteBackfillStore(
                        database_path=Path(directory) / "backfill.sqlite3"
                    ),
                    candidate_source=FakeCandidateSource(),
                ),
                method="POST",
            )

            payload = post_shortlist(
                RecommendationShortlistRequestPayload(
                    sessionId="live-session",
                    source="live_tmdb",
                )
            )

            snapshot = snapshot_store.load_snapshot("live-session")

            self.assertEqual(len(payload), 5)
            self.assertEqual(
                [item.sourceMovieId for item in payload],
                [f"tmdb:{index}" for index in range(1, 6)],
            )
            self.assertEqual(payload[0].providerNames, ["Amazon Prime Video"])
            self.assertEqual(payload[0].posterUrl, "https://example.test/poster-1.jpg")
            self.assertEqual(payload[0].safePickStatus, "Safe Pick")
            self.assertEqual(payload[0].availability, "Amazon Prime Video DE flatrate")
            self.assertTrue(payload[0].whyShort)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertEqual(snapshot.session_id, "live-session")
            self.assertEqual(len(snapshot.candidate_inputs), 5)
            self.assertEqual(snapshot.candidate_inputs[0].source_movie_id, "tmdb:1")
            self.assertEqual(snapshot.enrichment_coverage, (5, 0, 5, 0.0))
            self.assertEqual(
                snapshot.candidate_inputs[0].enrichment_provider,
                "tmdb-metadata-fallback",
            )

    def test_post_recommendation_shortlist_can_continue_past_first_tmdb_page(
        self,
    ) -> None:
        post_shortlist = recommendation_shortlist_endpoint(
            create_app(
                candidate_source=TmdbCandidateSource(
                    client=FakePagedTmdbClient(movie_ids=tuple(range(1, 26))),
                    config=TmdbCandidateSourceConfig(api_key="test"),
                ),
            ),
            method="POST",
        )

        payload = post_shortlist(
            RecommendationShortlistRequestPayload(
                sessionId="live-continuation-session",
                source="live_tmdb",
                excludedSourceMovieIds=[f"tmdb:{index}" for index in range(1, 21)],
            )
        )

        self.assertEqual(len(payload), 5)
        self.assertEqual(
            [item.sourceMovieId for item in payload],
            [f"tmdb:{index}" for index in range(21, 26)],
        )

    def test_post_recommendation_shortlist_uses_availability_settings(self) -> None:
        candidate_source = RecordingSixCandidateSource()
        post_shortlist = recommendation_shortlist_endpoint(
            create_app(candidate_source=candidate_source),
            method="POST",
        )

        post_shortlist(
            RecommendationShortlistRequestPayload(
                sessionId="availability-session",
                source="live_tmdb",
                availabilityRegion="Any streaming Germany",
                serviceConstraint=None,
            )
        )

        self.assertEqual(candidate_source.sessions[0].region, "DE")
        self.assertIsNone(candidate_source.sessions[0].service_constraint)

        post_shortlist(
            RecommendationShortlistRequestPayload(
                sessionId="prime-session",
                source="live_tmdb",
                availabilityRegion="Prime Video Germany",
                serviceConstraint="Prime Video",
            )
        )

        self.assertEqual(candidate_source.sessions[1].region, "DE")
        self.assertEqual(candidate_source.sessions[1].service_constraint, "Prime Video")

    def test_post_recommendation_shortlist_combines_additive_tonight_intents(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate_source = RecordingCandidateSource()
            post_shortlist = recommendation_shortlist_endpoint(
                create_app(
                    backfill_store=SQLiteBackfillStore(
                        database_path=Path(directory) / "backfill.sqlite3"
                    ),
                    candidate_source=candidate_source,
                ),
                method="POST",
            )

            payload = post_shortlist(
                RecommendationShortlistRequestPayload(
                    sessionId="steered-session",
                    source="live_tmdb",
                    tonightIntents=[
                        {"rawText": "something funny from the 90s"},
                        {"rawText": "actually more action"},
                    ],
                )
            )

            self.assertEqual(len(payload), 5)
            self.assertEqual(
                candidate_source.mood_texts,
                ("something funny from the 90s + actually more action",),
            )
            self.assertEqual(
                tuple(intent.raw_text for intent in candidate_source.sessions[0].tonight_intents),
                ("something funny from the 90s", "actually more action"),
            )

    def test_post_recommendation_shortlist_turns_people_filter_into_constraint(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate_source = RecordingCandidateSource()
            post_shortlist = recommendation_shortlist_endpoint(
                create_app(
                    backfill_store=SQLiteBackfillStore(
                        database_path=Path(directory) / "backfill.sqlite3"
                    ),
                    candidate_source=candidate_source,
                ),
                method="POST",
            )

            payload = post_shortlist(
                RecommendationShortlistRequestPayload(
                    sessionId="person-steered-session",
                    source="live_tmdb",
                    tonightIntents=[
                        {
                            "rawText": "something with Tom Cruise in it",
                            "filters": {"people": ["Tom Cruise"]},
                        },
                    ],
                )
            )

            self.assertEqual(
                tuple(
                    constraint.raw_name
                    for constraint in candidate_source.person_constraints[0]
                ),
                ("Tom Cruise",),
            )
            self.assertEqual(payload[0].matchedPersonNames, ["Tom Cruise"])
            self.assertEqual(
                candidate_source.sessions[0].tonight_intents[0].person_names,
                ("Tom Cruise",),
            )

    def test_post_recommendation_shortlist_preserves_excluded_signals_in_mood_text(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate_source = RecordingCandidateSource()
            post_shortlist = recommendation_shortlist_endpoint(
                create_app(
                    backfill_store=SQLiteBackfillStore(
                        database_path=Path(directory) / "backfill.sqlite3"
                    ),
                    candidate_source=candidate_source,
                ),
                method="POST",
            )

            payload = post_shortlist(
                RecommendationShortlistRequestPayload(
                    sessionId="excluded-signal-session",
                    source="live_tmdb",
                    tonightIntents=[
                        {
                            "rawText": "No cartoonish kids stuff",
                            "softSignals": ["cozy"],
                            "excludedSignals": ["animation", "family"],
                            "confidence": "high",
                        },
                    ],
                )
            )

            self.assertEqual(len(payload), 5)
            self.assertEqual(
                candidate_source.mood_texts,
                ("No cartoonish kids stuff + cozy + avoid animation + avoid family",),
            )
            structured_intent = candidate_source.sessions[0].tonight_intents[0]
            self.assertEqual(structured_intent.confidence, "high")
            self.assertIn(
                ("cozy", "positive"),
                {
                    (signal.concept, signal.polarity)
                    for signal in structured_intent.signals
                },
            )
            self.assertIn(
                ("animation", "negative"),
                {
                    (signal.concept, signal.polarity)
                    for signal in structured_intent.signals
                },
            )

    def test_post_recommendation_shortlist_returns_explicit_nudge_shortage_error(
        self,
    ) -> None:
        post_shortlist = recommendation_shortlist_endpoint(
            create_app(candidate_source=SparseCandidateSource()),
            method="POST",
        )

        with self.assertRaises(HTTPException) as raised:
            post_shortlist(
                RecommendationShortlistRequestPayload(
                    sessionId="shortage-session",
                    source="live_tmdb",
                    tonightIntents=[
                        {
                            "rawText": "something with Josh Brolin in it",
                            "filters": {"people": ["Josh Brolin"]},
                        },
                    ],
                )
            )

        self.assertEqual(raised.exception.status_code, 502)
        self.assertIn("couldn't find five movies", raised.exception.detail.casefold())
        self.assertIn("nudges", raised.exception.detail.casefold())

    def test_post_recommendation_shortlist_consumes_saved_taste_lab_profile_evidence(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot_store = SQLiteRecommendationSnapshotStore(
                database_path=Path(directory) / "taste-lab-shortlist-snapshot.sqlite3"
            )
            taste_lab_store = SQLiteTasteLabStore(
                database_path=Path(directory) / "taste-lab.sqlite3"
            )
            taste_lab_store.save_ratings(
                ratings=(
                    TasteLabRatingExport(
                        household_id="default-household",
                        profile_id="profile-1",
                        movie=TasteLabMovieIdentity(
                            source_movie_id="tmdb:101",
                            title="Knives Out",
                            genres=("Mystery", "Comedy"),
                        ),
                        label=TasteLabRatingLabel.LOVED,
                        rated_at="2026-07-01T12:00:00Z",
                    ),
                ),
            )
            post_shortlist = recommendation_shortlist_endpoint(
                create_app(
                    recommendation_snapshot_store=snapshot_store,
                    taste_lab_store=taste_lab_store,
                ),
                method="POST",
            )

            payload = post_shortlist(
                RecommendationShortlistRequestPayload(
                    sessionId="taste-lab-session",
                    participantIds=["profile-1", "profile-2"],
                )
            )

            snapshot = snapshot_store.load_snapshot("taste-lab-session")

            self.assertEqual(len(payload), 5)
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            self.assertTrue(
                any(
                    "Taste Lab signals: 1" in candidate.why_short
                    for candidate in snapshot.candidates
                )
            )

    def test_post_recommendation_shortlist_caps_dense_taste_lab_genre_strength(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "dense-taste-lab-shortlist.sqlite3"
            taste_lab_store = SQLiteTasteLabStore(database_path=database_path)
            taste_lab_store.save_ratings(
                ratings=tuple(
                    taste_lab_rating(
                        profile_id="profile-1",
                        title=f"Drama Seed {index}",
                        genres=("Drama",),
                        label=TasteLabRatingLabel.LOVED,
                    )
                    for index in range(12)
                )
            )
            post_shortlist = recommendation_shortlist_endpoint(
                create_app(
                    taste_lab_store=taste_lab_store,
                    candidate_source=FakeCandidateSource(),
                ),
                method="POST",
            )

            payload = post_shortlist(
                RecommendationShortlistRequestPayload(
                    sessionId="dense-taste-lab-session",
                    source="live_tmdb",
                    participantIds=["profile-1"],
                )
            )

            self.assertEqual(len(payload), 5)
            self.assertTrue(
                any("Taste Lab signals" in (item.whyShort or "") for item in payload)
            )

    def test_post_recommendation_shortlist_suppresses_exact_watched_memory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "memory-shortlist.sqlite3"
            backfill_store = SQLiteBackfillStore(database_path=database_path)
            ManualBackfillService(backfill_store).add_watched_title(
                household_id="default-household",
                entry=resolved_title_entry(
                    source_movie_id="tmdb:1",
                    title="Live Pick 1",
                ),
                include_global=True,
            )
            snapshot_store = SQLiteRecommendationSnapshotStore(
                database_path=database_path
            )
            post_shortlist = recommendation_shortlist_endpoint(
                create_app(
                    backfill_store=backfill_store,
                    recommendation_snapshot_store=snapshot_store,
                    candidate_source=SixCandidateSource(),
                ),
                method="POST",
            )

            payload = post_shortlist(
                RecommendationShortlistRequestPayload(
                    sessionId="watched-memory-session",
                    source="live_tmdb",
                )
            )

            snapshot = snapshot_store.load_snapshot("watched-memory-session")

            self.assertNotIn("tmdb:1", [item.sourceMovieId for item in payload])
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            watched_input = next(
                candidate
                for candidate in snapshot.candidate_inputs
                if candidate.source_movie_id == "tmdb:1"
            )
            self.assertTrue(watched_input.already_watched)

    def test_post_recommendation_shortlist_exposes_profile_app_memory_evidence(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "profile-memory-shortlist.sqlite3"
            backfill_store = SQLiteBackfillStore(database_path=database_path)
            ManualBackfillService(backfill_store).add_watched_title(
                household_id="default-household",
                entry=resolved_title_entry(
                    source_movie_id="tmdb:edge-original",
                    title="Edge of Tomorrow",
                ),
                participant_ids=("profile-1",),
                taste_label=BackfillTasteLabel.NO,
            )
            snapshot_store = SQLiteRecommendationSnapshotStore(
                database_path=database_path
            )
            post_shortlist = recommendation_shortlist_endpoint(
                create_app(
                    backfill_store=backfill_store,
                    recommendation_snapshot_store=snapshot_store,
                    candidate_source=MemoryEvidenceCandidateSource(),
                ),
                method="POST",
            )

            post_shortlist(
                RecommendationShortlistRequestPayload(
                    sessionId="profile-memory-session",
                    source="live_tmdb",
                    participantIds=["profile-1"],
                )
            )

            snapshot = snapshot_store.load_snapshot("profile-memory-session")

            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            edge_candidate = next(
                candidate
                for candidate in snapshot.candidates
                if candidate.title == "Edge of Tomorrow Again"
            )
            labels = {
                contribution.label
                for evidence in edge_candidate.scoring_evidence
                for contribution in evidence.contributions
            }
            self.assertIn("app_memory:Edge of Tomorrow", labels)

    def test_post_recommendation_shortlist_uses_persistent_taste_memory_events(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "persistent-memory-shortlist.sqlite3"
            taste_memory_store = SQLiteTasteMemoryStore(database_path=database_path)
            snapshot_store = SQLiteRecommendationSnapshotStore(
                database_path=database_path
            )
            post_shortlist = recommendation_shortlist_endpoint(
                create_app(
                    recommendation_snapshot_store=snapshot_store,
                    taste_memory_store=taste_memory_store,
                    candidate_source=PersistentMemoryCandidateSource(),
                ),
                method="POST",
            )

            before_payload = post_shortlist(
                RecommendationShortlistRequestPayload(
                    sessionId="persistent-memory-before",
                    source="live_tmdb",
                    participantIds=["profile-1"],
                )
            )
            TasteMemoryService(taste_memory_store).record_app_owned_rating(
                household_id="default-household",
                profile_id="profile-1",
                source_movie_id="tmdb:midnight-cipher",
                title="Midnight Cipher",
                taste_label=BackfillTasteLabel.LOVED,
                occurred_at="2026-07-07T12:00:00Z",
            )
            after_payload = post_shortlist(
                RecommendationShortlistRequestPayload(
                    sessionId="persistent-memory-after",
                    source="live_tmdb",
                    participantIds=["profile-1"],
                )
            )
            other_profile_payload = post_shortlist(
                RecommendationShortlistRequestPayload(
                    sessionId="persistent-memory-other-profile",
                    source="live_tmdb",
                    participantIds=["profile-2"],
                )
            )

            after_snapshot = snapshot_store.load_snapshot("persistent-memory-after")

            before_rank = next(
                index
                for index, item in enumerate(before_payload, start=1)
                if item.title == "Midnight Cipher Returns"
            )
            after_rank = next(
                index
                for index, item in enumerate(after_payload, start=1)
                if item.title == "Midnight Cipher Returns"
            )

            self.assertNotEqual(before_payload[0].title, "Midnight Cipher Returns")
            self.assertLess(after_rank, before_rank)
            self.assertNotEqual(
                other_profile_payload[0].title,
                "Midnight Cipher Returns",
            )
            self.assertIsNotNone(after_snapshot)
            assert after_snapshot is not None
            memory_candidate = next(
                candidate
                for candidate in after_snapshot.candidates
                if candidate.title == "Midnight Cipher Returns"
            )
            self.assertIn("Memory signals: 1", memory_candidate.why_short)
            self.assertIn(
                "title_similarity",
                memory_candidate.scoring_evidence[0].signal_families,
            )

    def test_post_recommendation_shortlist_surfaces_household_compromise_pick(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "compromise-shortlist.sqlite3"
            taste_lab_store = SQLiteTasteLabStore(database_path=database_path)
            taste_lab_store.save_ratings(
                ratings=(
                    taste_lab_rating(
                        profile_id="profile-1",
                        title="Loud Action Seed",
                        genres=("Action",),
                        label=TasteLabRatingLabel.LOVED,
                    ),
                    taste_lab_rating(
                        profile_id="profile-1",
                        title="Action Comedy Bridge",
                        genres=("Action", "Comedy"),
                        label=TasteLabRatingLabel.LOVED,
                    ),
                ),
            )
            taste_lab_store.save_ratings(
                ratings=(
                    taste_lab_rating(
                        profile_id="profile-2",
                        title="Silly Comedy Seed",
                        genres=("Comedy",),
                        label=TasteLabRatingLabel.LOVED,
                    ),
                    taste_lab_rating(
                        profile_id="profile-2",
                        title="Action Comedy Bridge",
                        genres=("Action", "Comedy"),
                        label=TasteLabRatingLabel.LOVED,
                    ),
                ),
            )
            snapshot_store = SQLiteRecommendationSnapshotStore(
                database_path=database_path
            )
            post_shortlist = recommendation_shortlist_endpoint(
                create_app(
                    recommendation_snapshot_store=snapshot_store,
                    taste_lab_store=taste_lab_store,
                    candidate_source=CompromiseCandidateSource(),
                ),
                method="POST",
            )

            payload = post_shortlist(
                RecommendationShortlistRequestPayload(
                    sessionId="household-compromise-session",
                    source="live_tmdb",
                    participantIds=["profile-1", "profile-2"],
                )
            )

            snapshot = snapshot_store.load_snapshot("household-compromise-session")

            self.assertEqual(payload[0].title, "Action Comedy Bridge")
            self.assertIsNotNone(snapshot)
            assert snapshot is not None
            compromise_candidate = snapshot.candidates[0]
            self.assertEqual(compromise_candidate.title, "Action Comedy Bridge")
            self.assertEqual(compromise_candidate.fit_bucket, "compromise")
            self.assertEqual(len(compromise_candidate.user_scores), 2)
            self.assertIn(
                "genre",
                compromise_candidate.scoring_evidence[0].signal_families,
            )


def recommendation_shortlist_endpoint(app, method: str = "GET"):
    for route in app.routes:
        if (
            isinstance(route, APIRoute)
            and route.path == "/recommendations/shortlist"
            and method in route.methods
        ):
            return route.endpoint

    raise AssertionError(
        f"{method} /recommendations/shortlist route was not registered."
    )


class FakeCandidateSource:
    def fetch_candidates(
        self,
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        limit: int = 20,
    ) -> tuple[Candidate, ...]:
        return tuple(
            Candidate(
                source_movie_id=f"tmdb:{index}",
                title=f"Live Pick {index}",
                media_type=MediaType.MOVIE,
                release_year=2020 + index,
                runtime_min=95 + index,
                poster_url=f"https://example.test/poster-{index}.jpg",
                genres=("Drama", "Sci-Fi"),
                overview=f"Live overview {index}.",
                providers=("Amazon Prime Video",),
                provider_availability=(
                    ProviderAvailability(
                        provider_name="Amazon Prime Video",
                        access_type=ProviderAccessType.FLATRATE,
                        region="DE",
                    ),
                ),
                original_language="en",
                spoken_languages=("en",),
                matched_person_names=tuple(
                    constraint.raw_name
                    for constraint in session.person_constraints
                ),
            )
            for index in range(1, min(limit, 5) + 1)
        )


class FakePagedTmdbClient:
    def __init__(self, movie_ids: tuple[int, ...]) -> None:
        self._movie_ids = movie_ids

    def get_json(self, path: str, *, params=None):
        if path == "/discover/movie":
            assert params is not None
            page = int(params.get("page", "1"))
            start = (page - 1) * 20
            end = start + 20
            return {
                "results": [
                    {
                        "id": movie_id,
                        "title": f"Live Candidate {movie_id}",
                        "release_date": "2024-01-01",
                        "overview": f"Overview for {movie_id}.",
                        "original_language": "en",
                        "poster_path": f"/poster-{movie_id}.jpg",
                    }
                    for movie_id in self._movie_ids[start:end]
                ],
                "total_pages": max(1, (len(self._movie_ids) + 19) // 20),
            }

        if path.endswith("/watch/providers"):
            return {
                "results": {
                    "DE": {
                        "flatrate": [{"provider_name": "Amazon Prime Video"}],
                    }
                }
            }

        movie_id = int(path.removeprefix("/movie/").split("/", maxsplit=1)[0])
        return {
            "id": movie_id,
            "title": f"Live Candidate {movie_id}",
            "release_date": "2024-01-01",
            "runtime": 100 + movie_id,
            "genres": [{"name": "Drama"}, {"name": "Thriller"}],
            "overview": f"Overview for {movie_id}.",
            "original_language": "en",
            "spoken_languages": [{"iso_639_1": "en"}],
            "credits": {"cast": []},
        }


class RecordingCandidateSource(FakeCandidateSource):
    def __init__(self) -> None:
        self.mood_texts: tuple[str | None, ...] = ()
        self.person_constraints = ()
        self.sessions: list[SessionContext] = []

    def fetch_candidates(
        self,
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        limit: int = 20,
    ) -> tuple[Candidate, ...]:
        self.sessions.append(session)
        self.mood_texts = (*self.mood_texts, session.mood_text)
        self.person_constraints = (
            *self.person_constraints,
            session.person_constraints,
        )
        return super().fetch_candidates(
            session=session,
            household_defaults=household_defaults,
            limit=limit,
        )


class SixCandidateSource(FakeCandidateSource):
    def fetch_candidates(
        self,
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        limit: int = 20,
    ) -> tuple[Candidate, ...]:
        return tuple(
            live_candidate(index=index, title=f"Live Pick {index}")
            for index in range(1, min(limit, 6) + 1)
        )


class RecordingSixCandidateSource(SixCandidateSource):
    def __init__(self) -> None:
        self.sessions: list[SessionContext] = []

    def fetch_candidates(
        self,
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        limit: int = 20,
    ) -> tuple[Candidate, ...]:
        self.sessions.append(session)
        return super().fetch_candidates(
            session=session,
            household_defaults=household_defaults,
            limit=limit,
        )


class MemoryEvidenceCandidateSource:
    def fetch_candidates(
        self,
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        limit: int = 20,
    ) -> tuple[Candidate, ...]:
        return (
            live_candidate(index=1, title="Edge of Tomorrow Again"),
            live_candidate(index=2, title="Dinner Party Mystery"),
            live_candidate(index=3, title="Arrival"),
            live_candidate(index=4, title="Paddington 2"),
            live_candidate(index=5, title="The Shining"),
        )


class PersistentMemoryCandidateSource:
    def fetch_candidates(
        self,
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        limit: int = 20,
        ) -> tuple[Candidate, ...]:
        return (
            persistent_memory_candidate(
                index=1,
                title="Distant Planet",
                genres=("Mystery", "Comedy"),
            ),
            persistent_memory_candidate(
                index=2,
                title="Midnight Cipher Returns",
                genres=(),
            ),
            persistent_memory_candidate(index=3, title="Arrival", genres=("Drama",)),
            persistent_memory_candidate(
                index=4,
                title="Paddington 2",
                genres=("Comedy",),
            ),
            persistent_memory_candidate(
                index=5,
                title="The Shining",
                genres=("Horror",),
            ),
        )


def persistent_memory_candidate(
    *,
    index: int,
    title: str,
    genres: tuple[str, ...],
) -> Candidate:
    return Candidate(
        source_movie_id=f"tmdb:{index}",
        title=title,
        media_type=MediaType.MOVIE,
        release_year=2020 + index,
        runtime_min=95 + index,
        poster_url=f"https://example.test/poster-{index}.jpg",
        genres=genres,
        overview=f"Live overview {index}.",
        providers=("Amazon Prime Video",),
        provider_availability=(
            ProviderAvailability(
                provider_name="Amazon Prime Video",
                access_type=ProviderAccessType.FLATRATE,
                region="DE",
            ),
        ),
        original_language="en",
        spoken_languages=("en",),
    )


def taste_lab_rating(
    *,
    profile_id: str,
    title: str,
    genres: tuple[str, ...],
    label: TasteLabRatingLabel,
) -> TasteLabRatingExport:
    return TasteLabRatingExport(
        household_id="default-household",
        profile_id=profile_id,
        movie=TasteLabMovieIdentity(
            source_movie_id=f"fixture:{title.casefold().replace(' ', '-')}",
            title=title,
            genres=genres,
        ),
        label=label,
        rated_at="2026-07-07T12:00:00Z",
    )


class CompromiseCandidateSource:
    def fetch_candidates(
        self,
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        limit: int = 20,
    ) -> tuple[Candidate, ...]:
        return (
            persistent_memory_candidate(
                index=101,
                title="Pure Action Night",
                genres=("Action",),
            ),
            persistent_memory_candidate(
                index=102,
                title="Pure Comedy Night",
                genres=("Comedy",),
            ),
            persistent_memory_candidate(
                index=103,
                title="Action Comedy Bridge",
                genres=("Action", "Comedy"),
            ),
            persistent_memory_candidate(index=104, title="Quiet Drama", genres=("Drama",)),
            persistent_memory_candidate(
                index=105,
                title="Puzzle Mystery",
                genres=("Mystery",),
            ),
        )


class SparseCandidateSource:
    def fetch_candidates(
        self,
        *,
        session: SessionContext,
        household_defaults: HouseholdDefaults,
        limit: int = 20,
    ) -> tuple[Candidate, ...]:
        return (
            live_candidate(index=1, title="Only Match 1"),
            live_candidate(index=2, title="Only Match 2"),
        )


def live_candidate(*, index: int, title: str) -> Candidate:
    return Candidate(
        source_movie_id=f"tmdb:{index}",
        title=title,
        media_type=MediaType.MOVIE,
        release_year=2020 + index,
        runtime_min=95 + index,
        poster_url=f"https://example.test/poster-{index}.jpg",
        genres=("Drama", "Sci-Fi"),
        overview=f"Live overview {index}.",
        providers=("Amazon Prime Video",),
        provider_availability=(
            ProviderAvailability(
                provider_name="Amazon Prime Video",
                access_type=ProviderAccessType.FLATRATE,
                region="DE",
            ),
        ),
        original_language="en",
        spoken_languages=("en",),
    )


def resolved_title_entry(*, source_movie_id: str, title: str) -> TitleResolutionEntry:
    source, _, source_id = source_movie_id.partition(":")
    return TitleResolutionEntry.resolved(
        title,
        TitleResolutionCandidate(
            source=source,
            source_id=source_id,
            title=title,
            media_type=MediaType.MOVIE,
        ),
    )


if __name__ == "__main__":
    unittest.main()
