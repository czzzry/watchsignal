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
      recipientLabel: string;
      displaySnapshot: RecoveryMovieDisplayPayload[];
    }
  | {
      kind: "matching";
      stage: "matching_pending" | "matching_failed";
      recipientLabel: string;
      phase: "saving" | "failed";
      shouldPoll: boolean;
    }
  | {
      kind: "result";
      stage: "result_ready";
      recipientLabel: string;
      canonicalSessionId: string;
      displaySnapshot: RecoveryMovieDisplayPayload[];
      finalReactions: RecoveryReactionPayload[];
      resultSource: "shared" | "local";
    };

export type PrivateTransitionRecipientPresentation = {
  label: string;
  avatarKey: string;
  colorKey: string;
};

export function privateTransitionRecipientPresentation(
  recoveredRecipientLabel: string | null,
  current: PrivateTransitionRecipientPresentation,
): PrivateTransitionRecipientPresentation {
  if (!recoveredRecipientLabel) return current;
  return {
    label: recoveredRecipientLabel,
    avatarKey: "default",
    colorKey: "neutral",
  };
}

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
      recipientLabel: projection.recipientLabel,
      displaySnapshot: projection.displaySnapshot,
    };
  }
  if (projection.kind === "matching_pending") {
    return {
      kind: "matching",
      stage: projection.kind,
      recipientLabel: projection.recipientLabel,
      phase: "saving",
      shouldPoll: true,
    };
  }
  if (projection.kind === "matching_failed") {
    return {
      kind: "matching",
      stage: projection.kind,
      recipientLabel: projection.recipientLabel,
      phase: "failed",
      shouldPoll: false,
    };
  }
  return {
    kind: "result",
    stage: projection.kind,
    recipientLabel: projection.recipientLabel,
    canonicalSessionId: projection.canonicalSessionId,
    displaySnapshot: projection.displaySnapshot,
    finalReactions: projection.finalReactions,
    resultSource: projection.resultSource,
  };
}
