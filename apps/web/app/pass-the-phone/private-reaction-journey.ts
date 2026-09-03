import type { ReactionState } from "../pass-the-phone-model";

export type PrivateReactionJourney = {
  trail: string[];
  cursor: number;
  deferredCandidateIds: string[];
  forcedCandidateIds: string[];
};

export type PrivateReactionAdvance = {
  journey: PrivateReactionJourney;
  outcome: "advanced" | "complete";
};

export type PrivateReactionForward = {
  journey: PrivateReactionJourney;
  outcome: "forward" | "deferred" | "decision-required" | "unavailable";
};

export type PrivateReactionSwipeAction = "back" | "skip" | "none";

export function createPrivateReactionJourney(
  candidateIds: readonly string[],
): PrivateReactionJourney {
  return {
    trail: candidateIds.length > 0 ? [candidateIds[0]!] : [],
    cursor: 0,
    deferredCandidateIds: [],
    forcedCandidateIds: [],
  };
}

export function activePrivateReactionCandidateId(
  journey: PrivateReactionJourney,
): string | null {
  return journey.trail[journey.cursor] ?? null;
}

export function canNavigatePrivateReactionBack(
  journey: PrivateReactionJourney,
): boolean {
  return journey.cursor > 0;
}

export function canNavigatePrivateReactionForward(
  journey: PrivateReactionJourney,
): boolean {
  return journey.cursor < journey.trail.length - 1;
}

export function navigatePrivateReactionBack(
  journey: PrivateReactionJourney,
): PrivateReactionJourney {
  if (!canNavigatePrivateReactionBack(journey)) return journey;
  return { ...journey, cursor: journey.cursor - 1 };
}

export function advancePrivateReactionAfterAnswer({
  journey,
  candidateIds,
  reactions,
}: {
  journey: PrivateReactionJourney;
  candidateIds: readonly string[];
  reactions: ReactionState;
}): PrivateReactionAdvance {
  const activeCandidateId = activePrivateReactionCandidateId(journey);
  if (!activeCandidateId) return { journey, outcome: "complete" };

  const cleanedJourney = {
    ...journey,
    deferredCandidateIds: journey.deferredCandidateIds.filter(
      (candidateId) => candidateId !== activeCandidateId,
    ),
    forcedCandidateIds: journey.forcedCandidateIds.filter(
      (candidateId) => candidateId !== activeCandidateId,
    ),
  };

  if (canNavigatePrivateReactionForward(journey)) {
    return {
      journey: { ...cleanedJourney, cursor: journey.cursor + 1 },
      outcome: "advanced",
    };
  }

  const nextCandidateId = nextPendingCandidateId({
    activeCandidateId,
    candidateIds,
    reactions,
    deferredCandidateIds: cleanedJourney.deferredCandidateIds,
  });
  if (!nextCandidateId) {
    return { journey: cleanedJourney, outcome: "complete" };
  }

  return {
    journey: appendJourneyCandidate(cleanedJourney, nextCandidateId),
    outcome: "advanced",
  };
}

export function navigatePrivateReactionForwardOrSkip({
  journey,
  candidateIds,
  reactions,
}: {
  journey: PrivateReactionJourney;
  candidateIds: readonly string[];
  reactions: ReactionState;
}): PrivateReactionForward {
  if (canNavigatePrivateReactionForward(journey)) {
    return {
      journey: { ...journey, cursor: journey.cursor + 1 },
      outcome: "forward",
    };
  }

  const activeCandidateId = activePrivateReactionCandidateId(journey);
  if (!activeCandidateId) return { journey, outcome: "unavailable" };
  if (journey.forcedCandidateIds.includes(activeCandidateId)) {
    return { journey, outcome: "decision-required" };
  }
  if (journey.deferredCandidateIds.includes(activeCandidateId)) {
    return {
      journey: {
        ...journey,
        forcedCandidateIds: [...journey.forcedCandidateIds, activeCandidateId],
      },
      outcome: "decision-required",
    };
  }

  const deferredCandidateIds = [...journey.deferredCandidateIds, activeCandidateId];
  const deferredJourney = { ...journey, deferredCandidateIds };
  const nextCandidateId = nextPendingCandidateId({
    activeCandidateId,
    candidateIds,
    reactions,
    deferredCandidateIds,
  }) ?? activeCandidateId;

  return {
    journey: nextCandidateId === activeCandidateId
      ? deferredJourney
      : appendJourneyCandidate(deferredJourney, nextCandidateId),
    outcome: "deferred",
  };
}

export function privateReactionCompletedCount(
  candidateIds: readonly string[],
  reactions: ReactionState,
): number {
  return candidateIds.filter((candidateId) => reactions[candidateId] !== undefined).length;
}

export function privateReactionSwipeAction({
  deltaX,
  deltaY,
  blocked,
  minimumDistance = 52,
}: {
  deltaX: number;
  deltaY: number;
  blocked: boolean;
  minimumDistance?: number;
}): PrivateReactionSwipeAction {
  const horizontalDistance = Math.abs(deltaX);
  if (
    blocked ||
    horizontalDistance < minimumDistance ||
    horizontalDistance <= Math.abs(deltaY) * 1.15
  ) {
    return "none";
  }
  return deltaX > 0 ? "back" : "skip";
}

function nextPendingCandidateId({
  activeCandidateId,
  candidateIds,
  reactions,
  deferredCandidateIds,
}: {
  activeCandidateId: string;
  candidateIds: readonly string[];
  reactions: ReactionState;
  deferredCandidateIds: readonly string[];
}): string | null {
  const pendingCandidates = candidateIds.filter(
    (candidateId) => candidateId !== activeCandidateId && reactions[candidateId] === undefined,
  );
  const deferred = new Set(deferredCandidateIds);
  const pristineCandidateId = orderedAfter(candidateIds, activeCandidateId).find(
    (candidateId) => pendingCandidates.includes(candidateId) && !deferred.has(candidateId),
  );
  if (pristineCandidateId) return pristineCandidateId;

  return deferredCandidateIds.find(
    (candidateId) => candidateId !== activeCandidateId && reactions[candidateId] === undefined,
  ) ?? null;
}

function orderedAfter(
  candidateIds: readonly string[],
  activeCandidateId: string,
): string[] {
  const activeIndex = candidateIds.indexOf(activeCandidateId);
  if (activeIndex < 0) return [...candidateIds];
  return [
    ...candidateIds.slice(activeIndex + 1),
    ...candidateIds.slice(0, activeIndex),
  ];
}

function appendJourneyCandidate(
  journey: PrivateReactionJourney,
  candidateId: string,
): PrivateReactionJourney {
  const retainedTrail = journey.trail.slice(0, journey.cursor + 1);
  return {
    ...journey,
    trail: [...retainedTrail, candidateId],
    cursor: retainedTrail.length,
  };
}
