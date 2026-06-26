export const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export type SetupProfile = {
  id: string;
  label: string;
  order: number;
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
  profiles: [
    { id: "profile-1", label: "Husband", order: 1 },
    { id: "profile-2", label: "Wife", order: 2 },
  ],
  defaults: {
    sessionType: "Movie night",
    inputMode: "Pass the phone",
    availabilityRegion: "Prime Video Germany",
    languageAccess: "English audio or verified English subtitles",
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

  return {
    householdLabel: candidate.householdLabel,
    profiles,
    defaults,
  };
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
