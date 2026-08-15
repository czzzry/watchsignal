import type { OnboardingDraft, OnboardingStatus } from "../pass-the-phone-model";
import type { DemoCandidate } from "../session-fixtures";
import type { TitleResolutionEntryPayload } from "../session-client";
import { publicErrorMessage } from "./public-error-message.ts";

export const onboardingBuckets = ["loved", "fine", "no"] as const;
export type OnboardingBucketKey = (typeof onboardingBuckets)[number];
export type OnboardingFlowState = {
  phase: "intro" | "bucket" | "summary";
  bucket: OnboardingBucketKey;
};

export const onboardingBucketCopy: Record<
  OnboardingBucketKey,
  { label: string; prompt: string }
> = {
  loved: { label: "Loved", prompt: "A movie you would happily watch again." },
  fine: { label: "It was fine", prompt: "Good enough, but not special." },
  no: { label: "Not for me", prompt: "A clear no from past experience." },
};

export function entriesForOnboardingBucket(
  draft: OnboardingDraft,
  bucket: OnboardingBucketKey,
): TitleResolutionEntryPayload[] {
  if (bucket === "loved") return draft.lovedTitleEntries;
  if (bucket === "fine") return draft.fineTitleEntries;
  return draft.noTitleEntries;
}

export function manualValueForOnboardingBucket(
  draft: OnboardingDraft,
  bucket: OnboardingBucketKey,
): string {
  if (bucket === "loved") return draft.manualLoved;
  if (bucket === "fine") return draft.manualFine;
  return draft.manualNo;
}

export function firstIncompleteOnboardingBucket(
  draft: OnboardingDraft,
): OnboardingBucketKey | null {
  return onboardingBuckets.find(
    (bucket) => entriesForOnboardingBucket(draft, bucket).length === 0,
  ) ?? null;
}

export function onboardingDraftComplete(draft: OnboardingDraft): boolean {
  return firstIncompleteOnboardingBucket(draft) === null;
}

export function onboardingCompletionCount(draft: OnboardingDraft): number {
  return onboardingBuckets.filter(
    (bucket) => entriesForOnboardingBucket(draft, bucket).length > 0,
  ).length;
}

export function onboardingHomeStatusCopy(
  status: OnboardingStatus,
  completedCount: number | null,
  totalCount: number,
): {
  busyLabel: "Checking" | "Saving" | null;
  progressLabel: string;
  completionKnown: boolean;
} {
  if (completedCount === null) {
    return {
      busyLabel: status === "loading" ? "Checking" : null,
      progressLabel: status === "loading" ? "Checking taste setup" : "Setup check needed",
      completionKnown: false,
    };
  }

  return {
    busyLabel: status === "saving" ? "Saving" : status === "loading" ? "Checking" : null,
    progressLabel: `${completedCount} of ${totalCount} ready`,
    completionKnown: true,
  };
}

export function onboardingPublicMessage(message: string | null): string | null {
  if (!message) return null;
  if (/^Each person needs at least one Loved, Ok, and No seed\.$/.test(message)) {
    return message;
  }
  return publicErrorMessage("onboarding-save", message);
}

export function advanceOnboardingFlow(
  state: OnboardingFlowState,
  draft: OnboardingDraft,
): OnboardingFlowState {
  if (state.phase === "intro") {
    return {
      phase: "bucket",
      bucket: firstIncompleteOnboardingBucket(draft) ?? "loved",
    };
  }
  if (state.phase === "summary") return state;
  const index = onboardingBuckets.indexOf(state.bucket);
  return index < onboardingBuckets.length - 1
    ? { phase: "bucket", bucket: onboardingBuckets[index + 1] }
    : { phase: "summary", bucket: state.bucket };
}

export function reverseOnboardingFlow(
  state: OnboardingFlowState,
): OnboardingFlowState | null {
  if (state.phase === "intro") return null;
  if (state.phase === "summary") return { phase: "bucket", bucket: "no" };
  const index = onboardingBuckets.indexOf(state.bucket);
  return index > 0
    ? { phase: "bucket", bucket: onboardingBuckets[index - 1] }
    : { phase: "intro", bucket: state.bucket };
}

export function addSuggestedOnboardingSeed(
  draft: OnboardingDraft,
  bucket: OnboardingBucketKey,
  candidate: DemoCandidate,
): OnboardingDraft {
  const entry: TitleResolutionEntryPayload = {
    rawTitle: candidate.title,
    status: "resolved",
    candidate: {
      source: "tmdb",
      sourceId: candidate.id,
      title: candidate.title,
      mediaType: "movie",
      releaseYear: candidate.year,
      overview: candidate.reason,
    },
  };
  const withoutDuplicate = removeMatchingEntries(
    draft,
    (current) => current.candidate?.sourceId === candidate.id,
  );
  return addEntry(withoutDuplicate, bucket, entry);
}

export function addManualOnboardingSeed(
  draft: OnboardingDraft,
  bucket: OnboardingBucketKey,
): OnboardingDraft {
  const trimmed = manualValueForOnboardingBucket(draft, bucket).trim();
  if (!trimmed) return draft;
  const normalized = trimmed.toLocaleLowerCase();
  const withoutDuplicate = removeMatchingEntries(
    draft,
    (entry) =>
      entry.status === "unresolved" &&
      entry.rawTitle.trim().toLocaleLowerCase() === normalized,
  );
  return addEntry(
    setManualValue(withoutDuplicate, bucket, trimmed),
    bucket,
    {
      rawTitle: trimmed,
      status: "unresolved",
      unresolvedReason: "Manual seed entry added from onboarding.",
    },
  );
}

export function removeOnboardingSeed(
  draft: OnboardingDraft,
  bucket: OnboardingBucketKey,
  key: string,
): OnboardingDraft {
  const field = entryField(bucket);
  return {
    ...draft,
    [field]: draft[field].filter((entry) => onboardingEntryKey(entry) !== key),
  };
}

export function onboardingEntryKey(entry: TitleResolutionEntryPayload): string {
  return entry.candidate?.sourceId ?? `${entry.status}:${entry.rawTitle.trim().toLocaleLowerCase()}`;
}

function addEntry(
  draft: OnboardingDraft,
  bucket: OnboardingBucketKey,
  entry: TitleResolutionEntryPayload,
): OnboardingDraft {
  const field = entryField(bucket);
  const key = onboardingEntryKey(entry);
  return {
    ...draft,
    [field]: [entry, ...draft[field].filter((current) => onboardingEntryKey(current) !== key)],
  };
}

function removeMatchingEntries(
  draft: OnboardingDraft,
  predicate: (entry: TitleResolutionEntryPayload) => boolean,
): OnboardingDraft {
  return {
    ...draft,
    lovedTitleEntries: draft.lovedTitleEntries.filter((entry) => !predicate(entry)),
    fineTitleEntries: draft.fineTitleEntries.filter((entry) => !predicate(entry)),
    noTitleEntries: draft.noTitleEntries.filter((entry) => !predicate(entry)),
  };
}

function setManualValue(
  draft: OnboardingDraft,
  bucket: OnboardingBucketKey,
  value: string,
): OnboardingDraft {
  if (bucket === "loved") return { ...draft, manualLoved: value };
  if (bucket === "fine") return { ...draft, manualFine: value };
  return { ...draft, manualNo: value };
}

function entryField(bucket: OnboardingBucketKey): "lovedTitleEntries" | "fineTitleEntries" | "noTitleEntries" {
  if (bucket === "loved") return "lovedTitleEntries";
  if (bucket === "fine") return "fineTitleEntries";
  return "noTitleEntries";
}
