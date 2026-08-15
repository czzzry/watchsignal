import type {
  CandidateCastMember,
  CandidateProviderAvailability,
} from "../../session-fixtures";

export type ResultDetailsCastMember = {
  name: string;
  character: string | null;
  profileUrl: string | null;
};

export type ResultProviderPresentation = {
  providerLabel: string;
  accessLabel: string;
  regionLabel: string;
};

export function publicResultSynopsis({
  overview,
  title,
}: {
  overview?: string | null;
  title: string;
}): string {
  return overview?.trim() || `More details for ${title} are not available yet.`;
}

export function resultDetailsCast({
  castDetails,
  topCast,
}: {
  castDetails?: CandidateCastMember[];
  topCast: string[];
}): ResultDetailsCastMember[] {
  const detailsByName = new Map(
    (castDetails ?? []).map((member) => [member.name.trim().toLowerCase(), member]),
  );

  const names = Array.from(
    new Set([
      ...topCast.map((name) => name.trim()).filter(Boolean),
      ...(castDetails ?? []).map((member) => member.name.trim()).filter(Boolean),
    ]),
  ).slice(0, 3);

  return names.map((name) => {
    const detail = detailsByName.get(name.trim().toLowerCase());
    return {
      name,
      character: detail?.character?.trim() || null,
      profileUrl: detail?.profileUrl?.trim() || null,
    };
  });
}

export function resultEvidence({
  reactions,
  tone,
  runtime,
}: {
  reactions: string;
  tone: string;
  runtime: string;
}): string[] {
  const evidence = [stripTerminalPunctuation(reactions), tone.trim()];
  const runtimeMinutes = parseRuntimeMinutes(runtime);
  evidence.push(
    runtimeMinutes !== null && runtimeMinutes < 120
      ? "Under two hours"
      : `Runtime ${runtime}`,
  );

  return Array.from(new Set(evidence.filter(Boolean))).slice(0, 3);
}

export function resultProviderPresentation({
  providerAvailability,
  fallbackAvailability,
}: {
  providerAvailability?: CandidateProviderAvailability[];
  fallbackAvailability: string;
}): ResultProviderPresentation {
  const entries = (providerAvailability ?? []).filter(
    (entry) => entry.providerName.trim() && entry.accessType.trim() && entry.region.trim(),
  );
  if (entries.length === 0) {
    return {
      providerLabel: fallbackAvailability || "Availability check needed",
      accessLabel: "Confirm access in your provider app",
      regionLabel: "Region DE",
    };
  }

  const providerLabel = Array.from(
    new Set(entries.map((entry) => entry.providerName.trim())),
  ).join(", ");
  const accessTypes = Array.from(
    new Set(entries.map((entry) => accessTypeLabel(entry.accessType))),
  );
  const regions = Array.from(
    new Set(entries.map((entry) => entry.region.trim().toUpperCase())),
  );

  return {
    providerLabel,
    accessLabel: sentenceList(accessTypes),
    regionLabel: `Region ${regions.join("/")}`,
  };
}

export function personInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return "?";
  }
  return `${parts[0][0] ?? ""}${parts.length > 1 ? parts.at(-1)?.[0] ?? "" : ""}`.toUpperCase();
}

export function verifiedProviderLaunchUrl(value?: string): string | null {
  if (!value?.trim()) {
    return null;
  }

  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : null;
  } catch {
    return null;
  }
}

function parseRuntimeMinutes(runtime: string): number | null {
  const hours = runtime.match(/(\d+)\s*h/i);
  const minutes = runtime.match(/(\d+)\s*m/i);
  if (!hours && !minutes) {
    return null;
  }
  return Number(hours?.[1] ?? 0) * 60 + Number(minutes?.[1] ?? 0);
}

function accessTypeLabel(value: string): string {
  switch (value.trim().toLowerCase()) {
    case "flatrate":
    case "subscription":
      return "Included with subscription";
    case "rent":
      return "Rent";
    case "buy":
      return "Buy";
    case "free":
      return "Free";
    case "ads":
      return "Included with ads";
    default:
      return value.trim();
  }
}

function sentenceList(values: string[]): string {
  if (values.length <= 1) {
    return values[0] ?? "Confirm access";
  }
  if (values.length === 2) {
    return `${values[0]} or ${values[1].toLowerCase()}`;
  }
  return `${values.slice(0, -1).join(", ")}, or ${values.at(-1)?.toLowerCase()}`;
}

function stripTerminalPunctuation(value: string): string {
  return value.trim().replace(/[.!?]+$/, "");
}
