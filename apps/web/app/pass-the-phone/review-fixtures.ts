import type { SessionMode } from "../session-fixtures";
import type { RankedCandidate } from "../pass-the-phone-model";
import type {
  DebugHistorySessionPayload,
  TasteProfileSummaryPayload,
} from "../session-client";

export function reviewModeV2DebugHistory({
  bestPick,
  participantIds,
  sessionMode,
}: {
  bestPick: RankedCandidate;
  participantIds: string[];
  sessionMode: SessionMode;
}): DebugHistorySessionPayload {
  const sessionId = "review-v2-explanation";
  return {
    activeMode: sessionMode,
    batchCount: 1,
    bestPickSourceMovieId: bestPick.id,
    founderReactions: [],
    householdId: "default-household",
    participantIds,
    postWatchFeedback: [],
    previousFounderReactions: [],
    previousShortlist: [],
    previousWifeReactions: [],
    recommendationSnapshot: {
      candidateInputs: [
        {
          alreadyWatched: false,
          enrichmentFeatureScores: {
            profile_concept_fit: 0.82,
            candidate_concept_depth: 0.74,
          },
          enrichmentProvider: "review_fixture",
          enrichmentStatus: "enriched",
          genres: bestPick.genres,
          isInterestingSafePick: bestPick.safePickStatus === "Safe Pick",
          matchedEnrichmentSourceMovieId: bestPick.id,
          providerAccess: [bestPick.availability],
          providers: [bestPick.availability],
          safetyStatus: bestPick.safePickStatus,
          sourceMovieId: bestPick.id,
          title: bestPick.title,
        },
      ],
      candidates: [
        {
          candidateRank: 1,
          dominantPositiveEvidence: [
            "profile_memory:concept_fit",
            "candidate_metadata:theme_depth",
            "shared_reconciliation:bridge_pick",
          ],
          dominantPenalties: ["negative_preference:slow_burn_risk"],
          fitBucket: "strong",
          groupScore: bestPick.score,
          hardFilterPass: true,
          isInterestingPick: true,
          scoringEvidence: [
            {
              contributions: [
                {
                  family: "profile_memory",
                  label: "profile_memory:concept_fit",
                  value: 0.42,
                },
                {
                  family: "candidate_metadata",
                  label: "candidate_metadata:theme_depth",
                  value: 0.31,
                },
                {
                  family: "negative_preference",
                  label: "negative_preference:slow_burn_risk",
                  value: -0.11,
                },
              ],
              enrichmentStatus: "enriched",
              signalFamilies: [
                "profile_memory",
                "candidate_metadata",
                "negative_preference",
              ],
              sourceMovieId: bestPick.id,
            },
          ],
          sourceMovieId: bestPick.id,
          title: bestPick.title,
          userScores: participantIds.map((participantId, index) => ({
            score: index === 0 ? 0.86 : 0.8,
            userId: participantId,
          })),
          whyShort:
            "V2 review fixture showing profile fit, candidate metadata, and a visible penalty.",
        },
      ],
      confidenceLabel: "medium",
      confidenceScore: 0.74,
      enrichmentCoverage: {
        candidateCount: 1,
        enrichedCandidateCount: 1,
        enrichmentRate: 1,
        fallbackCandidateCount: 0,
      },
      fallbackReason: null,
      interestingSafePickId: bestPick.id,
      isUncertain: false,
      partialSupportNotes: [
        "V2 explanation fixture: profile and candidate evidence are visible in review mode.",
      ],
      recommendedFollowUp: null,
      scorerVersion: "v2_contract",
      sessionId,
      uncertaintyReason: null,
    },
    rerankedSourceMovieIds: [bestPick.id],
    sessionId,
    sessionOutcome: null,
    shortlist: [
      {
        candidateRank: 1,
        sourceMovieId: bestPick.id,
        title: bestPick.title,
      },
    ],
    shownSourceMovieIds: [bestPick.id],
    state: "reranked",
    unavailableEvidence: [],
    wifeReactions: [],
  };
}

export function reviewModeTasteProfileSummaries(
  participantIds: string[],
): TasteProfileSummaryPayload[] {
  return participantIds.map((profileId) => ({
    evidence: [],
    familiarityOnlyCount: 0,
    genreSignals: [],
    householdId: "default-household",
    preferenceEvidenceCount: 1,
    profileId,
    ratingCount: 1,
  }));
}
