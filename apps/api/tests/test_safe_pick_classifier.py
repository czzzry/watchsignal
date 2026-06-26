import unittest

from movie_night_mediator.app.safe_pick import SafePickClassifier
from movie_night_mediator.domain import (
    Candidate,
    ManualWatchabilityCorrection,
    MediaType,
    ProviderAccessType,
    ProviderAvailability,
    SessionContext,
    WatchabilityStatus,
)


class SafePickClassifierTest(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = SafePickClassifier()

    def test_english_original_with_prime_germany_flatrate_is_safe_pick(self) -> None:
        result = self.classifier.classify(
            Candidate(
                source_movie_id="tmdb:603",
                title="The Matrix",
                media_type=MediaType.MOVIE,
                original_language="en",
                provider_availability=(
                    ProviderAvailability(
                        provider_name="Prime Video",
                        access_type=ProviderAccessType.FLATRATE,
                        region="DE",
                    ),
                ),
            )
        )

        self.assertEqual(result.status, WatchabilityStatus.SAFE_PICK)
        self.assertIn("english_original_or_verified_subtitles", result.reasons)

    def test_amazon_rent_or_buy_without_prime_flatrate_needs_quick_check(self) -> None:
        result = self.classifier.classify(
            Candidate(
                source_movie_id="tmdb:11",
                title="Rentable Only",
                media_type=MediaType.MOVIE,
                original_language="en",
                provider_availability=(
                    ProviderAvailability(
                        provider_name="Amazon Video",
                        access_type=ProviderAccessType.RENT,
                        region="DE",
                    ),
                    ProviderAvailability(
                        provider_name="Prime Video",
                        access_type=ProviderAccessType.BUY,
                        region="DE",
                    ),
                ),
            )
        )

        self.assertEqual(result.status, WatchabilityStatus.NEEDS_QUICK_CHECK)
        self.assertIn("amazon_rent_or_buy_only", result.reasons)

    def test_foreign_language_without_verified_english_subtitles_needs_quick_check(self) -> None:
        result = self.classifier.classify(
            Candidate(
                source_movie_id="tmdb:496243",
                title="Foreign Language Choice",
                media_type=MediaType.MOVIE,
                original_language="ko",
                provider_availability=(
                    ProviderAvailability(
                        provider_name="Prime Video",
                        access_type=ProviderAccessType.FLATRATE,
                        region="DE",
                    ),
                ),
            )
        )

        self.assertEqual(result.status, WatchabilityStatus.NEEDS_QUICK_CHECK)
        self.assertIn("english_subtitles_not_verified", result.reasons)

    def test_foreign_language_with_verified_english_subtitles_is_safe_pick(self) -> None:
        result = self.classifier.classify(
            Candidate(
                source_movie_id="tmdb:496243",
                title="Subtitled Choice",
                media_type=MediaType.MOVIE,
                original_language="ko",
                english_subtitles_verified=True,
                provider_availability=(
                    ProviderAvailability(
                        provider_name="Prime Video",
                        access_type=ProviderAccessType.FLATRATE,
                        region="DE",
                    ),
                ),
            )
        )

        self.assertEqual(result.status, WatchabilityStatus.SAFE_PICK)

    def test_already_watched_is_rejected_unless_rewatches_are_allowed(self) -> None:
        candidate = Candidate(
            source_movie_id="tmdb:13",
            title="Known Choice",
            media_type=MediaType.MOVIE,
            original_language="en",
            already_watched=True,
            provider_availability=(
                ProviderAvailability(
                    provider_name="Prime Video",
                    access_type=ProviderAccessType.FLATRATE,
                    region="DE",
                ),
            ),
        )

        rejected_result = self.classifier.classify(candidate)
        allowed_result = self.classifier.classify(
            candidate,
            session=SessionContext(session_id="rewatch-session", allow_rewatch=True),
        )

        self.assertEqual(rejected_result.status, WatchabilityStatus.REJECTED)
        self.assertIn("already_watched", rejected_result.reasons)
        self.assertEqual(allowed_result.status, WatchabilityStatus.SAFE_PICK)

    def test_manual_verified_watchable_correction_can_upgrade_to_safe_pick(self) -> None:
        result = self.classifier.classify(
            Candidate(
                source_movie_id="tmdb:999",
                title="Manually Checked Choice",
                media_type=MediaType.MOVIE,
                original_language="ja",
            ),
            manual_correction=ManualWatchabilityCorrection(
                source_movie_id="tmdb:999",
                verified_watchable=True,
                notes="Generic manual fixture note.",
            ),
        )

        self.assertEqual(result.status, WatchabilityStatus.SAFE_PICK)
        self.assertTrue(result.manual_correction_applied)
        self.assertIn("manual_verified_watchable", result.reasons)

    def test_manual_english_subtitle_correction_can_clarify_language_gate(self) -> None:
        result = self.classifier.classify(
            Candidate(
                source_movie_id="tmdb:496243",
                title="Manually Subtitle Checked Choice",
                media_type=MediaType.MOVIE,
                original_language="ko",
                provider_availability=(
                    ProviderAvailability(
                        provider_name="Prime Video",
                        access_type=ProviderAccessType.FLATRATE,
                        region="DE",
                    ),
                ),
            ),
            manual_correction=ManualWatchabilityCorrection(
                source_movie_id="tmdb:496243",
                english_subtitles_verified=True,
            ),
        )

        self.assertEqual(result.status, WatchabilityStatus.SAFE_PICK)
        self.assertTrue(result.manual_correction_applied)
        self.assertIn("english_original_or_verified_subtitles", result.reasons)

    def test_manual_subtitle_correction_does_not_override_missing_prime_flatrate(self) -> None:
        result = self.classifier.classify(
            Candidate(
                source_movie_id="tmdb:496243",
                title="Subtitle Checked But Not On Prime",
                media_type=MediaType.MOVIE,
                original_language="ko",
            ),
            manual_correction=ManualWatchabilityCorrection(
                source_movie_id="tmdb:496243",
                english_subtitles_verified=True,
            ),
        )

        self.assertEqual(result.status, WatchabilityStatus.NEEDS_QUICK_CHECK)
        self.assertTrue(result.manual_correction_applied)
        self.assertIn("prime_germany_subscription_not_verified", result.reasons)

    def test_manual_verified_unwatchable_correction_rejects_candidate(self) -> None:
        result = self.classifier.classify(
            Candidate(
                source_movie_id="tmdb:603",
                title="The Matrix",
                media_type=MediaType.MOVIE,
                original_language="en",
                provider_availability=(
                    ProviderAvailability(
                        provider_name="Prime Video",
                        access_type=ProviderAccessType.FLATRATE,
                        region="DE",
                    ),
                ),
            ),
            manual_correction=ManualWatchabilityCorrection(
                source_movie_id="tmdb:603",
                verified_watchable=False,
            ),
        )

        self.assertEqual(result.status, WatchabilityStatus.REJECTED)
        self.assertIn("manual_verified_unwatchable", result.reasons)


if __name__ == "__main__":
    unittest.main()
