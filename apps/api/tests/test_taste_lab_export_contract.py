from __future__ import annotations

import unittest

from movie_night_mediator.taste_lab import (
    TASTE_LAB_EXPORT_SCHEMA_VERSION,
    TasteLabFamiliarity,
    TasteLabMovieIdentity,
    TasteLabQueueProvenance,
    TasteLabRatingExport,
    TasteLabRatingLabel,
    WatchSignalTasteSignal,
)


class TasteLabExportContractTest(unittest.TestCase):
    def test_havent_seen_is_familiarity_only_not_negative_preference(self) -> None:
        export = TasteLabRatingExport(
            household_id="household-1",
            profile_id="sandy",
            movie=TasteLabMovieIdentity(
                source_movie_id="tmdb:603",
                title="The Matrix",
                release_year=1999,
            ),
            label=TasteLabRatingLabel.HAVENT_SEEN,
            rated_at="2026-07-01T12:00:00Z",
        )

        self.assertEqual(export.familiarity, TasteLabFamiliarity.UNSEEN)
        self.assertIsNone(export.preference_value)
        self.assertFalse(export.is_importable_preference)
        self.assertEqual(
            export.watchsignal_taste_signal,
            WatchSignalTasteSignal.FAMILIARITY_ONLY,
        )

    def test_seen_labels_map_to_importable_watchsignal_taste_signals(self) -> None:
        cases = (
            (TasteLabRatingLabel.LOVED, 1.0, WatchSignalTasteSignal.STRONG_POSITIVE),
            (TasteLabRatingLabel.LIKED, 0.65, WatchSignalTasteSignal.POSITIVE),
            (TasteLabRatingLabel.MEH, 0.0, WatchSignalTasteSignal.NEUTRAL),
            (TasteLabRatingLabel.HATED, -1.0, WatchSignalTasteSignal.STRONG_NEGATIVE),
        )

        for label, preference_value, signal in cases:
            with self.subTest(label=label):
                export = TasteLabRatingExport(
                    profile_id="robin",
                    movie=TasteLabMovieIdentity(
                        source_movie_id=f"movielens:{label.value}",
                        title=f"{label.value.title()} Movie",
                    ),
                    label=label,
                    rated_at="2026-07-01T12:00:00Z",
                )

                self.assertEqual(export.familiarity, TasteLabFamiliarity.SEEN)
                self.assertEqual(export.preference_value, preference_value)
                self.assertEqual(export.watchsignal_taste_signal, signal)
                self.assertTrue(export.is_importable_preference)

    def test_export_round_trip_preserves_stable_json_shape(self) -> None:
        export = TasteLabRatingExport(
            household_id="household-1",
            profile_id="sandy",
            movie=TasteLabMovieIdentity(
                source_movie_id="movielens:1",
                title="Galaxy Divide",
                release_year=1999,
                tmdb_id="12345",
                poster_path="/poster.jpg",
                genres=("Sci-Fi", "Drama"),
            ),
            label=TasteLabRatingLabel.LOVED,
            rated_at="2026-07-01T12:00:00Z",
            queue_provenance=TasteLabQueueProvenance(
                queue_source="offline_signal_score_v1",
                generated_at="2026-07-01T11:00:00Z",
                rank=1,
                signal_score=0.91,
                score_components={
                    "recognizability": 0.99,
                    "divisiveness": 0.88,
                },
            ),
        )

        payload = export.as_dict()
        loaded = TasteLabRatingExport.from_dict(payload)

        self.assertEqual(payload["schema_version"], TASTE_LAB_EXPORT_SCHEMA_VERSION)
        self.assertEqual(payload["profile_id"], "sandy")
        self.assertEqual(payload["movie"]["source_movie_id"], "movielens:1")
        self.assertEqual(
            payload["queue_provenance"]["queue_source"],
            "offline_signal_score_v1",
        )
        self.assertEqual(loaded.as_dict(), payload)

    def test_rejects_inconsistent_havent_seen_familiarity(self) -> None:
        with self.assertRaisesRegex(ValueError, "familiarity must match"):
            TasteLabRatingExport(
                profile_id="sandy",
                movie=TasteLabMovieIdentity(
                    source_movie_id="tmdb:1",
                    title="Mismatch",
                ),
                label=TasteLabRatingLabel.HAVENT_SEEN,
                familiarity=TasteLabFamiliarity.SEEN,
                rated_at="2026-07-01T12:00:00Z",
            )

    def test_rejects_unsupported_schema_version(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported Taste Lab export"):
            TasteLabRatingExport(
                profile_id="sandy",
                movie=TasteLabMovieIdentity(
                    source_movie_id="tmdb:1",
                    title="Future Contract",
                ),
                label=TasteLabRatingLabel.LOVED,
                rated_at="2026-07-01T12:00:00Z",
                schema_version="taste_lab.rating_export.v99",
            )


if __name__ == "__main__":
    unittest.main()
