"use client";

import type { ReactionValue, SessionMode } from "./session-fixtures";

export type ApiSessionMode = "compromise" | "husband_first" | "wife_first";

export type SharedSessionPayload = {
  sessionId: string;
  householdId: string;
  activeMode: ApiSessionMode;
  participantIds: string[];
  state: "founder_reacting" | "handoff" | "wife_reacting" | "reranked";
  shortlist: SessionShortlistItemPayload[];
  founderReactions: SessionReactionPayload[];
  wifeReactions: SessionReactionPayload[];
  previousShortlist: SessionShortlistItemPayload[];
  previousFounderReactions: SessionReactionPayload[];
  previousWifeReactions: SessionReactionPayload[];
  shownSourceMovieIds: string[];
  batchCount: number;
  rerankedSourceMovieIds: string[];
  bestPickSourceMovieId: string | null;
};

export type SessionShortlistItemPayload = {
  sourceMovieId: string;
  title: string;
  candidateRank: number;
};

export type ShortlistCandidatePayload = SessionShortlistItemPayload & {
  year?: number | null;
  releaseYear?: number | null;
  runtime?: string | null;
  runtimeMin?: number | null;
  genres?: string[];
  posterUrl?: string | null;
  safePickStatus?: string | null;
  availability?: string | null;
  providerNames?: string[];
  topCast?: string[];
  languageAccess?: string | null;
  tone?: string | null;
  reason?: string | null;
  whyShort?: string | null;
  fitBucket?: string | null;
  groupScore?: number | null;
  founderScore?: number | null;
  wifeScore?: number | null;
  isInterestingPick?: boolean | null;
};

export type SessionReactionPayload = {
  sourceMovieId: string;
  reactionLabel: ReactionValue;
};

export type TitleResolutionCandidatePayload = {
  source: string;
  sourceId: string;
  title: string;
  mediaType: "movie" | "tv";
  releaseYear?: number | null;
  overview?: string;
  originalLanguage?: string | null;
  popularity?: number | null;
};

export type TitleResolutionEntryPayload = {
  rawTitle: string;
  status: "resolved" | "unresolved";
  candidate?: TitleResolutionCandidatePayload | null;
  unresolvedReason?: string | null;
};

export type WatchedTitleBackfillPayload = {
  householdId: string;
  scope: "participant" | "global";
  participantId?: string | null;
  titleKey: string;
  rawTitle: string;
  status: "resolved" | "unresolved";
  candidate?: TitleResolutionCandidatePayload | null;
  unresolvedReason?: string | null;
  watchedOn?: string | null;
  watched: boolean;
  tasteLabel?: "loved" | "fine" | "no" | null;
};

export type OnboardingConstraintsPayload = {
  horrorExclusion: boolean;
  subtitleIntolerance: boolean;
};

export type ParticipantOnboardingPayload = {
  profileId: string;
  lovedTitleEntries: TitleResolutionEntryPayload[];
  fineTitleEntries: TitleResolutionEntryPayload[];
  noTitleEntries: TitleResolutionEntryPayload[];
  constraints: OnboardingConstraintsPayload;
  isComplete: boolean;
};

export type OnboardingCompletionPayload = {
  requiredProfileIds: string[];
  completedProfileIds: string[];
  incompleteProfileIds: string[];
  sharedRecommendationLocked: boolean;
  sharedRecommendationUnlocked: boolean;
};

export type SessionOutcomeType =
  | "watched_recommended"
  | "watched_other"
  | "watched_nothing";

export type OutcomeSelectionOrigin =
  | "pick_for_us"
  | "reranked_shortlist"
  | "manual_other_choice";

export type SessionOutcomePayload = {
  sessionId: string;
  outcomeType: SessionOutcomeType;
  selectedSourceMovieId?: string | null;
  selectedTitle?: string | null;
  selectionOrigin?: OutcomeSelectionOrigin | null;
  notes?: string | null;
};

export type SaveSessionOutcomeRequest = {
  householdId: string;
  outcomeType: SessionOutcomeType;
  selectedSourceMovieId?: string | null;
  selectedTitle?: string | null;
  selectionOrigin?: OutcomeSelectionOrigin | null;
  notes?: string | null;
};

export type SavePostWatchFeedbackRequest = {
  householdId: string;
  sessionId: string;
  userId: string;
  sourceMovieId: string;
  feedbackLabel: "loved" | "fine" | "no";
  freeTextNote?: string | null;
};

export type PostWatchFeedbackPayload = {
  sessionId: string;
  userId: string;
  sourceMovieId: string;
  feedbackLabel: "loved" | "fine" | "no";
  freeTextNote?: string | null;
};

export type WatchlistEntryPayload = {
  householdId: string;
  sourceMovieId: string;
  title: string;
  savedAt: string;
  savedByProfileId?: string | null;
  posterUrl?: string | null;
  releaseYear?: number | null;
  isTasteSignal: boolean;
};

export type SaveWatchlistEntryRequest = {
  householdId: string;
  sourceMovieId: string;
  title: string;
  savedByProfileId?: string | null;
  posterUrl?: string | null;
  releaseYear?: number | null;
};

export type AppOwnedMovieRatingRequest = {
  profileId: string;
  tasteLabel: "loved" | "fine" | "no";
};

export type AppOwnedMovieWatchedRequest = {
  householdId: string;
  sourceMovieId: string;
  title: string;
  watchedOn?: string | null;
  ratings: AppOwnedMovieRatingRequest[];
};

export type RecentSessionFeedbackPayload = {
  userId: string;
  feedbackLabel: string;
};

export type RecentSessionSummaryPayload = {
  sessionId: string;
  activeMode: string;
  state: string;
  participantIds: string[];
  bestPickSourceMovieId: string | null;
  bestPickTitle: string | null;
  outcomeType: string | null;
  outcomeTitle: string | null;
  feedback: RecentSessionFeedbackPayload[];
};

export type DebugHistorySessionPayload = {
  sessionId: string;
  householdId: string;
  activeMode: ApiSessionMode;
  state: string;
  participantIds: string[];
  shortlist: SessionShortlistItemPayload[];
  previousShortlist: SessionShortlistItemPayload[];
  founderReactions: DebugHistoryReactionPayload[];
  wifeReactions: DebugHistoryReactionPayload[];
  previousFounderReactions: DebugHistoryReactionPayload[];
  previousWifeReactions: DebugHistoryReactionPayload[];
  shownSourceMovieIds: string[];
  batchCount: number;
  rerankedSourceMovieIds: string[];
  bestPickSourceMovieId: string | null;
  sessionOutcome: DebugHistoryOutcomePayload | null;
  postWatchFeedback: DebugHistoryFeedbackPayload[];
  recommendationSnapshot: DebugHistoryRecommendationSnapshotPayload | null;
  unavailableEvidence: string[];
};

export type DebugHistoryReactionPayload = {
  participantId: string;
  sourceMovieId: string;
  reactionLabel: string;
};

export type DebugHistoryFeedbackPayload = {
  userId: string;
  sourceMovieId: string;
  feedbackLabel: string;
  hasFreeTextNote: boolean;
};

export type DebugHistoryOutcomePayload = {
  outcomeType: string;
  selectedSourceMovieId: string | null;
  selectedTitle: string | null;
  selectionOrigin: string | null;
  hasNotes: boolean;
};

export type DebugHistoryUserScorePayload = {
  userId: string;
  score: number;
};

export type DebugHistoryCandidateInputPayload = {
  sourceMovieId: string;
  title: string;
  genres: string[];
  providers: string[];
  providerAccess: string[];
  safetyStatus: string;
  alreadyWatched: boolean;
  isInterestingSafePick: boolean;
};

export type DebugHistoryRecommendationCandidatePayload = {
  sourceMovieId: string;
  title: string;
  candidateRank: number;
  fitBucket: string;
  groupScore: number;
  userScores: DebugHistoryUserScorePayload[];
  whyShort: string;
  hardFilterPass: boolean;
  isInterestingPick: boolean;
};

export type DebugHistoryRecommendationSnapshotPayload = {
  sessionId: string;
  candidateInputs: DebugHistoryCandidateInputPayload[];
  candidates: DebugHistoryRecommendationCandidatePayload[];
  isUncertain: boolean;
  uncertaintyReason: string | null;
  recommendedFollowUp: string | null;
  interestingSafePickId: string | null;
};

export type TasteGenreSignalPayload = {
  genre: string;
  positiveCount: number;
  neutralCount: number;
  negativeCount: number;
  score: number;
};

export type TasteProfileSummaryPayload = {
  householdId: string;
  profileId: string;
  ratingCount: number;
  preferenceEvidenceCount: number;
  familiarityOnlyCount: number;
  genreSignals: TasteGenreSignalPayload[];
};

export type ProfileMemorySignalPayload = {
  label: string;
  count: number;
  source: "visible_app_memory" | "private_calibration" | string;
};

export type ProfileMemorySummaryPayload = {
  householdId: string;
  profileId: string;
  sharedSavedCount: number;
  savedByProfileCount: number;
  recentReactionCount: number;
  watchedCount: number;
  ratedCount: number;
  visibleAppMemoryCount: number;
  privateCalibrationCount: number;
  signals: ProfileMemorySignalPayload[];
};

export type TonightIntentInterpretationPayload = {
  rawText: string;
  status: "confirmation_required" | "clarification_required";
  confirmationText?: string | null;
  clarificationQuestion?: string | null;
  filters: Record<string, unknown>;
  softSignals: string[];
  confidence: string;
};

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
  shortlistSize: number;
  tonightIntent?: TonightIntentInterpretationPayload | null;
  tonightIntents?: TonightIntentInterpretationPayload[];
  excludedSourceMovieIds?: string[];
};

export type LoadShortlistResponse = {
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

  if (shortlist.length === 0) {
    throw new Error("Recommendation API returned an empty shortlist.");
  }

  return { shortlist };
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

export async function interpretTonightIntent(
  text: string,
): Promise<TonightIntentInterpretationPayload> {
  return postJson("/api/tonight-intent/interpret", { text });
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
    year: numberValue(candidate.year),
    releaseYear:
      numberValue(candidate.releaseYear) ??
      numberValue(candidate.release_year),
    runtime: stringValue(candidate.runtime),
    runtimeMin:
      numberValue(candidate.runtimeMin) ??
      numberValue(candidate.runtime_min),
    genres: stringArrayValue(candidate.genres),
    posterUrl:
      stringValue(candidate.posterUrl) ??
      stringValue(candidate.poster_url),
    safePickStatus:
      stringValue(candidate.safePickStatus) ??
      stringValue(candidate.safe_pick_status),
    availability: stringValue(candidate.availability),
    providerNames: stringArrayValue(candidate.providerNames),
    topCast:
      stringArrayValue(candidate.topCast) ||
      stringArrayValue(candidate.top_cast),
    languageAccess:
      stringValue(candidate.languageAccess) ??
      stringValue(candidate.language_access),
    tone: stringValue(candidate.tone) ?? stringValue(candidate.fitBucket),
    reason:
      stringValue(candidate.reason) ??
      stringValue(candidate.whyShort) ??
      stringValue(candidate.why_short),
    whyShort: stringValue(candidate.whyShort),
    fitBucket:
      stringValue(candidate.fitBucket) ??
      stringValue(candidate.fit_bucket),
    groupScore:
      numberValue(candidate.groupScore) ??
      numberValue(candidate.group_score),
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
          : null,
  };
}

function stringValue(value: unknown): string | null {
  return typeof value === "string" && value.trim().length > 0 ? value : null;
}

function numberValue(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stringArrayValue(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value.filter(
    (item): item is string => typeof item === "string" && item.trim().length > 0,
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
