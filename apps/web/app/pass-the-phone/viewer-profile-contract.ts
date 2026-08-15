import type { PeopleMode } from "../pass-the-phone-model";
import type { SetupProfile } from "../setup-api";
import { publicErrorMessage } from "./public-error-message.ts";

export type ViewerModeOption = {
  value: PeopleMode;
  label: string;
  detail: string;
};

export function viewerModeOptions(
  founderLabel: string,
  wifeLabel: string,
): ViewerModeOption[] {
  return [
    {
      value: "couple",
      label: "Couple",
      detail: `${founderLabel} + ${wifeLabel}`,
    },
    {
      value: "founder",
      label: "Husband solo",
      detail: founderLabel,
    },
    {
      value: "wife",
      label: "Wife solo",
      detail: wifeLabel,
    },
  ];
}

export function hasDistinctViewerProfiles(
  peopleMode: PeopleMode,
  activeProfileId: string,
  partnerProfileId: string,
): boolean {
  return peopleMode !== "couple" || (
    Boolean(activeProfileId) &&
    Boolean(partnerProfileId) &&
    activeProfileId !== partnerProfileId
  );
}

export function profileNameIssue(
  value: string,
  profiles: SetupProfile[],
): string | null {
  const normalized = value.trim().toLocaleLowerCase();
  if (!normalized) {
    return "Enter a name.";
  }
  if (profiles.some((profile) => profile.label.trim().toLocaleLowerCase() === normalized)) {
    return "That profile already exists.";
  }
  return null;
}

export function viewerSetupMessage(
  message: string | null,
  action: "selection" | "create",
): string | null {
  if (!message) {
    return null;
  }
  const normalized = message.toLocaleLowerCase();
  if (normalized.includes("saved") || normalized.includes("active profile") || normalized.includes("is ready")) {
    return "Saved.";
  }
  return publicErrorMessage(
    action === "create" ? "profile-create" : "profile-selection",
    message,
  );
}
