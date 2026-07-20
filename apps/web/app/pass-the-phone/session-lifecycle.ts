import type { DemoCandidate, SessionMode } from "../session-fixtures";
import type {
  CandidateViewModel,
  PeopleMode,
  ReactionState,
  SeenMemoryValue,
} from "../pass-the-phone-model";
import {
  advanceSessionHandoff,
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
  toErrorMessage,
  toSeenMemoryErrorMessage,
  toSessionCandidate,
  toSessionCreationErrorMessage,
} from "../pass-the-phone-helpers.ts";
import {
  continuationExcludedSourceMovieIds,
  latestTonightIntent,
  scoringReactionSignals,
  scoringReactionSignalsFromLocal,
  sessionShortlistFromCandidates,
} from "./session-control.ts";

type SessionUpdate = {
  sharedSession?: SharedSessionPayload | null;
  liveSessionId?: string | null;
  shownSourceMovieIds?: string[];
  recommendationSource?: string;
  sessionSource?: "api" | "demo";
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
  loadTasteProfileSummaries: (session: SharedSessionPayload) => Promise<void>;
  loadSoloTasteProfileSummaries: (
    householdId: string,
    participantIds: string[],
  ) => Promise<void>;
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
};

export async function startPassThePhoneSession(
  input: StartSessionInput,
  ports: SessionLifecyclePorts,
  dependencies: SessionLifecycleDependencies = defaultDependencies,
): Promise<void> {
  ports.resetBatch();
  ports.resetSessionProgress();

  if (!input.apiConnected) {
    ports.updateSession({
      sessionSource: "demo",
      apiError: input.disconnectedMessage,
    });
    ports.navigateToStarted();
    return;
  }

  ports.startSessionSync("loading");

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
      tonightIntent: input.activeTonightIntent,
      tonightIntents: input.activeTonightIntents,
    });
    const candidates = shortlistResponse.shortlist.map(toSessionCandidate);
    ports.updateSession({
      recommendationSource: shortlistResponse.recommendationSource,
    });

    if (candidates.length === 0) {
      throw new Error("Recommendation API returned no usable picks for this session.");
    }

    ports.resetBatch(candidates);
    ports.updateSession({
      shownSourceMovieIds: candidates.map((candidate) => candidate.id),
    });

    if (input.isCoupleSession) {
      await createCoupleSession({
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
      });
      await ports.loadSoloTasteProfileSummaries(
        "default-household",
        input.participantIds,
      );
    }
  } catch (error) {
    await recoverWithFallbackCandidates(error, input, ports, dependencies);
  } finally {
    ports.finishSessionSync();
    ports.navigateToStarted();
  }
}

type ContinueSessionInput = {
  apiConnected: boolean;
  sessionMode: SessionMode;
  participantIds: string[];
  shortlistSize: number;
  availabilityRegion: string;
  sessionSource: "api" | "demo";
  sharedSession: SharedSessionPayload | null;
  liveSessionId: string | null;
  shownSourceMovieIds: string[];
  sessionCandidates: CandidateViewModel[];
  firstPassActor: "founder" | "wife";
  founderReactions: ReactionState;
  wifeReactions: ReactionState;
  tonightIntents: TonightIntentInterpretationPayload[];
};

export async function continuePassThePhoneSession(
  input: ContinueSessionInput,
  ports: SessionLifecyclePorts,
  dependencies: SessionLifecycleDependencies = defaultDependencies,
): Promise<void> {
  if (!input.apiConnected || input.sessionSource !== "api") {
    ports.updateSession({
      apiError:
        "Show 5 more needs the synced session so earlier reactions can stay attached.",
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
      tonightIntent: latestTonightIntent(input.tonightIntents),
      tonightIntents: input.tonightIntents,
      excludedSourceMovieIds: excludedMovieIds(input),
      sessionReactions: reactionSignals(input, dependencies),
    });
    const candidates = shortlistResponse.shortlist.map(toSessionCandidate);
    ports.updateSession({
      recommendationSource: shortlistResponse.recommendationSource,
    });

    if (candidates.length !== 5) {
      throw new Error("Recommendation API did not return five fresh picks.");
    }

    if (input.sharedSession !== null) {
      const continuedSession = await dependencies.continueSession(
        input.sharedSession.sessionId,
        sessionShortlistFromCandidates(candidates),
      );
      ports.updateSession({ sharedSession: continuedSession });
      await ports.loadTasteProfileSummaries(continuedSession);
    } else {
      ports.addShownMovieIds(candidates.map((candidate) => candidate.id));
    }

    ports.resetBatch(candidates);
    ports.navigateToStarted();
  } catch (error) {
    ports.updateSession({ apiError: toErrorMessage(error) });
  } finally {
    ports.finishSessionSync();
  }
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
}): Promise<void> {
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
    });
    await ports.loadTasteProfileSummaries(session);
  } catch (error) {
    ports.updateSession({
      sharedSession: null,
      liveSessionId: null,
      sessionSource: "demo",
      apiError: `${toSessionCreationErrorMessage(error)} Continuing on the same shortlist in local mode.`,
    });
  }
}

async function recoverWithFallbackCandidates(
  error: unknown,
  input: StartSessionInput,
  ports: SessionLifecyclePorts,
  dependencies: SessionLifecycleDependencies,
): Promise<void> {
  const fallbackSessionId = dependencies.createId();
  const fallbackCandidates = input.fallbackCandidates.slice(0, 5);
  ports.resetBatch(fallbackCandidates);
  ports.updateSession({
    sharedSession: null,
    liveSessionId: input.isCoupleSession ? null : fallbackSessionId,
    shownSourceMovieIds: fallbackCandidates.map((candidate) => candidate.id),
    recommendationSource: "demo",
    sessionSource: input.isCoupleSession ? "demo" : "api",
    apiError: `${toErrorMessage(error)} Using the backup catalog for this round.`,
  });
  ports.updateResults({
    debugHistoryStatus: "idle",
    debugHistoryMessage: null,
  });

  if (!input.isCoupleSession) {
    return;
  }

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
    });
    await ports.loadTasteProfileSummaries(fallbackSession);
  } catch (sessionError) {
    ports.updateSession({
      apiError: `${toErrorMessage(error)} ${toSessionCreationErrorMessage(sessionError)} The backup round will continue without saving.`,
    });
  }
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

  return scoringReactionSignalsFromLocal({
    sessionId: input.liveSessionId ?? dependencies.createId(),
    participantId: input.participantIds[0],
    candidates: input.sessionCandidates,
    reactions:
      input.firstPassActor === "founder"
        ? input.founderReactions
        : input.wifeReactions,
  });
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
  input: {
    apiConnected: boolean;
    peopleMode: PeopleMode;
    participantIds: string[];
    actor: "founder" | "wife";
    candidate: DemoCandidate;
    memory: SeenMemoryValue;
  },
  ports: Pick<
    SessionProgressPorts,
    "startSessionSync" | "finishSessionSync" | "updateSession"
  >,
  dependencies: SessionProgressDependencies = defaultProgressDependencies,
): Promise<void> {
  if (!input.apiConnected || input.memory === "forget") {
    return;
  }

  const profileId = participantIdForActor(
    input.peopleMode,
    input.participantIds,
    input.actor,
  );
  if (!profileId) {
    return;
  }

  ports.startSessionSync("saving");
  try {
    const onboarding = await dependencies.getOnboarding(profileId);
    await dependencies.saveOnboarding(
      profileId,
      mergeSeenMemoryIntoOnboarding(onboarding, input.candidate, input.memory),
    );
  } catch (error) {
    ports.updateSession({
      apiError: `${toSeenMemoryErrorMessage(error)} This note is only local for now.`,
    });
  } finally {
    ports.finishSessionSync();
  }
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
  },
  ports: Pick<
    SessionProgressPorts,
    | "startSessionSync"
    | "finishSessionSync"
    | "updateSession"
    | "setDemoDebugFallback"
  >,
  dependencies: SessionProgressDependencies = defaultProgressDependencies,
): Promise<void> {
  if (input.sessionSource !== "api" || input.sharedSession === null) {
    return;
  }

  const participantId = participantIdForActor(
    input.peopleMode,
    input.participantIds,
    input.actor,
  );
  if (!participantId) {
    return;
  }

  ports.startSessionSync("saving");
  try {
    const session = await dependencies.submitReactions(input.sharedSession.sessionId, {
      participantId,
      reactions: reactionsPayload(input.candidates, input.reactions),
    });
    ports.updateSession({ sharedSession: session });
  } catch (error) {
    ports.setDemoDebugFallback();
    ports.updateSession({ apiError: toErrorMessage(error) });
  } finally {
    ports.finishSessionSync();
  }
}

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
    ports.updateSession({ apiError: toErrorMessage(error) });
  } finally {
    ports.finishSessionSync();
    ports.completeHandoff();
  }
}
