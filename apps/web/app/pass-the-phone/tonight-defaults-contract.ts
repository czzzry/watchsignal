import type { LanguageMode, PeopleMode } from "../pass-the-phone-model";
import type { SessionMode } from "../session-fixtures";
import { publicErrorMessage } from "./public-error-message.ts";

export type DefaultChoice<T extends string> = {
  value: T;
  label: string;
  detail: string;
};

export type TonightDefaultsDraft = {
  languageMode: LanguageMode;
  availabilityRegion: string;
  sessionMode: SessionMode;
};

export type TonightDefaultsSaveResult =
  | { status: "saved" | "local-only" }
  | { status: "failed"; message: string };

export const languageChoices: DefaultChoice<LanguageMode>[] = [
  { value: "english", label: "English", detail: "English audio or English subtitles" },
  { value: "subtitles-ok", label: "Original audio", detail: "English subtitles required" },
  { value: "anything", label: "Any language", detail: "No language filter" },
];

export const availabilityChoices: DefaultChoice<string>[] = [
  { value: "Prime Video Germany", label: "Prime Video", detail: "Available in Germany" },
  { value: "Any streaming Germany", label: "Any streaming service", detail: "Subscription options in Germany" },
];

export function sessionModeChoices(
  founderLabel: string,
  wifeLabel: string,
): DefaultChoice<SessionMode>[] {
  return [
    { value: "compromise", label: "Balanced", detail: "Equal weight for both profiles" },
    { value: "founder-first", label: `${founderLabel} leads`, detail: `${founderLabel}'s fit breaks close calls` },
    { value: "wife-first", label: `${wifeLabel} leads`, detail: `${wifeLabel}'s fit breaks close calls` },
  ];
}

export function tonightDefaultsSummary({
  peopleMode,
  languageMode,
  availabilityRegion,
  sessionMode,
}: {
  peopleMode: PeopleMode;
  languageMode: LanguageMode;
  availabilityRegion: string;
  sessionMode: SessionMode;
}): string {
  const language = languageChoices.find((choice) => choice.value === languageMode)?.label ?? "Language";
  const availability = availabilityChoices.find((choice) => choice.value === availabilityRegion)?.label ?? "Availability";
  const decision = peopleMode === "couple"
    ? sessionMode === "compromise" ? "Balanced" : "Lead mode"
    : "Solo";
  return `${language} · ${availability} · ${decision}`;
}

export function defaultsStatus(canPersist: boolean, message: string | null): string {
  if (!canPersist) {
    return "Changes apply to this phone tonight.";
  }
  if (!message) {
    return "Saved with your household defaults.";
  }
  if (/saved/i.test(message) && !/could not|failed|unavailable|not reachable/i.test(message)) {
    return "Saved.";
  }
  return publicErrorMessage("defaults-save", message);
}

export async function commitTonightDefaultsTransaction(
  draft: TonightDefaultsDraft,
  persistAvailability: (
    availabilityRegion: string,
  ) => Promise<TonightDefaultsSaveResult>,
  applyDraft: (draft: TonightDefaultsDraft) => void,
): Promise<TonightDefaultsSaveResult> {
  const result = await persistAvailability(draft.availabilityRegion);
  if (result.status !== "failed") {
    applyDraft(draft);
  }
  return result;
}
