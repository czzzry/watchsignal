from __future__ import annotations

from movie_night_mediator.domain.models import (
    Candidate,
    HouseholdDefaults,
    ManualWatchabilityCorrection,
    ProviderAccessType,
    ProviderAvailability,
    SessionContext,
    WatchabilityClassification,
    WatchabilityStatus,
)

PRIME_VIDEO_PROVIDER_ALIASES = frozenset(
    {
        "prime video",
        "amazon prime video",
        "amazon prime",
    }
)


class SafePickClassifier:
    def classify(
        self,
        candidate: Candidate,
        *,
        session: SessionContext | None = None,
        household_defaults: HouseholdDefaults | None = None,
        manual_correction: ManualWatchabilityCorrection | None = None,
    ) -> WatchabilityClassification:
        resolved_session = session or SessionContext(session_id="watchability")
        resolved_defaults = household_defaults or HouseholdDefaults()
        reasons: list[str] = []

        if manual_correction is not None and manual_correction.source_movie_id != candidate.source_movie_id:
            raise ValueError("Manual watchability correction does not match candidate.")

        if candidate.media_type != resolved_session.requested_media_type:
            return self._classification(
                candidate,
                WatchabilityStatus.REJECTED,
                ("media_type_mismatch",),
                manual_correction,
            )

        avoids_rewatch = resolved_defaults.rewatch_avoidance_default and not resolved_session.allow_rewatch
        if avoids_rewatch and candidate.already_watched:
            return self._classification(
                candidate,
                WatchabilityStatus.REJECTED,
                ("already_watched",),
                manual_correction,
            )

        if manual_correction is not None and manual_correction.verified_watchable is False:
            return self._classification(
                candidate,
                WatchabilityStatus.REJECTED,
                ("manual_verified_unwatchable",),
                manual_correction,
            )

        provider_passes = self._has_flatrate_prime_video(
            candidate.provider_availability,
            region=resolved_session.region or resolved_defaults.default_region,
        )
        if manual_correction is not None and manual_correction.verified_watchable is True:
            provider_passes = True
            reasons.append("manual_verified_watchable")

        if not provider_passes:
            reasons.append("prime_germany_subscription_not_verified")
            if self._has_non_subscription_amazon_access(candidate.provider_availability):
                reasons.append("amazon_rent_or_buy_only")
            elif candidate.providers:
                reasons.append("provider_bucket_missing")
            return self._classification(
                candidate,
                WatchabilityStatus.NEEDS_QUICK_CHECK,
                tuple(reasons),
                manual_correction,
            )

        if self._language_passes(candidate, manual_correction):
            reasons.append("english_original_or_verified_subtitles")
            return self._classification(
                candidate,
                WatchabilityStatus.SAFE_PICK,
                tuple(reasons),
                manual_correction,
            )

        return self._classification(
            candidate,
            WatchabilityStatus.NEEDS_QUICK_CHECK,
            tuple((*reasons, "english_subtitles_not_verified")),
            manual_correction,
        )

    def _classification(
        self,
        candidate: Candidate,
        status: WatchabilityStatus,
        reasons: tuple[str, ...],
        manual_correction: ManualWatchabilityCorrection | None,
    ) -> WatchabilityClassification:
        return WatchabilityClassification(
            source_movie_id=candidate.source_movie_id,
            title=candidate.title,
            status=status,
            reasons=reasons,
            manual_correction_applied=manual_correction is not None,
        )

    def _has_flatrate_prime_video(
        self,
        provider_availability: tuple[ProviderAvailability, ...],
        *,
        region: str,
    ) -> bool:
        expected_region = region.upper()
        return any(
            availability.region.upper() == expected_region
            and availability.access_type == ProviderAccessType.FLATRATE
            and self._is_prime_video(availability.provider_name)
            for availability in provider_availability
        )

    def _has_non_subscription_amazon_access(
        self,
        provider_availability: tuple[ProviderAvailability, ...],
    ) -> bool:
        return any(
            availability.access_type in {ProviderAccessType.RENT, ProviderAccessType.BUY}
            and self._is_amazon_or_prime_video(availability.provider_name)
            for availability in provider_availability
        )

    def _language_passes(
        self,
        candidate: Candidate,
        manual_correction: ManualWatchabilityCorrection | None,
    ) -> bool:
        if candidate.original_language.lower() == "en":
            return True
        if candidate.english_subtitles_verified:
            return True
        if manual_correction is None:
            return False
        return manual_correction.verified_watchable is True or manual_correction.english_subtitles_verified

    def _is_prime_video(self, provider_name: str) -> bool:
        return self._normalize_provider(provider_name) in PRIME_VIDEO_PROVIDER_ALIASES

    def _is_amazon_or_prime_video(self, provider_name: str) -> bool:
        normalized_provider = self._normalize_provider(provider_name)
        return normalized_provider in PRIME_VIDEO_PROVIDER_ALIASES or normalized_provider == "amazon video"

    def _normalize_provider(self, provider_name: str) -> str:
        return " ".join(provider_name.casefold().split())
