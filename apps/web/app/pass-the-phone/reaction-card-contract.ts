import type { DemoCandidate, ReactionValue } from "../session-fixtures";

export const privateReactionValues = ["interested", "maybe", "no"] as const satisfies readonly ReactionValue[];

type PublicReactionFitEvidence = Pick<
  DemoCandidate,
  | "dominantPositiveEvidence"
  | "genres"
  | "matchedPersonNames"
>;

type PublicReactionSynopsis = Pick<DemoCandidate, "overview" | "title">;

export function publicReactionSynopsis(
  candidate: PublicReactionSynopsis,
): string {
  const overview = candidate.overview?.trim();
  return overview || `More details for ${candidate.title} are not available yet.`;
}

export function publicReactionFitLine(
  candidate: PublicReactionFitEvidence,
): string {
  const evidence = candidate.dominantPositiveEvidence ?? [];
  const requestedPerson = candidate.matchedPersonNames
    ?.map((name) => cleanPublicEvidenceValue(name))
    .find((name): name is string =>
      Boolean(name) && evidence.some(
        (item) => item.toLocaleLowerCase() === `nudge_person:${name}`.toLocaleLowerCase(),
      )
    );
  if (requestedPerson) {
    return `${requestedPerson} matches what you asked for in tonight’s movie.`;
  }

  const confirmedIntent = firstPublicEvidenceValue(
    evidence,
    ["nudge_signal:include:", "tonight_intent:"],
  );
  if (confirmedIntent) {
    return `${sentenceCase(confirmedIntent)} matches what you asked for in a movie tonight.`;
  }

  const savedTaste = firstPublicEvidenceValue(
    evidence,
    ["profile_concept:likes:"],
  );
  if (savedTaste) {
    return `Your saved taste for ${savedTaste} supports this choice tonight.`;
  }

  if (evidence.some(
    (item) => item === "shared:overlap_strength" || item === "shared:bridge_value",
  )) {
    return "Your shared taste gives this movie a clear reason to consider.";
  }

  const genres = candidate.genres
    .map((genre) => cleanPublicEvidenceValue(genre))
    .filter((genre): genre is string => Boolean(genre))
    .slice(0, 2);
  if (genres.length === 2) {
    return `A ${genres[0]} and ${genres[1]} option for your private pick tonight.`;
  }
  if (genres.length === 1) {
    return `A ${genres[0]} option for your private pick tonight.`;
  }
  return "One of tonight’s shortlisted movies for your private pick.";
}

function firstPublicEvidenceValue(
  evidence: string[],
  prefixes: string[],
): string | null {
  for (const item of evidence) {
    const prefix = prefixes.find((candidate) => item.startsWith(candidate));
    if (!prefix) continue;
    const value = cleanPublicEvidenceValue(item.slice(prefix.length));
    if (value) return value;
  }
  return null;
}

function cleanPublicEvidenceValue(value: string): string | null {
  const cleaned = value
    .replaceAll("_", " ")
    .replaceAll("/", " and ")
    .replace(/[^\p{L}\p{N}’'& -]+/gu, " ")
    .replace(/\s+/g, " ")
    .trim()
    .split(" ")
    .slice(0, 3)
    .join(" ");
  if (
    !cleaned ||
    /\b(?:mode|score|signal|evidence|taste lab|count|debug|model|rank)\b/i.test(cleaned)
  ) {
    return null;
  }
  return cleaned;
}

function sentenceCase(value: string): string {
  return value.charAt(0).toLocaleUpperCase() + value.slice(1);
}

export function canBeginPrivateReaction({
  commitLocked,
  isSyncing,
  lastAcceptedAt = Number.NEGATIVE_INFINITY,
  now = Number.POSITIVE_INFINITY,
}: {
  commitLocked: boolean;
  isSyncing: boolean;
  lastAcceptedAt?: number;
  now?: number;
}): boolean {
  return !commitLocked && !isSyncing && now - lastAcceptedAt >= 220;
}

export function privateReactionMotionDuration(reducedMotion: boolean): number {
  return reducedMotion ? 0 : 220;
}

export function privateReactionStatus({
  pending,
  isSyncing,
  localOnly,
}: {
  pending: ReactionValue | null;
  isSyncing: boolean;
  localOnly: boolean;
}): string {
  if (pending !== null || isSyncing) {
    return "Saving your private pick…";
  }
  return localOnly ? "Private on this phone" : "Private until you both finish";
}
