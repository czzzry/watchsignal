import type { CandidateViewModel } from "../pass-the-phone-model";

export type RecoveryReactionValue = "interested" | "maybe" | "no" | "seen";

export type RecoveryMovieDisplay = {
  sourceMovieId: string;
  title: string;
  year: number | null;
  runtimeLabel: string;
  posterUrl: string | null;
  backdropUrl: string | null;
  providerUrl: string | null;
  synopsis: string;
  genres: string[];
  cast: Array<{
    name: string;
    character: string | null;
    profileUrl: string | null;
  }>;
  providers: Array<{
    providerName: string;
    accessType: string;
    region: string;
  }>;
  matchedPersonNames: string[];
  safePickStatus: "Safe Pick" | "Needs Quick Check";
  availability: string;
  languageAccess: string;
  tone: string;
  positiveEvidence: string[];
  penalties: string[];
};

export type FounderSealCommand = {
  kind: "seal_founder_ballot";
  workflowVersion: 1;
  payloadVersion: 1;
  canonicalSessionId: string;
  commandId: string;
  ballot: Array<{
    sourceMovieId: string;
    reaction: RecoveryReactionValue;
  }>;
  displaySnapshot: RecoveryMovieDisplay[];
};

export type OpenSecondPassCommand = {
  kind: "open_second_pass";
  workflowVersion: 1;
  payloadVersion: 1;
  canonicalSessionId?: string;
  commandId: string;
};

export type FinalSealCommand = Omit<
  FounderSealCommand,
  "kind" | "canonicalSessionId"
> & {
  kind: "seal_final_ballot";
  canonicalSessionId?: string;
};

export type PrivateTransitionCommand =
  | FounderSealCommand
  | OpenSecondPassCommand
  | FinalSealCommand
  | {
      kind: "use_local_result";
      workflowVersion: 1;
      payloadVersion: 1;
      commandId: string;
    };

export function createPrivateTransitionToken(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  const binary = Array.from(bytes, (byte) => String.fromCharCode(byte)).join("");
  return btoa(binary)
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replace(/=+$/, "");
}

export function createPrivateTransitionCommandId(): string {
  return Array.from(crypto.getRandomValues(new Uint8Array(32)), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

export function recoveryMovieDisplayFromCandidate(
  candidate: CandidateViewModel,
): RecoveryMovieDisplay {
  const castDetails: Array<{
    name: string;
    character?: string;
    profileUrl?: string;
  }> = candidate.castDetails?.length
    ? candidate.castDetails
    : candidate.topCast.map((name) => ({ name }));
  const matchedPersonNames = (candidate.matchedPersonNames ?? [])
    .slice(0, 3)
    .map((name) => boundedText(name, 100));
  return {
    sourceMovieId: candidate.id,
    title: boundedText(candidate.title, 200),
    year: candidate.year,
    runtimeLabel: boundedText(candidate.runtime, 40),
    posterUrl: httpsUrlOrNull(candidate.posterUrl),
    backdropUrl: httpsUrlOrNull(candidate.backdropUrl),
    providerUrl: httpsUrlOrNull(candidate.providerUrl),
    synopsis: boundedText(candidate.overview ?? "", 1_500),
    genres: candidate.genres
      .slice(0, 5)
      .map((genre) => boundedText(genre, 40)),
    cast: castDetails.slice(0, 3).map((member) => ({
      name: boundedText(member.name, 100),
      character: boundedOptionalText(member.character, 120),
      profileUrl: httpsUrlOrNull(member.profileUrl),
    })),
    providers: (candidate.providerAvailability ?? [])
      .slice(0, 8)
      .map((provider) => ({
        providerName: boundedText(provider.providerName, 100),
        accessType: boundedText(provider.accessType, 40),
        region: boundedText(provider.region, 8),
      })),
    matchedPersonNames,
    safePickStatus: candidate.safePickStatus,
    availability: boundedText(candidate.availability, 240),
    languageAccess: boundedText(candidate.languageAccess, 160),
    tone: boundedText(candidate.tone, 120),
    positiveEvidence: publicPositiveEvidence(
      candidate,
      matchedPersonNames,
    ),
    penalties: (candidate.dominantPenalties ?? [])
      .filter(isPublicPenaltyEvidence)
      .slice(0, 12)
      .map((value) => boundedText(value, 160)),
  };
}

function httpsUrlOrNull(value: string | null | undefined): string | null {
  const normalized = value?.trim();
  return normalized?.startsWith("https://") && unicodeLength(normalized) <= 2_048
    ? normalized
    : null;
}

function publicPositiveEvidence(
  candidate: CandidateViewModel,
  matchedPersonNames: string[],
): string[] {
  const originalMatchedPeople = new Set(candidate.matchedPersonNames ?? []);
  const sanitized = (candidate.dominantPositiveEvidence ?? []).flatMap(
    (value): string[] => {
      if (value.startsWith("nudge_person:")) {
        const person = value.slice("nudge_person:".length).trim();
        if (!originalMatchedPeople.has(person)) return [];
        const boundedPerson = boundedText(person, 100);
        return matchedPersonNames.includes(boundedPerson)
          ? [`nudge_person:${boundedPerson}`]
          : [];
      }
      if (value.startsWith("learned_taste:")) {
        return ["learned_taste:present"];
      }
      if (value.startsWith("title_similarity:")) {
        return ["title_similarity:present"];
      }
      if (
        [
          "nudge_signal:include:",
          "tonight_intent:",
          "profile_concept:likes:",
        ].some((prefix) => value.startsWith(prefix)) ||
        ["shared:overlap_strength", "shared:bridge_value"].includes(value)
      ) {
        return [boundedText(value, 160)];
      }
      return [];
    },
  );
  return Array.from(new Set(sanitized)).slice(0, 12);
}

function isPublicPenaltyEvidence(value: string): boolean {
  return value.startsWith("nudge_signal:avoid:");
}

function boundedText(value: string, maximum: number): string {
  return Array.from(value.trim()).slice(0, maximum).join("");
}

function boundedOptionalText(
  value: string | null | undefined,
  maximum: number,
): string | null {
  const normalized = value?.trim();
  return normalized ? boundedText(normalized, maximum) : null;
}

function unicodeLength(value: string): number {
  return Array.from(value).length;
}

export function stableCanonicalJson(value: unknown): string {
  return JSON.stringify(canonicalValue(value));
}

export async function founderSealCommandFingerprint(
  command: FounderSealCommand,
): Promise<string> {
  return privateTransitionCommandFingerprint(command);
}

export async function privateTransitionCommandFingerprint(
  command: PrivateTransitionCommand,
): Promise<string> {
  const bytes = new TextEncoder().encode(
    stableCanonicalJson(recoveryCommandFingerprintPayload(command)),
  );
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
}

export function stableRecoveryCommandJson(
  command: PrivateTransitionCommand,
): string {
  return stableCanonicalJson(recoveryCommandFingerprintPayload(command));
}

function recoveryCommandFingerprintPayload(
  command: PrivateTransitionCommand,
): unknown {
  if (
    command.kind === "open_second_pass"
    || command.kind === "use_local_result"
  ) return command;
  return {
    ...command,
    displaySnapshot: command.displaySnapshot.map((movie) => ({
      sourceMovieId: movie.sourceMovieId,
      title: movie.title,
      year: movie.year,
      runtime: movie.runtimeLabel,
      posterUrl: movie.posterUrl,
      backdropUrl: movie.backdropUrl,
      providerUrl: movie.providerUrl,
      overview: movie.synopsis,
      genres: movie.genres,
      castDetails: movie.cast,
      providerAvailability: movie.providers,
      matchedPersonNames: movie.matchedPersonNames,
      safePickStatus: movie.safePickStatus,
      availability: movie.availability,
      languageAccess: movie.languageAccess,
      tone: movie.tone,
      dominantPositiveEvidence: movie.positiveEvidence,
      dominantPenalties: movie.penalties,
    })),
  };
}

function canonicalValue(value: unknown): unknown {
  if (
    value === null ||
    typeof value === "string" ||
    typeof value === "boolean"
  ) {
    return value;
  }
  if (typeof value === "number" && Number.isSafeInteger(value)) {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map(canonicalValue);
  }
  if (isRecord(value)) {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, canonicalValue(value[key])]),
    );
  }
  throw new TypeError("Recovery commands must contain only canonical JSON values.");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
