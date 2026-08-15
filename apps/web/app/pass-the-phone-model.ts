import type {
  ParticipantOnboardingPayload,
  TitleResolutionEntryPayload,
} from "./session-client";
import type { DemoCandidate, ReactionValue } from "./session-fixtures";

export type ApiHealth = {
  connected: boolean;
  label: "Connected" | "Disconnected";
  detail: string;
};

export type WizardStep = "setup" | "founder" | "handoff" | "wife" | "results";

export type ReactionState = Record<string, ReactionValue | undefined>;
export type SeenMemoryValue = "loved" | "fine" | "no" | "forget";
export type SeenMemoryState = Record<string, SeenMemoryValue | undefined>;
export type FeedbackState = Record<string, "loved" | "fine" | "no" | undefined>;
export type FeedbackNoteState = Record<string, string>;

export type OnboardingDraft = {
  lovedTitleEntries: TitleResolutionEntryPayload[];
  fineTitleEntries: TitleResolutionEntryPayload[];
  noTitleEntries: TitleResolutionEntryPayload[];
  manualLoved: string;
  manualFine: string;
  manualNo: string;
};

export type SessionSource = "api" | "demo";
export type SyncStatus = "ready" | "saving" | "loading";
export type DebugHistoryStatus = "idle" | "loading" | "ready" | "failed";
export type OnboardingStatus = "idle" | "loading" | "ready" | "saving" | "failed";

export type ReviewTag = "bug" | "confusing" | "ugly" | "good";
export type PeopleMode = "couple" | "founder" | "wife";
export type LanguageMode = "english" | "subtitles-ok" | "anything";

export type ReviewNote = {
  id: string;
  step: WizardStep;
  tag: ReviewTag;
  text: string;
  createdAt: string;
};

export type OnboardingPromptState = {
  profileId: string;
  profileLabel: string;
} | null;

export type CandidateProvenance = {
  poster: "api-payload" | "local-demo-asset" | "fallback-placeholder";
  criticScore: "demo-fixture" | "not-provided";
  descriptiveCopy: "api-payload" | "local-demo-fixture" | "generic-fallback";
};

export type CandidateViewModel = DemoCandidate & {
  provenance: CandidateProvenance;
};

export type MatchIndexBreakdown = {
  scoreKind: "match_index_v1";
  score: number;
  exactScore: number;
  baseSignal: number;
  reactionDeltaRaw: number;
  combinedRaw: number;
  rawMinimum: -0.36 | -0.18;
  rawMaximum: 1.24 | 1.12;
};

export type RankedCandidate = CandidateViewModel & {
  score: number;
  profileScore: number;
  matchIndex: MatchIndexBreakdown;
};

export type TitleResolutionEntry =
  ParticipantOnboardingPayload["lovedTitleEntries"][number];
