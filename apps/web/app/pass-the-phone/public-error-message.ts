export const publicErrorContexts = [
  "onboarding-load",
  "onboarding-save",
  "seen-memory-save",
  "reaction-save",
  "handoff-save",
  "matching",
  "initial-shortlist",
  "continuation",
  "profile-selection",
  "profile-create",
  "defaults-save",
  "history-load",
  "profile-memory-load",
] as const;

export type PublicErrorContext = (typeof publicErrorContexts)[number];

const publicMessages: Record<PublicErrorContext, string> = {
  "onboarding-load":
    "Couldn’t load taste setup. Your current setup is unchanged. Try again.",
  "onboarding-save":
    "Couldn’t save this taste setup. Your picks are still here.",
  "seen-memory-save":
    "Couldn’t save this memory. Your choice is still here. Try again.",
  "reaction-save":
    "Couldn’t save that response. Your choice is still here. Try again.",
  "handoff-save":
    "The handoff stayed private, but reload recovery isn’t available. Keep this tab open and try again.",
  matching:
    "Matching paused. Your completed picks are still here. Try again.",
  "initial-shortlist":
    "Couldn’t find five fresh picks. Your setup is still here. Try again.",
  continuation:
    "Couldn’t find five fresh movies. Your earlier choices are still here. Try again.",
  "profile-selection":
    "This choice is saved on this phone for tonight.",
  "profile-create":
    "New profiles need a connection. The name is still here.",
  "defaults-save":
    "Couldn’t save remotely. Your choices are still here.",
  "history-load":
    "Couldn’t load recent nights. Nothing was changed. Try again.",
  "profile-memory-load":
    "Couldn’t load taste memory. Your profiles are unchanged. Try again.",
};

export function publicErrorMessage(
  context: PublicErrorContext,
  _cause?: unknown,
): string {
  return publicMessages[context];
}
