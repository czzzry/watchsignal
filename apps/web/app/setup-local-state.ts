import type { SetupProfile, SetupState } from "./setup-api";

export const localSetupKey = "watchsignal.setup.v1";

export type SetupStorage = Pick<Storage, "getItem" | "setItem" | "removeItem">;

export type StoredSetup = {
  setup: SetupState;
  pendingSync: true;
};

export function updateSetupProfile(
  setup: SetupState,
  profileId: string,
  change: Partial<SetupProfile>,
): SetupState {
  return {
    ...setup,
    profiles: setup.profiles.map((profile) =>
      profile.id === profileId ? { ...profile, ...change } : profile,
    ),
  };
}

export function normalizeSetup(setup: SetupState): SetupState {
  return {
    ...setup,
    profiles: setup.profiles.map((profile) => ({
      ...profile,
      label: profile.label.trim() || `Profile ${profile.order}`,
    })),
  };
}

export function keepSetupOnPhone(storage: SetupStorage, setup: SetupState): SetupState {
  const normalized = normalizeSetup(setup);
  storage.setItem(
    localSetupKey,
    JSON.stringify({ setup: normalized, pendingSync: true } satisfies StoredSetup),
  );
  return normalized;
}

export function loadSetupFromPhone(storage: SetupStorage): SetupState | null {
  return loadStoredSetupFromPhone(storage)?.setup ?? null;
}

export function loadStoredSetupFromPhone(storage: SetupStorage): StoredSetup | null {
  try {
    const stored = storage.getItem(localSetupKey);
    if (!stored) return null;
    const parsed = JSON.parse(stored) as unknown;
    const setup = isRecord(parsed) && "setup" in parsed
      ? parseCompleteSetup(parsed.setup)
      : parseCompleteSetup(parsed);
    if (!setup) return null;
    return { setup, pendingSync: true };
  } catch {
    return null;
  }
}

export function clearSetupFromPhone(storage: SetupStorage): void {
  storage.removeItem(localSetupKey);
}

export function setupStatesMatch(first: SetupState, second: SetupState): boolean {
  return JSON.stringify(first) === JSON.stringify(second);
}

function parseCompleteSetup(value: unknown): SetupState | null {
  if (!isRecord(value) || !isRecord(value.defaults) || !Array.isArray(value.profiles)) {
    return null;
  }
  const profiles = value.profiles.map(parseProfile);
  if (profiles.length < 2 || profiles.some((profile) => profile === null)) return null;
  const completeProfiles = profiles as SetupProfile[];
  if (
    typeof value.householdLabel !== "string" ||
    typeof value.activeProfileId !== "string" ||
    typeof value.partnerProfileId !== "string" ||
    value.activeProfileId === value.partnerProfileId ||
    !completeProfiles.some((profile) => profile.id === value.activeProfileId) ||
    !completeProfiles.some((profile) => profile.id === value.partnerProfileId)
  ) {
    return null;
  }
  const defaults = value.defaults;
  if (
    typeof defaults.availabilityRegion !== "string" ||
    typeof defaults.avoidAlreadyWatched !== "boolean" ||
    typeof defaults.inputMode !== "string" ||
    typeof defaults.languageAccess !== "string" ||
    typeof defaults.sessionType !== "string" ||
    typeof defaults.shortlistSize !== "number"
  ) {
    return null;
  }
  return {
    householdLabel: value.householdLabel,
    activeProfileId: value.activeProfileId,
    partnerProfileId: value.partnerProfileId,
    profiles: completeProfiles,
    defaults: {
      availabilityRegion: defaults.availabilityRegion,
      avoidAlreadyWatched: defaults.avoidAlreadyWatched,
      inputMode: defaults.inputMode,
      languageAccess: defaults.languageAccess,
      sessionType: defaults.sessionType,
      shortlistSize: defaults.shortlistSize,
    },
  };
}

function parseProfile(value: unknown): SetupProfile | null {
  if (
    !isRecord(value) ||
    typeof value.id !== "string" ||
    typeof value.label !== "string" ||
    typeof value.order !== "number" ||
    typeof value.avatarKey !== "string" ||
    typeof value.colorKey !== "string"
  ) {
    return null;
  }
  return {
    id: value.id,
    label: value.label,
    order: value.order,
    avatarKey: value.avatarKey,
    colorKey: value.colorKey,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
