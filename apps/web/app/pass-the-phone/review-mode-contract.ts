import type { SharedSessionPayload } from "../session-client";

export function reviewModeFromSearch(search: string): boolean {
  return new URLSearchParams(search).get("review") === "1";
}

export function reviewModeAllowsDiagnostics(reviewMode: boolean): boolean {
  return reviewMode;
}

export type ReviewDiagnosticRequestPorts = {
  loadDebugHistory: () => void | Promise<void>;
  loadSessionTasteEvidence: (session: SharedSessionPayload) => void | Promise<void>;
  loadSoloTasteEvidence: (
    householdId: string,
    participantIds: string[],
  ) => void | Promise<void>;
};

export function createReviewDiagnosticRequests(
  reviewMode: boolean,
  ports: ReviewDiagnosticRequestPorts,
) {
  async function request(action: () => void | Promise<void>): Promise<"requested" | "skipped"> {
    if (!reviewModeAllowsDiagnostics(reviewMode)) return "skipped";
    await action();
    return "requested";
  }

  return {
    initialResults: () => request(ports.loadDebugHistory),
    soloSession: (householdId: string, participantIds: string[]) =>
      request(() => ports.loadSoloTasteEvidence(householdId, participantIds)),
    coupleSession: (session: SharedSessionPayload) =>
      request(() => ports.loadSessionTasteEvidence(session)),
    continuation: (session: SharedSessionPayload) =>
      request(() => ports.loadSessionTasteEvidence(session)),
    markWatched: () => request(ports.loadDebugHistory),
    outcome: () => request(ports.loadDebugHistory),
    feedback: () => request(ports.loadDebugHistory),
  };
}

export function reviewSurfaceContract(reviewMode: boolean): {
  showEvidence: boolean;
  showNotes: boolean;
  showEntry: false;
} {
  return {
    showEvidence: reviewModeAllowsDiagnostics(reviewMode),
    showNotes: reviewModeAllowsDiagnostics(reviewMode),
    showEntry: false,
  };
}
