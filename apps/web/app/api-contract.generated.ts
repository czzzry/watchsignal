// Generated from FastAPI OpenAPI components.
// Do not edit by hand. Regenerate with:
// cd apps/api && ../../.tools/uv/bin/uv run python -m movie_night_mediator.api.generate_typescript_contract

export type AppOwnedMovieRatingPayload = {
  profileId: string;
  tasteLabel: SeedPreferenceLabel;
};

export type AppOwnedMovieWatchedPayload = {
  householdId?: string;
  ratings?: AppOwnedMovieRatingPayload[];
  sourceMovieId: string;
  title: string;
  watchedOn?: string | null;
};

export type BackfillWatchedTitlePayload = {
  entry: TitleResolutionEntryPayload;
  householdId?: string;
  includeGlobal?: boolean;
  participantIds?: string[];
  tasteLabel?: SeedPreferenceLabel | null;
  watched?: boolean;
  watchedOn?: string | null;
};

export type ContinueSharedSessionPayload = {
  shortlist: SessionShortlistItemPayload[];
};

export type CreateSharedSessionPayload = {
  activeMode?: SessionMode;
  householdId?: string;
  participantIds: string[];
  sessionId?: string | null;
  shortlist: SessionShortlistItemPayload[];
};

export type DebugHistoryCandidateInputPayload = {
  alreadyWatched: boolean;
  enrichmentFeatureScores: {
    [key: string]: number;
  };
  enrichmentProvider: string;
  enrichmentStatus: string;
  genres: string[];
  isInterestingSafePick: boolean;
  matchedEnrichmentSourceMovieId?: string | null;
  providerAccess: string[];
  providers: string[];
  safetyStatus: string;
  sourceMovieId: string;
  title: string;
};

export type DebugHistoryEnrichmentCoveragePayload = {
  candidateCount: number;
  enrichedCandidateCount: number;
  enrichmentRate: number;
  fallbackCandidateCount: number;
};

export type DebugHistoryFeedbackPayload = {
  feedbackLabel: string;
  hasFreeTextNote: boolean;
  sourceMovieId: string;
  userId: string;
};

export type DebugHistoryOutcomePayload = {
  hasNotes: boolean;
  outcomeType: string;
  selectedSourceMovieId?: string | null;
  selectedTitle?: string | null;
  selectionOrigin?: string | null;
};

export type DebugHistoryReactionPayload = {
  participantId: string;
  reactionLabel: string;
  sourceMovieId: string;
};

export type DebugHistoryRecommendationCandidatePayload = {
  candidateRank: number;
  dominantPenalties?: string[];
  dominantPositiveEvidence?: string[];
  fitBucket: string;
  groupScore: number;
  hardFilterPass: boolean;
  isInterestingPick: boolean;
  scoringEvidence: DebugHistoryScoringEvidencePayload[];
  sourceMovieId: string;
  title: string;
  userScores: DebugHistoryUserScorePayload[];
  whyShort: string;
};

export type DebugHistoryRecommendationSnapshotPayload = {
  candidateInputs: DebugHistoryCandidateInputPayload[];
  candidates: DebugHistoryRecommendationCandidatePayload[];
  confidenceLabel?: string | null;
  confidenceScore?: number | null;
  enrichmentCoverage: DebugHistoryEnrichmentCoveragePayload;
  fallbackReason?: string | null;
  interestingSafePickId?: string | null;
  isUncertain: boolean;
  partialSupportNotes?: string[];
  recommendedFollowUp?: string | null;
  scorerVersion?: string;
  sessionId: string;
  uncertaintyReason?: string | null;
};

export type DebugHistoryScoringEvidencePayload = {
  contributions: DebugHistorySignalContributionPayload[];
  enrichmentStatus: string;
  signalFamilies: string[];
  sourceMovieId: string;
};

export type DebugHistorySessionPayload = {
  activeMode: string;
  batchCount: number;
  bestPickSourceMovieId?: string | null;
  founderReactions: DebugHistoryReactionPayload[];
  householdId: string;
  participantIds: string[];
  postWatchFeedback: DebugHistoryFeedbackPayload[];
  previousFounderReactions: DebugHistoryReactionPayload[];
  previousShortlist: DebugHistoryShortlistItemPayload[];
  previousWifeReactions: DebugHistoryReactionPayload[];
  recommendationSnapshot?: DebugHistoryRecommendationSnapshotPayload | null;
  rerankedSourceMovieIds: string[];
  sessionId: string;
  sessionOutcome?: DebugHistoryOutcomePayload | null;
  shortlist: DebugHistoryShortlistItemPayload[];
  shownSourceMovieIds: string[];
  state: string;
  unavailableEvidence: string[];
  wifeReactions: DebugHistoryReactionPayload[];
};

export type DebugHistoryShortlistItemPayload = {
  candidateRank: number;
  sourceMovieId: string;
  title: string;
};

export type DebugHistorySignalContributionPayload = {
  family: string;
  label: string;
  value: number;
};

export type DebugHistoryUserScorePayload = {
  score: number;
  userId: string;
};

export type HTTPValidationError = {
  detail?: ValidationError[];
};

export type IntentInterpretationStatus = "confirmation_required" | "clarification_required";

export type MediaType = "movie" | "tv";

export type OnboardingCompletionPayload = {
  completedProfileIds: string[];
  incompleteProfileIds: string[];
  requiredProfileIds: string[];
  sharedRecommendationLocked: boolean;
  sharedRecommendationUnlocked: boolean;
};

export type OnboardingConstraintsPayload = {
  horrorExclusion?: boolean;
  subtitleIntolerance?: boolean;
};

export type OutcomeSelectionOrigin = "pick_for_us" | "reranked_shortlist" | "manual_other_choice";

export type ParticipantOnboardingPayload = {
  constraints?: OnboardingConstraintsPayload;
  fineTitleEntries?: TitleResolutionEntryPayload[];
  isComplete?: boolean;
  lovedTitleEntries?: TitleResolutionEntryPayload[];
  noTitleEntries?: TitleResolutionEntryPayload[];
  profileId: string;
};

export type PostWatchFeedbackPayload = {
  feedbackLabel: string;
  freeTextNote?: string | null;
  householdId?: string;
  sessionId: string;
  sourceMovieId: string;
  userId: string;
};

export type PostWatchFeedbackResponsePayload = {
  feedbackLabel: string;
  freeTextNote?: string | null;
  sessionId: string;
  sourceMovieId: string;
  userId: string;
};

export type ProfileMemorySignalPayload = {
  count: number;
  label: string;
  source: string;
};

export type ProfileMemorySummaryPayload = {
  householdId: string;
  privateCalibrationCount: number;
  profileId: string;
  ratedCount: number;
  recentReactionCount: number;
  savedByProfileCount: number;
  sharedSavedCount: number;
  signals: ProfileMemorySignalPayload[];
  visibleAppMemoryCount: number;
  watchedCount: number;
};

export type RecentSessionFeedbackPayload = {
  feedbackLabel: string;
  userId: string;
};

export type RecentSessionSummaryPayload = {
  activeMode: string;
  bestPickSourceMovieId?: string | null;
  bestPickTitle?: string | null;
  feedback: RecentSessionFeedbackPayload[];
  outcomeTitle?: string | null;
  outcomeType?: string | null;
  participantIds: string[];
  sessionId: string;
  state: string;
};

export type RecommendationProviderAvailabilityPayload = {
  accessType: string;
  providerName: string;
  region: string;
};

export type RecommendationShortlistItemPayload = {
  availability: string;
  candidateRank: number;
  dominantPenalties?: string[];
  dominantPositiveEvidence?: string[];
  englishSubtitlesVerified: boolean;
  fitBucket: string;
  founderScore?: number | null;
  genres: string[];
  groupScore: number;
  isInterestingPick: boolean;
  languageAccess: string;
  matchedPersonNames?: string[];
  mediaType?: MediaType;
  originalLanguage: string;
  overview?: string;
  posterUrl?: string | null;
  providerAvailability: RecommendationProviderAvailabilityPayload[];
  providerNames: string[];
  reason: string;
  releaseYear?: number | null;
  runtime?: string | null;
  runtimeMin?: number | null;
  safePickStatus: string;
  sourceMovieId: string;
  spokenLanguages: string[];
  title: string;
  tone: string;
  topCast?: string[];
  whyShort: string;
  wifeScore?: number | null;
  year?: number | null;
};

export type RecommendationShortlistRequestPayload = {
  activeMode?: SessionMode;
  availabilityRegion?: string | null;
  excludedSourceMovieIds?: string[];
  householdId?: string;
  participantIds?: string[];
  scoringEngine?: ScoringEngineId;
  serviceConstraint?: string | null;
  sessionId: string;
  sessionReactions?: ScoringSessionReactionPayload[];
  shortlistSize?: number;
  source?: "demo" | "live_tmdb";
  tonightIntent?: {
    [key: string]: unknown;
  } | null;
  tonightIntents?: ({
    [key: string]: unknown;
  })[];
};

export type SaveSessionOutcomePayload = {
  householdId?: string;
  notes?: string | null;
  outcomeType: SessionOutcomeType;
  selectedSourceMovieId?: string | null;
  selectedTitle?: string | null;
  selectionOrigin?: OutcomeSelectionOrigin | null;
};

export type SaveWatchlistEntryPayload = {
  householdId?: string;
  posterUrl?: string | null;
  releaseYear?: number | null;
  savedByDisplayLabel?: string | null;
  savedByProfileId?: string | null;
  sourceMovieId: string;
  title: string;
};

export type ScoringEngineId = "v1_heuristic" | "v2_contract";

export type ScoringSessionReactionPayload = {
  reactionLabel: string;
  sourceMovieId: string;
  title?: string | null;
};

export type SeedPreferenceLabel = "loved" | "fine" | "no";

export type SessionMode = "husband_first" | "wife_first" | "compromise";

export type SessionOutcomePayload = {
  notes?: string | null;
  outcomeType: SessionOutcomeType;
  selectedSourceMovieId?: string | null;
  selectedTitle?: string | null;
  selectionOrigin?: OutcomeSelectionOrigin | null;
  sessionId: string;
};

export type SessionOutcomeType = "watched_recommended" | "watched_other" | "watched_nothing";

export type SessionReactionLabel = "interested" | "maybe" | "no" | "seen";

export type SessionReactionPayload = {
  reactionLabel: SessionReactionLabel;
  sourceMovieId: string;
};

export type SessionShortlistItemPayload = {
  candidateRank: number;
  profileScore?: number;
  sourceMovieId: string;
  title: string;
};

export type SetupDefaultsPayload = {
  availabilityRegion: string;
  avoidAlreadyWatched: boolean;
  inputMode: string;
  languageAccess: string;
  sessionType: string;
  shortlistSize: number;
};

export type SetupProfileCreatePayload = {
  label: string;
};

export type SetupProfilePayload = {
  avatarKey?: string;
  colorKey?: string;
  id: string;
  label: string;
  order: number;
};

export type SetupProfileRenamePayload = {
  label: string;
};

export type SetupStatePayload = {
  activeProfileId?: string | null;
  defaults: SetupDefaultsPayload;
  householdLabel: string;
  partnerProfileId?: string | null;
  profiles: SetupProfilePayload[];
};

export type SharedSessionPayload = {
  activeMode: SessionMode;
  batchCount: number;
  bestPickSourceMovieId?: string | null;
  founderReactions: SessionReactionPayload[];
  householdId: string;
  participantIds: string[];
  previousFounderReactions: SessionReactionPayload[];
  previousShortlist: SessionShortlistItemPayload[];
  previousWifeReactions: SessionReactionPayload[];
  rerankedShortlist: SessionShortlistItemPayload[];
  rerankedSourceMovieIds: string[];
  sessionId: string;
  shortlist: SessionShortlistItemPayload[];
  shownSourceMovieIds: string[];
  state: SharedSessionState;
  wifeReactions: SessionReactionPayload[];
};

export type SharedSessionState = "founder_reacting" | "handoff" | "wife_reacting" | "reranked";

export type SubmitSessionReactionsPayload = {
  participantId: string;
  reactions: SessionReactionPayload[];
};

export type TasteGenreSignalPayload = {
  genre: string;
  negativeCount: number;
  neutralCount: number;
  positiveCount: number;
  score: number;
};

export type TasteLabCandidatePayload = {
  movie: TasteLabMoviePayload;
  queueProvenance: TasteLabQueueProvenancePayload;
};

export type TasteLabMoviePayload = {
  genres?: string[];
  posterPath?: string | null;
  releaseYear?: number | null;
  sourceMovieId: string;
  title: string;
  tmdbId?: string | null;
};

export type TasteLabQueueProvenancePayload = {
  generatedAt?: string | null;
  queueReason?: string | null;
  queueSource: string;
  rank?: number | null;
  scoreComponents?: {
    [key: string]: number;
  };
  signalScore?: number | null;
};

export type TasteLabRatingExportPayload = {
  familiarity: string;
  householdId: string;
  isImportablePreference: boolean;
  label: TasteLabRatingLabel;
  movie: TasteLabMoviePayload;
  preferenceValue?: number | null;
  profileId: string;
  queueProvenance?: TasteLabQueueProvenancePayload | null;
  ratedAt: string;
  schemaVersion: string;
  watchsignalTasteSignal: string;
};

export type TasteLabRatingInputPayload = {
  label: TasteLabRatingLabel;
  movie: TasteLabMoviePayload;
  queueProvenance?: TasteLabQueueProvenancePayload | null;
  ratedAt?: string | null;
};

export type TasteLabRatingLabel = "loved" | "liked" | "meh" | "hated" | "havent_seen";

export type TasteLabSubmitRatingsPayload = {
  householdId?: string;
  ratings: TasteLabRatingInputPayload[];
};

export type TasteMemoryEventPayload = {
  effectLabel?: string | null;
  eventId: string;
  eventType: string;
  familiarity?: string | null;
  genres: string[];
  householdId: string;
  occurredAt: string;
  preferenceValue?: number | null;
  profileId: string;
  sentimentLabel?: string | null;
  source: string;
  sourceMovieId: string;
  status: string;
  title: string;
};

export type TasteProfileEvidencePayload = {
  familiarity: string;
  genres: string[];
  householdId: string;
  isPreferenceEvidence: boolean;
  label: string;
  preferenceValue?: number | null;
  profileId: string;
  queueProvenance?: TasteLabQueueProvenancePayload | null;
  ratedAt: string;
  releaseYear?: number | null;
  source: string;
  sourceMovieId: string;
  title: string;
  tmdbId?: string | null;
  watchsignalTasteSignal: string;
};

export type TasteProfileSummaryPayload = {
  evidence: TasteProfileEvidencePayload[];
  familiarityOnlyCount: number;
  genreSignals: TasteGenreSignalPayload[];
  householdId: string;
  preferenceEvidenceCount: number;
  profileId: string;
  ratingCount: number;
};

export type TitleResolutionCandidatePayload = {
  mediaType?: MediaType;
  originalLanguage?: string | null;
  overview?: string;
  popularity?: number | null;
  releaseYear?: number | null;
  source: string;
  sourceId: string;
  title: string;
};

export type TitleResolutionEntryPayload = {
  candidate?: TitleResolutionCandidatePayload | null;
  rawTitle: string;
  status: TitleResolutionStatus;
  unresolvedReason?: string | null;
};

export type TitleResolutionStatus = "resolved" | "unresolved";

export type TonightIntentInterpretRequestPayload = {
  text: string;
};

export type TonightIntentInterpretationPayload = {
  clarificationQuestion?: string | null;
  confidence: string;
  confirmationText?: string | null;
  excludedSignals?: string[];
  filters: {
    [key: string]: unknown;
  };
  rawText: string;
  resolution?: "exact" | "guess" | "unsupported";
  softSignals: string[];
  status: IntentInterpretationStatus;
  unsupportedReason?: string | null;
};

export type UpdateSharedSessionPayload = {
  activeMode: SessionMode;
};

export type ValidationError = {
  ctx?: Record<string, unknown>;
  input?: unknown;
  loc: (string | number)[];
  msg: string;
  type: string;
};

export type WatchedStatusScope = "participant" | "global";

export type WatchedTitleBackfillPayload = {
  candidate?: TitleResolutionCandidatePayload | null;
  householdId: string;
  participantId?: string | null;
  rawTitle: string;
  scope: WatchedStatusScope;
  status: TitleResolutionStatus;
  tasteLabel?: SeedPreferenceLabel | null;
  titleKey: string;
  unresolvedReason?: string | null;
  watched: boolean;
  watchedOn?: string | null;
};

export type WatchlistEntryPayload = {
  canBeRecommendationSeed?: boolean;
  householdId: string;
  isTasteSignal?: boolean;
  posterUrl?: string | null;
  releaseYear?: number | null;
  savedAt: string;
  savedByDisplayLabel?: string | null;
  savedByProfileId?: string | null;
  sourceMovieId: string;
  title: string;
};
