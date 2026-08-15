import type { DemoCandidate, SessionMode } from "../session-fixtures";
import type {
  CandidateViewModel,
  PeopleMode,
  ReactionState,
  SeenMemoryValue,
} from "../pass-the-phone-model";
import {
  advanceSessionHandoff,
  appliedTonightIntentForTransport,
  createSharedSession,
  continueSharedSession,
  getProfileOnboarding,
  loadRecommendationShortlist,
  saveProfileOnboarding,
  submitSessionReactions,
  toApiSessionMode,
  type SharedSessionPayload,
  type TonightIntentInterpretationPayload,
} from "../session-client.ts";
import {
  createSessionId,
  mergeSeenMemoryIntoOnboarding,
  reactionsPayload,
  toSessionCandidate,
} from "../pass-the-phone-helpers.ts";
import {
  continuationExcludedSourceMovieIds,
  latestTonightIntent,
  scoringReactionSignals,
  scoringReactionSignalsFromLocal,
  sessionShortlistFromCandidates,
} from "./session-control.ts";
import type { SeenMemorySaveResult } from "./seen-memory-contract";
import {
  exactUsableShortlist,
  liveLocalShortlistNotice,
  localShortlistNotice,
  publicShortlistFailure,
  REQUIRED_SHORTLIST_SIZE,
  savedFallbackShortlistNotice,
  selectExactUsableShortlist,
  type ShortlistGenerationOutcome,
  type ShortlistGenerationStage,
} from "./shortlist-generation-contract.ts";
import { publicContinuationFailure } from "./continuation-steer-contract.ts";
import { publicErrorMessage } from "./public-error-message.ts";

type SessionUpdate = {
  sharedSession?: SharedSessionPayload | null;
  liveSessionId?: string | null;
  shownSourceMovieIds?: string[];
  recommendationSource?: string;
  sessionSource?: "api" | "demo";
  movieSource?: "live" | "local";
  persistenceSource?: "shared" | "local";
  apiError?: string | null;
};

type ResultsUpdate = {
  debugHistory?: null;
  debugHistoryStatus?: "idle";
  debugHistoryMessage?: null;
};

export type SessionLifecyclePorts = {
  resetBatch: (candidates?: CandidateViewModel[]) => void;
  resetSessionProgress: () => void;
  updateSession: (updates: SessionUpdate) => void;
  updateResults: (updates: ResultsUpdate) => void;
  startSessionSync: (status: "loading" | "saving") => void;
  finishSessionSync: () => void;
  navigateToStarted: () => void;
  addShownMovieIds: (sourceMovieIds: string[]) => void;
  archiveLocalReactionHistory?: () => void;
  loadTasteProfileSummaries: (
    session: SharedSessionPayload,
    trigger: "couple-session" | "continuation",
  ) => Promise<void>;
  loadSoloTasteProfileSummaries: (
    householdId: string,
    participantIds: string[],
  ) => Promise<void>;
  updateShortlistStage?: (stage: ShortlistGenerationStage) => void;
};

export type SessionLifecycleDependencies = {
  createId: () => string;
  loadShortlist: typeof loadRecommendationShortlist;
  createSession: typeof createSharedSession;
  continueSession: typeof continueSharedSession;
};

const defaultDependencies: SessionLifecycleDependencies = {
  createId: createSessionId,
  loadShortlist: loadRecommendationShortlist,
  createSession: createSharedSession,
  continueSession: continueSharedSession,
};

export type StartSessionInput = {
  apiConnected: boolean;
  isCoupleSession: boolean;
  sessionMode: SessionMode;
  participantIds: string[];
  shortlistSize: number;
  availabilityRegion: string;
  activeTonightIntent: TonightIntentInterpretationPayload | null;
  activeTonightIntents: TonightIntentInterpretationPayload[];
  fallbackCandidates: CandidateViewModel[];
  disconnectedMessage: string;
  sharedPersistenceAvailable?: boolean;
};

export async function startPassThePhoneSession(
  input: StartSessionInput,
  ports: SessionLifecyclePorts,
  dependencies: SessionLifecycleDependencies = defaultDependencies,
): Promise<ShortlistGenerationOutcome> {
  ports.resetBatch();
  ports.resetSessionProgress();

  if (input.shortlistSize !== REQUIRED_SHORTLIST_SIZE) {
    const message = publicShortlistFailure();
    ports.updateSession({ apiError: message });
    ports.updateShortlistStage?.("failed");
    return { status: "failed", message };
  }

  if (!input.apiConnected) {
    ports.updateShortlistStage?.("local");
    const fallbackCandidates = selectExactUsableShortlist(input.fallbackCandidates);
    if (!fallbackCandidates) {
      const message = publicShortlistFailure();
      ports.updateSession({ apiError: message });
      ports.updateShortlistStage?.("failed");
      return { status: "failed", message };
    }
    ports.resetBatch(fallbackCandidates);
    ports.updateSession({
      sessionSource: "demo",
      movieSource: "local",
      persistenceSource: "local",
      recommendationSource: "demo",
      shownSourceMovieIds: fallbackCandidates.map((candidate) => candidate.id),
      apiError: localShortlistNotice(),
    });
    ports.navigateToStarted();
    return {
      status: "ready",
      movieSource: "local",
      persistenceSource: "local",
    };
  }

  ports.startSessionSync("loading");
  ports.updateShortlistStage?.("finding");

  try {
    const sessionId = dependencies.createId();
    const shortlistResponse = await dependencies.loadShortlist({
      sessionId,
      householdId: "default-household",
      activeMode: toApiSessionMode(input.sessionMode),
      participantIds: input.participantIds,
      source: "live_tmdb",
      shortlistSize: input.shortlistSize,
      availabilityRegion: input.availabilityRegion,
      serviceConstraint: serviceConstraintFromAvailability(input.availabilityRegion),
      tonightIntent: input.activeTonightIntent
        ? appliedTonightIntentForTransport(input.activeTonightIntent)
        : null,
      tonightIntents: input.activeTonightIntents.map(appliedTonightIntentForTransport),
    });
    ports.updateShortlistStage?.("checking");
    const candidates = exactUsableShortlist(
      shortlistResponse.shortlist.map(toSessionCandidate),
    );
    ports.updateSession({
      recommendationSource: shortlistResponse.recommendationSource,
    });

    if (!candidates) {
      throw new Error(publicShortlistFailure());
    }

    ports.resetBatch(candidates);
    ports.updateSession({
      shownSourceMovieIds: candidates.map((candidate) => candidate.id),
    });

    let persistenceSource: "shared" | "local" = "local";
    if (input.isCoupleSession) {
      ports.updateShortlistStage?.("preparing");
      persistenceSource = await createCoupleSession({
        sessionId,
        candidates,
        input,
        ports,
        dependencies,
      });
    } else {
      ports.updateSession({
        sharedSession: null,
        liveSessionId: sessionId,
        sessionSource: "api",
        movieSource: "live",
        persistenceSource: "local",
        apiError: liveLocalShortlistNotice(),
      });
      await ports.loadSoloTasteProfileSummaries(
        "default-household",
        input.participantIds,
      );
    }
    if (persistenceSource === "shared") {
      ports.updateSession({ apiError: null });
    }
    ports.navigateToStarted();
    return {
      status: "ready",
      movieSource: "live",
      persistenceSource,
    };
  } catch (error) {
    return recoverWithFallbackCandidates(error, input, ports, dependencies);
  } finally {
    ports.finishSessionSync();
  }
}

type ContinueSessionInput = {
  apiConnected: boolean;
  sessionMode: SessionMode;
  participantIds: string[];
  shortlistSize: number;
  availabilityRegion: string;
  sessionSource: "api" | "demo";
  movieSource?: "live" | "local";
  persistenceSource?: "shared" | "local";
  sharedSession: SharedSessionPayload | null;
  liveSessionId: string | null;
  shownSourceMovieIds: string[];
  sessionCandidates: CandidateViewModel[];
  fallbackCandidates: CandidateViewModel[];
  firstPassActor: "founder" | "wife";
  founderReactions: ReactionState;
  wifeReactions: ReactionState;
  localReactionHistory?: ReturnType<typeof scoringReactionSignalsFromLocal>;
  tonightIntents: TonightIntentInterpretationPayload[];
};

export async function continuePassThePhoneSession(
  input: ContinueSessionInput,
  ports: SessionLifecyclePorts,
  dependencies: SessionLifecycleDependencies = defaultDependencies,
): Promise<void> {
  ports.updateSession({ apiError: null });
  const movieSource = input.movieSource ?? (input.sessionSource === "api" ? "live" : "local");
  const persistenceSource = input.persistenceSource ?? (input.sharedSession ? "shared" : "local");
  if (!input.apiConnected || movieSource !== "live") {
    const candidates = localContinuationCandidates({
      catalog: input.fallbackCandidates,
      shownSourceMovieIds: input.shownSourceMovieIds,
      currentCandidates: input.sessionCandidates,
      shortlistSize: input.shortlistSize,
    });

    if (candidates.length === input.shortlistSize) {
      ports.updateResults({
        debugHistory: null,
        debugHistoryStatus: "idle",
        debugHistoryMessage: null,
      });
      ports.addShownMovieIds(candidates.map((candidate) => candidate.id));
      ports.updateSession({
        recommendationSource: "demo",
        movieSource: "local",
        persistenceSource: "local",
        apiError: "Using five built-in picks. This round stays on this phone.",
      });
      ports.archiveLocalReactionHistory?.();
      ports.resetBatch(candidates);
      ports.navigateToStarted();
      return;
    }

    ports.updateSession({
      apiError: "No more picks are available right now. Try again when you’re online.",
    });
    return;
  }

  ports.startSessionSync("loading");
  ports.updateResults({
    debugHistory: null,
    debugHistoryStatus: "idle",
    debugHistoryMessage: null,
  });

  try {
    const shortlistResponse = await dependencies.loadShortlist({
      sessionId:
        input.sharedSession?.sessionId ??
        input.liveSessionId ??
        dependencies.createId(),
      householdId: input.sharedSession?.householdId ?? "default-household",
      activeMode: toApiSessionMode(input.sessionMode),
      participantIds: input.participantIds,
      source: "live_tmdb",
      shortlistSize: input.shortlistSize,
      availabilityRegion: input.availabilityRegion,
      serviceConstraint: serviceConstraintFromAvailability(input.availabilityRegion),
      tonightIntent: latestTonightIntent(input.tonightIntents)
        ? appliedTonightIntentForTransport(latestTonightIntent(input.tonightIntents)!)
        : null,
      tonightIntents: input.tonightIntents.map(appliedTonightIntentForTransport),
      excludedSourceMovieIds: excludedMovieIds(input),
      sessionReactions: reactionSignals(input, dependencies),
    });
    const excluded = excludedMovieIds(input);
    const candidates = exactUsableShortlist(
      shortlistResponse.shortlist.map(toSessionCandidate),
      excluded,
    );
    ports.updateSession({
      recommendationSource: shortlistResponse.recommendationSource,
    });

    if (!candidates) {
      throw new Error("We couldn’t make five fresh picks. Your earlier choices are still here.");
    }

    if (input.sharedSession !== null) {
      const continuedSession = await dependencies.continueSession(
        input.sharedSession.sessionId,
        sessionShortlistFromCandidates(candidates),
      );
      ports.updateSession({ sharedSession: continuedSession });
      await ports.loadTasteProfileSummaries(continuedSession, "continuation");
    } else {
      ports.addShownMovieIds(candidates.map((candidate) => candidate.id));
      ports.archiveLocalReactionHistory?.();
    }

    ports.resetBatch(candidates);
    ports.updateSession({
      movieSource: "live",
      apiError:
        persistenceSource === "local"
          ? liveLocalShortlistNotice()
          : null,
    });
    ports.navigateToStarted();
  } catch (error) {
    ports.updateSession({ apiError: publicContinuationFailure() });
  } finally {
    ports.finishSessionSync();
  }
}

export function localContinuationCandidates({
  catalog,
  shownSourceMovieIds,
  currentCandidates,
  shortlistSize,
}: {
  catalog: CandidateViewModel[];
  shownSourceMovieIds: string[];
  currentCandidates: CandidateViewModel[];
  shortlistSize: number;
}): CandidateViewModel[] {
  const excludedIds = new Set([
    ...shownSourceMovieIds,
    ...currentCandidates.map((candidate) => candidate.id),
  ]);

  return catalog
    .filter((candidate) => !excludedIds.has(candidate.id))
    .sort((first, second) =>
      first.baseRank === second.baseRank
        ? first.id.localeCompare(second.id)
        : first.baseRank - second.baseRank,
    )
    .slice(0, Math.max(0, shortlistSize));
}

export function canContinuePassThePhoneSession({
  apiConnected,
  movieSource,
  sessionSource,
  fallbackCandidates,
  shownSourceMovieIds,
  sessionCandidates,
  shortlistSize,
}: Pick<
  ContinueSessionInput,
  | "apiConnected"
  | "movieSource"
  | "sessionSource"
  | "fallbackCandidates"
  | "shownSourceMovieIds"
  | "sessionCandidates"
  | "shortlistSize"
>): boolean {
  if (apiConnected && (movieSource ?? (sessionSource === "api" ? "live" : "local")) === "live") {
    return true;
  }

  return localContinuationCandidates({
    catalog: fallbackCandidates,
    shownSourceMovieIds,
    currentCandidates: sessionCandidates,
    shortlistSize,
  }).length === shortlistSize;
}

async function createCoupleSession({
  sessionId,
  candidates,
  input,
  ports,
  dependencies,
}: {
  sessionId: string;
  candidates: CandidateViewModel[];
  input: StartSessionInput;
  ports: SessionLifecyclePorts;
  dependencies: SessionLifecycleDependencies;
}): Promise<"shared" | "local"> {
  if (input.sharedPersistenceAvailable === false) {
    ports.updateSession({
      sharedSession: null,
      liveSessionId: sessionId,
      sessionSource: "api",
      movieSource: "live",
      persistenceSource: "local",
      apiError: liveLocalShortlistNotice(),
    });
    return "local";
  }

  try {
    const session = await dependencies.createSession({
      sessionId,
      householdId: "default-household",
      activeMode: toApiSessionMode(input.sessionMode),
      participantIds: input.participantIds,
      shortlist: sessionShortlistFromCandidates(candidates),
    });
    ports.updateSession({
      sharedSession: session,
      liveSessionId: null,
      sessionSource: "api",
      movieSource: "live",
      persistenceSource: "shared",
    });
    await ports.loadTasteProfileSummaries(session, "couple-session");
    return "shared";
  } catch (error) {
    ports.updateSession({
      sharedSession: null,
      liveSessionId: sessionId,
      sessionSource: "api",
      movieSource: "live",
      persistenceSource: "local",
      apiError: liveLocalShortlistNotice(),
    });
    return "local";
  }
}

async function recoverWithFallbackCandidates(
  error: unknown,
  input: StartSessionInput,
  ports: SessionLifecyclePorts,
  dependencies: SessionLifecycleDependencies,
): Promise<ShortlistGenerationOutcome> {
  ports.updateShortlistStage?.("local");
  const fallbackSessionId = dependencies.createId();
  const fallbackCandidates = selectExactUsableShortlist(input.fallbackCandidates);
  if (!fallbackCandidates) {
    const message = publicShortlistFailure();
    ports.resetBatch();
    ports.updateSession({ apiError: message });
    ports.updateShortlistStage?.("failed");
    return { status: "failed", message };
  }
  ports.resetBatch(fallbackCandidates);
  ports.updateSession({
    sharedSession: null,
    liveSessionId: input.isCoupleSession ? null : fallbackSessionId,
    shownSourceMovieIds: fallbackCandidates.map((candidate) => candidate.id),
    recommendationSource: "demo",
    movieSource: "local",
    persistenceSource: "local",
    sessionSource: input.isCoupleSession ? "demo" : "api",
    apiError: localShortlistNotice(),
  });
  ports.updateResults({
    debugHistoryStatus: "idle",
    debugHistoryMessage: null,
  });

  if (!input.isCoupleSession) {
    ports.navigateToStarted();
    return {
      status: "ready",
      movieSource: "local",
      persistenceSource: "local",
    };
  }

  let fallbackPersistenceSource: "shared" | "local" = "local";
  try {
    const fallbackSession = await dependencies.createSession({
      sessionId: fallbackSessionId,
      householdId: "default-household",
      activeMode: toApiSessionMode(input.sessionMode),
      participantIds: input.participantIds,
      shortlist: sessionShortlistFromCandidates(fallbackCandidates),
    });
    ports.updateSession({
      sharedSession: fallbackSession,
      liveSessionId: null,
      sessionSource: "api",
      movieSource: "local",
      persistenceSource: "shared",
      apiError: savedFallbackShortlistNotice(),
    });
    await ports.loadTasteProfileSummaries(fallbackSession, "couple-session");
    fallbackPersistenceSource = "shared";
  } catch (sessionError) {
    ports.updateSession({
      apiError: localShortlistNotice(),
    });
  }
  ports.navigateToStarted();
  return {
    status: "ready",
    movieSource: "local",
    persistenceSource: fallbackPersistenceSource,
  };
}

function excludedMovieIds(input: ContinueSessionInput): string[] {
  if (input.sharedSession !== null) {
    return continuationExcludedSourceMovieIds(
      input.sharedSession,
      input.sessionCandidates,
    );
  }

  return Array.from(
    new Set([
      ...input.shownSourceMovieIds,
      ...input.sessionCandidates.map((candidate) => candidate.id),
    ]),
  );
}

function reactionSignals(
  input: ContinueSessionInput,
  dependencies: SessionLifecycleDependencies,
) {
  if (input.sharedSession !== null) {
    return scoringReactionSignals(input.sharedSession);
  }

  const current = scoringReactionSignalsFromLocal({
    sessionId: input.liveSessionId ?? dependencies.createId(),
    participantId: input.participantIds[0],
    candidates: input.sessionCandidates,
    reactions:
      input.firstPassActor === "founder"
        ? input.founderReactions
        : input.wifeReactions,
  });
  return Array.from(
    new Map(
      [...(input.localReactionHistory ?? []), ...current].map((reaction) => [
        reaction.sourceMovieId,
        reaction,
      ]),
    ).values(),
  );
}

export function serviceConstraintFromAvailability(
  availabilityRegion: string,
): string | null {
  const normalized = availabilityRegion.trim().toLowerCase();
  if (normalized.includes("any streaming") || normalized.includes("no provider")) {
    return null;
  }
  if (normalized.includes("prime")) {
    return "Prime Video";
  }
  return availabilityRegion.trim() || null;
}

type SessionProgressPorts = Pick<
  SessionLifecyclePorts,
  "startSessionSync" | "finishSessionSync" | "updateSession"
> & {
  setDemoDebugFallback: () => void;
  completeHandoff: () => void;
};

type SessionProgressDependencies = {
  getOnboarding: typeof getProfileOnboarding;
  saveOnboarding: typeof saveProfileOnboarding;
  submitReactions: typeof submitSessionReactions;
  advanceHandoff: typeof advanceSessionHandoff;
};

type SeenMemoryPersistenceInput = {
  apiConnected: boolean;
  peopleMode: PeopleMode;
  participantIds: string[];
  actor: "founder" | "wife";
  candidate: DemoCandidate;
  memory: SeenMemoryValue;
};

export type SeenMemoryConfirmation = {
  actor: "founder" | "wife";
  candidateId: string;
  memory: SeenMemoryValue;
  persistence: "saved" | "local-only";
};

const defaultProgressDependencies: SessionProgressDependencies = {
  getOnboarding: getProfileOnboarding,
  saveOnboarding: saveProfileOnboarding,
  submitReactions: submitSessionReactions,
  advanceHandoff: advanceSessionHandoff,
};

export function participantIdForActor(
  peopleMode: PeopleMode,
  participantIds: string[],
  actor: "founder" | "wife",
): string | null {
  if (peopleMode === "couple") {
    return actor === "founder" ? participantIds[0] ?? null : participantIds[1] ?? null;
  }

  if (peopleMode === "founder") {
    return actor === "founder" ? participantIds[0] ?? null : null;
  }

  return actor === "wife" ? participantIds[0] ?? null : null;
}

export async function persistSeenMemory(
  input: SeenMemoryPersistenceInput,
  ports: Pick<
    SessionProgressPorts,
    "startSessionSync" | "finishSessionSync" | "updateSession"
  >,
  dependencies: SessionProgressDependencies = defaultProgressDependencies,
): Promise<SeenMemorySaveResult> {
  const profileId = participantIdForActor(
    input.peopleMode,
    input.participantIds,
    input.actor,
  );
  if (!profileId) {
    const message = "This memory couldn’t be matched to the current person.";
    ports.updateSession({ apiError: message });
    return { status: "failed", message };
  }

  if (!input.apiConnected) {
    return { status: "local-only" };
  }

  ports.startSessionSync("saving");
  try {
    const onboarding = await dependencies.getOnboarding(profileId);
    await dependencies.saveOnboarding(
      profileId,
      mergeSeenMemoryIntoOnboarding(onboarding, input.candidate, input.memory),
    );
    return { status: "saved" };
  } catch (error) {
    const message = publicErrorMessage("seen-memory-save", error);
    ports.updateSession({ apiError: message });
    return {
      status: "failed",
      message,
    };
  } finally {
    ports.finishSessionSync();
  }
}

export async function commitSeenMemory(
  input: SeenMemoryPersistenceInput,
  ports: Pick<
    SessionProgressPorts,
    "startSessionSync" | "finishSessionSync" | "updateSession"
  >,
  onConfirmed: (confirmation: SeenMemoryConfirmation) => void,
  dependencies: SessionProgressDependencies = defaultProgressDependencies,
): Promise<SeenMemorySaveResult> {
  const result = await persistSeenMemory(input, ports, dependencies);
  if (result.status !== "failed") {
    onConfirmed({
      actor: input.actor,
      candidateId: input.candidate.id,
      memory: input.memory,
      persistence: result.status,
    });
  }
  return result;
}

export async function submitActorSessionPass(
  input: {
    sessionSource: "api" | "demo";
    sharedSession: SharedSessionPayload | null;
    peopleMode: PeopleMode;
    participantIds: string[];
    actor: "founder" | "wife";
    candidates: CandidateViewModel[];
    reactions: ReactionState;
    failureMode?: "fallback" | "retain";
  },
  ports: Pick<
    SessionProgressPorts,
    | "startSessionSync"
    | "finishSessionSync"
    | "updateSession"
    | "setDemoDebugFallback"
  >,
  dependencies: SessionProgressDependencies = defaultProgressDependencies,
): Promise<ActorPassSubmissionResult> {
  if (input.sessionSource !== "api" || input.sharedSession === null) {
    return { status: "ready" };
  }

  const participantId = participantIdForActor(
    input.peopleMode,
    input.participantIds,
    input.actor,
  );
  if (!participantId) {
    return { status: "ready" };
  }

  ports.startSessionSync("saving");
  try {
    const session = await dependencies.submitReactions(input.sharedSession.sessionId, {
      participantId,
      reactions: reactionsPayload(input.candidates, input.reactions),
    });
    ports.updateSession({ sharedSession: session });
    return { status: "ready" };
  } catch (error) {
    const message = publicErrorMessage("reaction-save", error);
    if (input.failureMode !== "retain") {
      ports.setDemoDebugFallback();
      ports.updateSession({ apiError: message });
      return { status: "local", message };
    }
    ports.updateSession({ apiError: message });
    return { status: "failed", message };
  } finally {
    ports.finishSessionSync();
  }
}

export type ActorPassSubmissionResult =
  | { status: "ready" }
  | { status: "local" | "failed"; message: string };

export async function advancePassThePhoneHandoff(
  input: {
    sessionSource: "api" | "demo";
    sharedSession: SharedSessionPayload | null;
  },
  ports: Pick<
    SessionProgressPorts,
    | "startSessionSync"
    | "finishSessionSync"
    | "updateSession"
    | "setDemoDebugFallback"
    | "completeHandoff"
  >,
  dependencies: SessionProgressDependencies = defaultProgressDependencies,
): Promise<void> {
  if (input.sessionSource !== "api" || input.sharedSession === null) {
    ports.completeHandoff();
    return;
  }

  ports.startSessionSync("loading");
  try {
    const session = await dependencies.advanceHandoff(input.sharedSession.sessionId);
    ports.updateSession({ sharedSession: session });
  } catch (error) {
    ports.setDemoDebugFallback();
    ports.updateSession({ apiError: publicErrorMessage("handoff-save", error) });
  } finally {
    ports.finishSessionSync();
    ports.completeHandoff();
  }
}
