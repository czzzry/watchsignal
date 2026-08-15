import type {
  PrivateTransitionResumeProjectionPayload,
  RecoveryMovieDisplayPayload,
  RecoveryReactionPayload,
} from "../api-contract.generated.ts";

export type PrivateTransitionRestorePlan =
  | {
      kind: "handoff";
      stage: "handoff_pending" | "handoff_ready";
      recipientLabel: string;
      canBegin: boolean;
      shouldPoll: boolean;
    }
  | {
      kind: "second_pass";
      stage: "second_pass_ready";
      displaySnapshot: RecoveryMovieDisplayPayload[];
    }
  | {
      kind: "matching";
      stage: "matching_pending" | "matching_failed";
      phase: "saving" | "failed";
      shouldPoll: boolean;
    }
  | {
      kind: "result";
      stage: "result_ready";
      canonicalSessionId: string;
      displaySnapshot: RecoveryMovieDisplayPayload[];
      finalReactions: RecoveryReactionPayload[];
      resultSource: "shared" | "local";
    };

export function privateTransitionRestorePlan(
  projection: PrivateTransitionResumeProjectionPayload,
): PrivateTransitionRestorePlan {
  if (
    projection.kind === "handoff_pending"
    || projection.kind === "handoff_ready"
  ) {
    return {
      kind: "handoff",
      stage: projection.kind,
      recipientLabel: projection.recipientLabel,
      canBegin: projection.canBegin,
      shouldPoll: projection.kind === "handoff_pending",
    };
  }
  if (projection.kind === "second_pass_ready") {
    return {
      kind: "second_pass",
      stage: projection.kind,
      displaySnapshot: projection.displaySnapshot,
    };
  }
  if (projection.kind === "matching_pending") {
    return {
      kind: "matching",
      stage: projection.kind,
      phase: "saving",
      shouldPoll: true,
    };
  }
  if (projection.kind === "matching_failed") {
    return {
      kind: "matching",
      stage: projection.kind,
      phase: "failed",
      shouldPoll: false,
    };
  }
  return {
    kind: "result",
    stage: projection.kind,
    canonicalSessionId: projection.canonicalSessionId,
    displaySnapshot: projection.displaySnapshot,
    finalReactions: projection.finalReactions,
    resultSource: projection.resultSource,
  };
}
