"use client";

import type { SessionMode } from "./session-fixtures";
import type {
  AppOwnedMovieRatingPayload,
  AppOwnedMovieWatchedPayload,
  DebugHistoryCandidateInputPayload,
  DebugHistoryEnrichmentCoveragePayload,
  DebugHistoryFeedbackPayload,
  DebugHistoryOutcomePayload,
  DebugHistoryReactionPayload,
  DebugHistoryRecommendationCandidatePayload,
  DebugHistoryRecommendationSnapshotPayload,
  DebugHistoryScoringEvidencePayload,
  DebugHistorySignalContributionPayload,
  DebugHistoryUserScorePayload,
  OnboardingCompletionPayload,
  OnboardingConstraintsPayload as BackendOnboardingConstraintsPayload,
  OutcomeSelectionOrigin,
  ParticipantOnboardingPayload as BackendParticipantOnboardingPayload,
  PostWatchFeedbackPayload,
  ProfileMemorySignalPayload,
  ProfileMemorySummaryPayload,
  RecentSessionFeedbackPayload,
  RecentSessionSummaryPayload as BackendRecentSessionSummaryPayload,
  RecommendationProviderAvailabilityPayload,
  RecommendationShortlistItemPayload,
  SaveSessionOutcomePayload,
  SaveWatchlistEntryPayload,
  ScoringSessionReactionPayload,
  SessionMode as BackendSessionMode,
  SessionOutcomePayload as BackendSessionOutcomePayload,
  SessionOutcomeType,
  SessionReactionPayload,
  SessionShortlistItemPayload,
  SharedSessionPayload as BackendSharedSessionPayload,
  TasteGenreSignalPayload,
  TasteMemoryEventPayload,
  TasteProfileSummaryPayload,
  TitleResolutionCandidatePayload,
  TitleResolutionEntryPayload,
  TonightIntentInterpretationPayload,
  WatchlistEntryPayload,
  WatchedTitleBackfillPayload,
  DebugHistorySessionPayload as BackendDebugHistorySessionPayload,
} from "./api-contract.generated";

export type {
  DebugHistoryCandidateInputPayload,
  DebugHistoryEnrichmentCoveragePayload,
  DebugHistoryFeedbackPayload,
  DebugHistoryOutcomePayload,
  DebugHistoryReactionPayload,
  DebugHistoryRecommendationCandidatePayload,
  DebugHistoryRecommendationSnapshotPayload,
  DebugHistoryScoringEvidencePayload,
  DebugHistorySignalContributionPayload,
  DebugHistoryUserScorePayload,
  OnboardingCompletionPayload,
  OutcomeSelectionOrigin,
  PostWatchFeedbackPayload,
  ProfileMemorySignalPayload,
  ProfileMemorySummaryPayload,
  RecentSessionFeedbackPayload,
  ScoringSessionReactionPayload,
  SessionOutcomeType,
  SessionReactionPayload,
  SessionShortlistItemPayload,
  TasteGenreSignalPayload,
  TasteMemoryEventPayload,
  TasteProfileSummaryPayload,
  TitleResolutionCandidatePayload,
  TitleResolutionEntryPayload,
  TonightIntentInterpretationPayload,
  WatchlistEntryPayload,
  WatchedTitleBackfillPayload,
};

export type ApiSessionMode = BackendSessionMode;
export type ShortlistCandidatePayload = RecommendationShortlistItemPayload;
export type SaveSessionOutcomeRequest = SaveSessionOutcomePayload;
export type SavePostWatchFeedbackRequest = PostWatchFeedbackPayload;
export type SaveWatchlistEntryRequest = SaveWatchlistEntryPayload;
export type AppOwnedMovieRatingRequest = AppOwnedMovieRatingPayload;
export type AppOwnedMovieWatchedRequest = AppOwnedMovieWatchedPayload;
type NormalizeNullables<T, TKey extends keyof T> = Omit<T, TKey> & {
  [Key in TKey]-?: Exclude<T[Key], undefined>;
};

export type SharedSessionPayload = NormalizeNullables<
  BackendSharedSessionPayload,
  "bestPickSourceMovieId"
>;
export type DebugHistorySessionPayload = NormalizeNullables<
  BackendDebugHistorySessionPayload,
  "bestPickSourceMovieId" | "recommendationSnapshot" | "sessionOutcome"
>;
export type OnboardingConstraintsPayload = NormalizeNullables<
  BackendOnboardingConstraintsPayload,
  "horrorExclusion" | "subtitleIntolerance"
>;
export type ParticipantOnboardingPayload = NormalizeNullables<
  BackendParticipantOnboardingPayload,
  "constraints" | "fineTitleEntries" | "isComplete" | "lovedTitleEntries" | "noTitleEntries"
>;
export type RecentSessionSummaryPayload = NormalizeNullables<
  BackendRecentSessionSummaryPayload,
  "bestPickSourceMovieId" | "bestPickTitle" | "outcomeTitle" | "outcomeType"
>;
export type SessionOutcomePayload = NormalizeNullables<
  BackendSessionOutcomePayload,
  "notes" | "selectedSourceMovieId" | "selectedTitle" | "selectionOrigin"
>;

export type CreateSessionRequest = {
  sessionId?: string;
  householdId: string;
  activeMode: ApiSessionMode;
  participantIds: string[];
  shortlist: SessionShortlistItemPayload[];
};

export type LoadShortlistRequest = {
  sessionId: string;
  householdId: string;
  activeMode: ApiSessionMode;
  participantIds: string[];
  source?: "demo" | "live_tmdb";
  shortlistSize: number;
  availabilityRegion?: string;
  serviceConstraint?: string | null;
  tonightIntent?: TonightIntentInterpretationPayload | null;
  tonightIntents?: TonightIntentInterpretationPayload[];
  excludedSourceMovieIds?: string[];
  sessionReactions?: ScoringSessionReactionPayload[];
};

export type LoadShortlistResponse = {
  recommendationSource: "demo" | "live_tmdb" | string;
  shortlist: ShortlistCandidatePayload[];
};

export type SubmitReactionsRequest = {
  participantId: string;
  reactions: SessionReactionPayload[];
};

export function toApiSessionMode(mode: SessionMode): ApiSessionMode {
  if (mode === "founder-first") {
    return "husband_first";
  }

  if (mode === "wife-first") {
    return "wife_first";
  }

  return "compromise";
}

export async function createSharedSession(
  request: CreateSessionRequest,
): Promise<SharedSessionPayload> {
  return postJson("/api/session", request);
}

export async function continueSharedSession(
  sessionId: string,
  shortlist: SessionShortlistItemPayload[],
): Promise<SharedSessionPayload> {
  return postJson(`/api/session/${encodeURIComponent(sessionId)}/continue`, {
    shortlist,
  });
}

export async function loadRecommendationShortlist(
  request: LoadShortlistRequest,
): Promise<LoadShortlistResponse> {
  const payload = await postJson<unknown>("/api/recommendations/shortlist", request);
  const shortlist = parseShortlistPayload(payload);
  const recommendationSource = isRecord(payload)
    ? stringValue(payload.recommendationSource) ?? stringValue(payload.recommendation_source)
    : null;

  if (shortlist.length === 0) {
    throw new Error("Recommendation API returned an empty shortlist.");
  }

  return { recommendationSource: recommendationSource ?? "demo", shortlist };
}

export async function submitSessionReactions(
  sessionId: string,
  request: SubmitReactionsRequest,
): Promise<SharedSessionPayload> {
  return postJson(`/api/session/${encodeURIComponent(sessionId)}/reactions`, request);
}

export async function advanceSessionHandoff(
  sessionId: string,
): Promise<SharedSessionPayload> {
  return postJson(`/api/session/${encodeURIComponent(sessionId)}/advance-handoff`, {});
}

export async function getSessionDebugHistory(
  sessionId: string,
): Promise<DebugHistorySessionPayload> {
  return getJson(
    `/api/session/${encodeURIComponent(sessionId)}/debug-history`,
  );
}

export async function getTasteProfileSummary(
  householdId: string,
  profileId: string,
): Promise<TasteProfileSummaryPayload> {
  const query = new URLSearchParams({ householdId });
  return getJson(
    `/api/taste-profile/${encodeURIComponent(profileId)}/summary?${query.toString()}`,
  );
}

export async function getProfileMemorySummary(
  householdId: string,
  profileId: string,
): Promise<ProfileMemorySummaryPayload> {
  const query = new URLSearchParams({ householdId });
  return getJson(
    `/api/profiles/${encodeURIComponent(profileId)}/memory?${query.toString()}`,
  );
}

export async function getProfileMemoryEvents(
  householdId: string,
  profileId: string,
): Promise<TasteMemoryEventPayload[]> {
  const query = new URLSearchParams({ householdId });
  return getJson(
    `/api/profiles/${encodeURIComponent(profileId)}/memory/events?${query.toString()}`,
  );
}

export async function interpretTonightIntent(
  text: string,
): Promise<TonightIntentInterpretationPayload> {
  return postJson("/api/tonight-intent/interpret", { text });
}

export async function interpretDirectedNudge(
  text: string,
): Promise<TonightIntentInterpretationPayload> {
  const response = await fetch("/api/tonight-intent/interpret", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text }),
    signal: AbortSignal.timeout(clientRequestTimeoutMs()),
  });

  const payload = (await response.json().catch(() => null)) as unknown;

  if (!response.ok) {
    throw new Error(parseApiError(payload, response.status));
  }

  return payload as TonightIntentInterpretationPayload;
}

export async function submitSessionOutcome(
  sessionId: string,
  request: SaveSessionOutcomeRequest,
): Promise<SessionOutcomePayload> {
  return postJson(`/api/session/${encodeURIComponent(sessionId)}/outcome`, request);
}

export async function submitPostWatchFeedback(
  request: SavePostWatchFeedbackRequest,
): Promise<PostWatchFeedbackPayload> {
  return postJson("/api/feedback/post-watch", request);
}

export async function getRecentSessions(
  householdId: string,
  limit = 6,
): Promise<RecentSessionSummaryPayload[]> {
  const query = new URLSearchParams({
    householdId,
    limit: String(limit),
  });
  return getJson(`/api/history/sessions?${query.toString()}`);
}

export async function getWatchlist(
  householdId: string,
): Promise<WatchlistEntryPayload[]> {
  const query = new URLSearchParams({ householdId });
  return getJson(`/api/watchlist?${query.toString()}`);
}

export async function saveWatchlistEntry(
  request: SaveWatchlistEntryRequest,
): Promise<WatchlistEntryPayload> {
  return postJson("/api/watchlist", request);
}

export async function removeWatchlistEntry(
  householdId: string,
  sourceMovieId: string,
): Promise<void> {
  const query = new URLSearchParams({ householdId });
  return deleteJson(
    `/api/watchlist/${encodeURIComponent(sourceMovieId)}?${query.toString()}`,
  );
}

export async function markAppOwnedMovieWatched(
  request: AppOwnedMovieWatchedRequest,
): Promise<WatchedTitleBackfillPayload[]> {
  return postJson("/api/app-owned-movies/watched", request);
}

export async function getProfileOnboarding(
  profileId: string,
): Promise<ParticipantOnboardingPayload> {
  return getJson(`/api/onboarding/${encodeURIComponent(profileId)}`);
}

export async function getOnboardingCompletion(
  requiredProfileIds: string[],
): Promise<OnboardingCompletionPayload> {
  const query = new URLSearchParams();
  requiredProfileIds.forEach((profileId) => {
    query.append("requiredProfileIds", profileId);
  });
  return getJson(`/api/onboarding/completion?${query.toString()}`);
}

export async function saveProfileOnboarding(
  profileId: string,
  request: ParticipantOnboardingPayload,
): Promise<ParticipantOnboardingPayload> {
  return putJson(`/api/onboarding/${encodeURIComponent(profileId)}`, request);
}

async function postJson<TResponse>(
  url: string,
  body: unknown,
): Promise<TResponse> {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(clientRequestTimeoutMs()),
  });

  const payload = (await response.json().catch(() => null)) as unknown;

  if (!response.ok) {
    throw new Error(parseApiError(payload, response.status));
  }

  return payload as TResponse;
}

async function putJson<TResponse>(
  url: string,
  body: unknown,
): Promise<TResponse> {
  const response = await fetch(url, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(clientRequestTimeoutMs()),
  });

  const payload = (await response.json().catch(() => null)) as unknown;

  if (!response.ok) {
    throw new Error(parseApiError(payload, response.status));
  }

  return payload as TResponse;
}

async function getJson<TResponse>(url: string): Promise<TResponse> {
  const response = await fetch(url, {
    method: "GET",
    signal: AbortSignal.timeout(clientRequestTimeoutMs()),
  });

  const payload = (await response.json().catch(() => null)) as unknown;

  if (!response.ok) {
    throw new Error(parseApiError(payload, response.status));
  }

  return payload as TResponse;
}

async function deleteJson(url: string): Promise<void> {
  const response = await fetch(url, {
    method: "DELETE",
    signal: AbortSignal.timeout(clientRequestTimeoutMs()),
  });

  if (response.ok) {
    return;
  }

  const payload = (await response.json().catch(() => null)) as unknown;
  throw new Error(parseApiError(payload, response.status));
}

function parseApiError(payload: unknown, status: number): string {
  if (
    typeof payload === "object" &&
    payload !== null &&
    "detail" in payload &&
    typeof payload.detail === "string"
  ) {
    return payload.detail;
  }

  return `Session API returned HTTP ${status}.`;
}

function clientRequestTimeoutMs(): number {
  return 45_000;
}

function parseShortlistPayload(payload: unknown): ShortlistCandidatePayload[] {
  const candidate =
    isRecord(payload) && Array.isArray(payload.shortlist)
      ? payload.shortlist
      : isRecord(payload) && Array.isArray(payload.candidates)
        ? payload.candidates
        : Array.isArray(payload)
          ? payload
          : [];

  return candidate
    .map(parseShortlistCandidate)
    .filter(
      (item): item is ShortlistCandidatePayload => item !== null,
    )
    .sort((first, second) => first.candidateRank - second.candidateRank);
}

function parseShortlistCandidate(
  candidate: unknown,
): ShortlistCandidatePayload | null {
  if (!isRecord(candidate)) {
    return null;
  }

  const sourceMovieId =
    stringValue(candidate.sourceMovieId) ??
    stringValue(candidate.source_movie_id) ??
    stringValue(candidate.id);
  const title = stringValue(candidate.title);

  if (!sourceMovieId || !title) {
    return null;
  }

  return {
    sourceMovieId,
    title,
    candidateRank:
      numberValue(candidate.candidateRank) ??
      numberValue(candidate.candidate_rank) ??
      1,
    mediaType:
      mediaTypeValue(candidate.mediaType) ??
      mediaTypeValue(candidate.media_type) ??
      undefined,
    year: numberValue(candidate.year),
    releaseYear:
      numberValue(candidate.releaseYear) ??
      numberValue(candidate.release_year),
    runtime: stringValue(candidate.runtime),
    runtimeMin:
      numberValue(candidate.runtimeMin) ??
      numberValue(candidate.runtime_min),
    genres: stringArrayValue(candidate.genres) ?? [],
    posterUrl:
      stringValue(candidate.posterUrl) ??
      stringValue(candidate.poster_url),
    overview: stringValue(candidate.overview) ?? "",
    safePickStatus:
      stringValue(candidate.safePickStatus) ??
      stringValue(candidate.safe_pick_status) ??
      "",
    availability: stringValue(candidate.availability) ?? "",
    providerNames:
      stringArrayValue(candidate.providerNames) ??
      stringArrayValue(candidate.provider_names) ??
      [],
    providerAvailability: providerAvailabilityValue(
      candidate.providerAvailability,
    ) ?? providerAvailabilityValue(candidate.provider_availability) ?? [],
    topCast:
      stringArrayValue(candidate.topCast) ??
      stringArrayValue(candidate.top_cast) ??
      undefined,
    matchedPersonNames:
      stringArrayValue(candidate.matchedPersonNames) ??
      stringArrayValue(candidate.matched_person_names) ??
      undefined,
    languageAccess:
      stringValue(candidate.languageAccess) ??
      stringValue(candidate.language_access) ??
      "",
    tone:
      stringValue(candidate.tone) ??
      stringValue(candidate.fitBucket) ??
      stringValue(candidate.fit_bucket) ??
      "",
    reason:
      stringValue(candidate.reason) ??
      stringValue(candidate.whyShort) ??
      stringValue(candidate.why_short) ??
      "",
    whyShort:
      stringValue(candidate.whyShort) ??
      stringValue(candidate.why_short) ??
      "",
    fitBucket:
      stringValue(candidate.fitBucket) ??
      stringValue(candidate.fit_bucket) ??
      "",
    groupScore:
      numberValue(candidate.groupScore) ??
      numberValue(candidate.group_score) ??
      0,
    founderScore:
      numberValue(candidate.founderScore) ??
      numberValue(candidate.founder_score),
    wifeScore:
      numberValue(candidate.wifeScore) ??
      numberValue(candidate.wife_score),
    isInterestingPick:
      typeof candidate.isInterestingPick === "boolean"
        ? candidate.isInterestingPick
        : typeof candidate.is_interesting_pick === "boolean"
          ? candidate.is_interesting_pick
          : false,
    originalLanguage:
      stringValue(candidate.originalLanguage) ??
      stringValue(candidate.original_language) ??
      "",
    spokenLanguages:
      stringArrayValue(candidate.spokenLanguages) ??
      stringArrayValue(candidate.spoken_languages) ??
      [],
    englishSubtitlesVerified:
      booleanValue(candidate.englishSubtitlesVerified) ??
      booleanValue(candidate.english_subtitles_verified) ??
      false,
    dominantPositiveEvidence:
      stringArrayValue(candidate.dominantPositiveEvidence) ??
      stringArrayValue(candidate.dominant_positive_evidence) ??
      undefined,
    dominantPenalties:
      stringArrayValue(candidate.dominantPenalties) ??
      stringArrayValue(candidate.dominant_penalties) ??
      undefined,
  };
}

function stringValue(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function numberValue(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stringArrayValue(value: unknown): string[] | null {
  if (!Array.isArray(value)) {
    return null;
  }

  return value.filter(
    (item): item is string => typeof item === "string" && item.trim().length > 0,
  );
}

function providerAvailabilityValue(
  value: unknown,
): RecommendationProviderAvailabilityPayload[] | null {
  if (!Array.isArray(value)) {
    return null;
  }

  return value
    .map((entry) => {
      if (!isRecord(entry)) {
        return null;
      }

      const providerName = stringValue(entry.providerName) ?? stringValue(entry.provider_name);
      const accessType = stringValue(entry.accessType) ?? stringValue(entry.access_type);
      const region = stringValue(entry.region);

      if (!providerName || !accessType || !region) {
        return null;
      }

      return {
        providerName,
        accessType,
        region,
      };
    })
    .filter(
      (entry): entry is RecommendationProviderAvailabilityPayload => entry !== null,
    );
}

function mediaTypeValue(value: unknown): "movie" | "tv" | null {
  return value === "movie" || value === "tv" ? value : null;
}

function booleanValue(value: unknown): boolean | null {
  return typeof value === "boolean" ? value : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
