export const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export type SetupProfile = {
  id: string;
  label: string;
  order: number;
  avatarKey: string;
  colorKey: string;
};

export type SetupDefaults = {
  sessionType: string;
  inputMode: string;
  availabilityRegion: string;
  languageAccess: string;
  shortlistSize: number;
  avoidAlreadyWatched: boolean;
};

export type SetupState = {
  householdLabel: string;
  profiles: SetupProfile[];
  activeProfileId: string;
  partnerProfileId: string;
  defaults: SetupDefaults;
};

export type SetupLoadResult = {
  setup: SetupState;
  source: "backend" | "fallback";
  detail: string;
  canPersist: boolean;
};

export const fallbackSetup: SetupState = {
  householdLabel: "Household",
  activeProfileId: "profile-1",
  partnerProfileId: "profile-2",
  profiles: [
    {
      id: "profile-1",
      label: "Husband",
      order: 1,
      avatarKey: "spark",
      colorKey: "cyan",
    },
    {
      id: "profile-2",
      label: "Wife",
      order: 2,
      avatarKey: "moon",
      colorKey: "rose",
    },
  ],
  defaults: {
    sessionType: "Movie night",
    inputMode: "Pass the phone",
    availabilityRegion: "Prime Video Germany",
    languageAccess: "English audio or foreign audio with verified English subtitles",
    shortlistSize: 5,
    avoidAlreadyWatched: true,
  },
};

export async function loadSetupState(
  apiBaseUrl = process.env.API_BASE_URL ?? DEFAULT_API_BASE_URL,
): Promise<SetupLoadResult> {
  const setupUrl = new URL("/setup", apiBaseUrl);

  try {
    const response = await fetch(setupUrl, {
      cache: "no-store",
      signal: AbortSignal.timeout(2000),
    });

    if (!response.ok) {
      return fallbackLoadResult(
        `Setup API returned HTTP ${response.status}. Local defaults are shown until Slice 2 lands.`,
      );
    }

    const payload = (await response.json()) as unknown;
    const setup = parseSetupState(payload);

    if (!setup) {
      return fallbackLoadResult(
        "Setup API returned an unexpected response. Local defaults are shown for review.",
      );
    }

    return {
      setup,
      source: "backend",
      detail: "Loaded setup from FastAPI.",
      canPersist: true,
    };
  } catch {
    return fallbackLoadResult(
      `Setup API is not reachable at ${apiBaseUrl}. Local defaults are shown for review.`,
    );
  }
}

export async function saveSetupState(setup: SetupState): Promise<SetupLoadResult> {
  try {
    const response = await fetch("/api/setup", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(setup),
    });
    const payload = (await response.json()) as unknown;
    const savedSetup = parseSetupState(payload);

    if (!response.ok || !savedSetup) {
      return {
        setup,
        source: "fallback",
        detail: "Setup could not be saved. Your edits are still visible locally.",
        canPersist: false,
      };
    }

    return {
      setup: savedSetup,
      source: "backend",
      detail: "Saved setup to FastAPI.",
      canPersist: true,
    };
  } catch {
    return {
      setup,
      source: "fallback",
      detail: "Setup API is not reachable. Your edits are still visible locally.",
      canPersist: false,
    };
  }
}

export async function createSetupProfile(
  label: string,
  fallbackSetupState: SetupState = fallbackSetup,
): Promise<SetupLoadResult> {
  try {
    const response = await fetch("/api/setup/profiles", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ label }),
    });
    const payload = (await response.json()) as unknown;
    const savedSetup = parseSetupState(payload);

    if (!response.ok || !savedSetup) {
      return {
        setup: fallbackSetupState,
        source: "fallback",
        detail: "Profile could not be created.",
        canPersist: false,
      };
    }

    return {
      setup: savedSetup,
      source: "backend",
      detail: `${label.trim()} is now the active profile.`,
      canPersist: true,
    };
  } catch {
    return {
      setup: fallbackSetupState,
      source: "fallback",
      detail: "Setup API is not reachable. Profile could not be created.",
      canPersist: false,
    };
  }
}

function fallbackLoadResult(detail: string): SetupLoadResult {
  return {
    setup: fallbackSetup,
    source: "fallback",
    detail,
    canPersist: false,
  };
}

function parseSetupState(payload: unknown): SetupState | null {
  const candidate =
    isRecord(payload) && isRecord(payload.setup) ? payload.setup : payload;

  if (!isRecord(candidate) || !isRecord(candidate.defaults)) {
    return null;
  }

  if (
    typeof candidate.householdLabel !== "string" ||
    !Array.isArray(candidate.profiles)
  ) {
    return null;
  }

  const profiles = candidate.profiles
    .map(parseProfile)
    .filter((profile): profile is SetupProfile => profile !== null);

  if (profiles.length < 2) {
    return null;
  }

  const defaults = parseDefaults(candidate.defaults);

  if (!defaults) {
    return null;
  }

  const activeProfileId =
    typeof candidate.activeProfileId === "string" && candidate.activeProfileId.trim()
      ? candidate.activeProfileId
      : profiles[0].id;
  const resolvedActiveProfileId = profiles.some((profile) => profile.id === activeProfileId)
    ? activeProfileId
    : profiles[0].id;

  return {
    householdLabel: candidate.householdLabel,
    profiles,
    activeProfileId: resolvedActiveProfileId,
    partnerProfileId: resolvePartnerProfileId(
      profiles,
      resolvedActiveProfileId,
      typeof candidate.partnerProfileId === "string" ? candidate.partnerProfileId : null,
    ),
    defaults,
  };
}

function resolvePartnerProfileId(
  profiles: SetupProfile[],
  activeProfileId: string,
  partnerProfileId: string | null,
): string {
  const profileIds = profiles.map((profile) => profile.id);
  const resolvedActiveProfileId = profileIds.includes(activeProfileId)
    ? activeProfileId
    : profileIds[0];
  if (
    partnerProfileId &&
    profileIds.includes(partnerProfileId) &&
    partnerProfileId !== resolvedActiveProfileId
  ) {
    return partnerProfileId;
  }

  return profileIds.find((profileId) => profileId !== resolvedActiveProfileId) ?? profileIds[1];
}

function parseProfile(profile: unknown): SetupProfile | null {
  if (!isRecord(profile)) {
    return null;
  }

  if (
    typeof profile.id !== "string" ||
    typeof profile.label !== "string" ||
    typeof profile.order !== "number"
  ) {
    return null;
  }

  return {
    id: profile.id,
    label: profile.label,
    order: profile.order,
    avatarKey:
      typeof profile.avatarKey === "string" && profile.avatarKey.trim()
        ? profile.avatarKey
        : defaultAvatarKey(profile.order),
    colorKey:
      typeof profile.colorKey === "string" && profile.colorKey.trim()
        ? profile.colorKey
        : defaultColorKey(profile.order),
  };
}

function parseDefaults(defaults: unknown): SetupDefaults | null {
  if (!isRecord(defaults)) {
    return null;
  }

  if (
    typeof defaults.sessionType !== "string" ||
    typeof defaults.inputMode !== "string" ||
    typeof defaults.availabilityRegion !== "string" ||
    typeof defaults.languageAccess !== "string" ||
    typeof defaults.shortlistSize !== "number" ||
    typeof defaults.avoidAlreadyWatched !== "boolean"
  ) {
    return null;
  }

  return {
    sessionType: defaults.sessionType,
    inputMode: defaults.inputMode,
    availabilityRegion: defaults.availabilityRegion,
    languageAccess: defaults.languageAccess,
    shortlistSize: defaults.shortlistSize,
    avoidAlreadyWatched: defaults.avoidAlreadyWatched,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function defaultAvatarKey(order: number): string {
  return order === 2 ? "moon" : "spark";
}

function defaultColorKey(order: number): string {
  return order === 2 ? "rose" : "cyan";
}
