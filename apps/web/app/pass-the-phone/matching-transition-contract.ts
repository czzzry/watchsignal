export const MATCH_CONVERGENCE_DURATION_MS = 480;
export const MATCH_REVEAL_MAX_MS = 850;

export type MatchingTransitionPhase = "saving" | "matching" | "failed";

export type MatchingTransitionCopy = {
  title: string;
  detail: string;
};

export function matchingTransitionCopy({
  phase,
  coupleSession,
}: {
  phase: MatchingTransitionPhase;
  coupleSession: boolean;
}): MatchingTransitionCopy {
  if (phase === "saving") {
    return {
      title: "Saving your picks",
      detail: coupleSession ? "Both ballots stay private." : "Your ballot stays private.",
    };
  }
  if (phase === "matching") {
    return {
      title: "Finding the overlap",
      detail: coupleSession ? "Both ballots are ready." : "Your picks are ready.",
    };
  }
  return {
    title: "Matching paused",
    detail: "Your picks are safe on this phone.",
  };
}

export function matchRevealMeetsBudget(durationMs: number): boolean {
  return durationMs >= 0 && durationMs <= MATCH_REVEAL_MAX_MS;
}
