import type { SessionOutcomeType } from "../../session-client";

export type OutcomeDraft = {
  outcomeType: SessionOutcomeType | null;
  otherPickId: string | null;
  note: string;
};

export type FeedbackRating = "loved" | "fine" | "no";
export type FeedbackSavedFingerprints = Record<string, string | undefined>;

type OutcomeSubmissionCompletion<T> =
  | { status: "saved"; fingerprint: string; value: T }
  | { status: "failed"; fingerprint: string; error: unknown };

type OutcomeSubmissionStart<T> =
  | { status: "started"; completion: Promise<OutcomeSubmissionCompletion<T>> }
  | { status: "blocked"; reason: "in_flight" | "confirmed" };

export type OutcomeSubmissionTransaction = {
  start<T>(
    fingerprint: string,
    submit: () => Promise<T>,
  ): OutcomeSubmissionStart<T>;
  isConfirmed(fingerprint: string): boolean;
  reset(): void;
};

export function outcomeDraftFingerprint(
  sessionId: string,
  draft: OutcomeDraft,
  bestPickId: string | null,
): string | null {
  if (draft.outcomeType === null) return null;
  const selectedId = selectedOutcomeMovieId(draft, bestPickId);
  if (draft.outcomeType !== "watched_nothing" && selectedId === null) return null;
  return JSON.stringify([
    sessionId,
    draft.outcomeType,
    selectedId,
    draft.note.trim(),
  ]);
}

export function createOutcomeSubmissionTransaction(): OutcomeSubmissionTransaction {
  let inFlight = false;
  let confirmedFingerprint: string | null = null;

  return {
    start<T>(fingerprint: string, submit: () => Promise<T>): OutcomeSubmissionStart<T> {
      if (inFlight) return { status: "blocked", reason: "in_flight" };
      if (confirmedFingerprint === fingerprint) {
        return { status: "blocked", reason: "confirmed" };
      }

      inFlight = true;
      const completion = (async (): Promise<OutcomeSubmissionCompletion<T>> => {
        try {
          const value = await submit();
          confirmedFingerprint = fingerprint;
          return { status: "saved", fingerprint, value };
        } catch (error) {
          return { status: "failed", fingerprint, error };
        } finally {
          inFlight = false;
        }
      })();
      return { status: "started", completion };
    },
    isConfirmed(fingerprint: string): boolean {
      return confirmedFingerprint === fingerprint;
    },
    reset(): void {
      inFlight = false;
      confirmedFingerprint = null;
    },
  };
}

export function feedbackDraftFingerprint(
  rating: FeedbackRating | undefined,
  note: string | undefined,
): string | null {
  if (rating === undefined) return null;
  return `${rating}:${note?.trim() ?? ""}`;
}

export function pendingFeedbackProfileIds(
  participantIds: string[],
  ratings: Record<string, FeedbackRating | undefined>,
  notes: Record<string, string | undefined>,
  savedFingerprints: FeedbackSavedFingerprints,
): string[] {
  return participantIds.filter((profileId) => {
    const fingerprint = feedbackDraftFingerprint(
      ratings[profileId],
      notes[profileId],
    );
    return fingerprint !== null && savedFingerprints[profileId] !== fingerprint;
  });
}

export async function settlePendingFeedback<T>(
  profileIds: string[],
  submit: (profileId: string) => Promise<T>,
): Promise<{
  saved: Array<{ profileId: string; value: T }>;
  failedProfileIds: string[];
}> {
  const attempts = await Promise.allSettled(profileIds.map(submit));
  return attempts.reduce<{
    saved: Array<{ profileId: string; value: T }>;
    failedProfileIds: string[];
  }>((result, attempt, index) => {
    const profileId = profileIds[index];
    if (attempt.status === "fulfilled") {
      result.saved.push({ profileId, value: attempt.value });
    } else {
      result.failedProfileIds.push(profileId);
    }
    return result;
  }, { saved: [], failedProfileIds: [] });
}

export function selectedOutcomeMovieId(
  draft: OutcomeDraft,
  bestPickId: string | null,
): string | null {
  if (draft.outcomeType === "watched_recommended") return bestPickId;
  if (draft.outcomeType === "watched_other") return draft.otherPickId;
  return null;
}

export function outcomeDraftCanSave(
  draft: OutcomeDraft,
  bestPickId: string | null,
  canPersist: boolean,
  shortlistIds: string[] = [],
): boolean {
  if (!canPersist || draft.outcomeType === null) return false;
  if (draft.outcomeType === "watched_nothing") return true;
  const selectedId = selectedOutcomeMovieId(draft, bestPickId);
  return selectedId !== null &&
    (draft.outcomeType === "watched_recommended" || shortlistIds.includes(selectedId));
}

export function feedbackDraftCanSave(
  watchedSourceMovieId: string | null,
  participantIds: string[],
  ratings: Record<string, FeedbackRating | undefined>,
  notes: Record<string, string | undefined> = {},
  savedFingerprints: FeedbackSavedFingerprints = {},
): boolean {
  return watchedSourceMovieId !== null &&
    participantIds.length > 0 &&
    participantIds.every((profileId) => ratings[profileId] !== undefined) &&
    pendingFeedbackProfileIds(
      participantIds,
      ratings,
      notes,
      savedFingerprints,
    ).length > 0;
}

export function publicOutcomeError(kind: "outcome" | "feedback"): string {
  return kind === "outcome"
    ? "Couldn’t save what happened. Your choices are still here."
    : "Couldn’t save those ratings. Your choices are still here.";
}
