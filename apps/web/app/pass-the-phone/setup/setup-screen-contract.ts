import type { DebugHistoryStatus } from "../../pass-the-phone-model";
import type { TasteLensSelection } from "../taste-lens-experience";

export type SetupScreenPresentation = {
  tasteLensSummary: string;
  footerNote: string;
};

export function setupScreenPresentation({
  selection,
  utilityLine,
}: {
  selection: TasteLensSelection | null;
  utilityLine: string;
}): SetupScreenPresentation {
  if (!selection) {
    return {
      tasteLensSummary: "Try a filmmaker",
      footerNote: utilityLine,
    };
  }

  const exactList = selection.mode === "exact-list";
  return {
    tasteLensSummary: `${selection.curatorName} · ${exactList ? "Published shelf" : "Inspiration"}`,
    footerNote: exactList
      ? `Only ${selection.curatorName}'s published shelf will be considered. No popularity fallback.`
      : `Using ${selection.curatorName}'s films as inspiration. No popularity fallback.`,
  };
}

export function shouldLoadRecentSessions(status: DebugHistoryStatus): boolean {
  return status === "idle";
}

export function requestSetupPrimaryAction({
  onboardingRequired,
  opener,
  onStart,
  onBeginOnboarding,
}: {
  onboardingRequired: boolean;
  opener: HTMLElement;
  onStart: () => void;
  onBeginOnboarding: (opener: HTMLElement) => void | Promise<void>;
}): void {
  if (onboardingRequired) {
    void onBeginOnboarding(opener);
    return;
  }

  onStart();
}
