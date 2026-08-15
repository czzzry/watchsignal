import type { TonightIntentInterpretationPayload } from "../session-client";

export function continuationBatchIsFresh(
  nextIds: string[],
  previouslyShownIds: string[],
): boolean {
  return nextIds.length === 5 &&
    new Set(nextIds).size === 5 &&
    nextIds.every((id) => !previouslyShownIds.includes(id));
}

export function clarificationResolvedOnce(
  interpretation: TonightIntentInterpretationPayload,
): { pending: TonightIntentInterpretationPayload | null; message: string } {
  if (interpretation.status === "clarification_required") {
    return {
      pending: null,
      message: "That still isn’t clear enough. Try a shorter steer.",
    };
  }
  return {
    pending: interpretation,
    message: "Review this before using it for the next five.",
  };
}

export function publicSteerFailure(): string {
  return "Couldn’t read that steer. Your words are still here.";
}

export function publicContinuationFailure(): string {
  return "Couldn’t find five fresh movies. Your earlier choices are still here.";
}
