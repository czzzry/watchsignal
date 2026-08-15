import type {
  DebugHistoryCandidateInputPayload,
  DebugHistoryRecommendationCandidatePayload,
  ParticipantOnboardingPayload,
  ShortlistCandidatePayload,
} from "./session-client";
import type { RecoveryMovieDisplayPayload } from "./api-contract.generated";
import { demoCandidates, type DemoCandidate, type ReactionValue, type SessionMode } from "./session-fixtures.ts";
import type {
  CandidateProvenance,
  CandidateViewModel,
  MatchIndexBreakdown,
  OnboardingDraft,
  PeopleMode,
  RankedCandidate,
  ReactionState,
  SeenMemoryState,
  SeenMemoryValue,
  TitleResolutionEntry,
  WizardStep,
} from "./pass-the-phone-model";

export const fallbackPosterUrl =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 342 513'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='1' y2='1'%3E%3Cstop stop-color='%2307131d'/%3E%3Cstop offset='.48' stop-color='%23142b3a'/%3E%3Cstop offset='1' stop-color='%23331854'/%3E%3C/linearGradient%3E%3CradialGradient id='r' cx='.35' cy='.28' r='.72'%3E%3Cstop stop-color='%2378f0ff' stop-opacity='.34'/%3E%3Cstop offset='.52' stop-color='%237e6cff' stop-opacity='.13'/%3E%3Cstop offset='1' stop-color='%23000000' stop-opacity='0'/%3E%3C/radialGradient%3E%3C/defs%3E%3Crect width='342' height='513' fill='url(%23g)'/%3E%3Crect width='342' height='513' fill='url(%23r)'/%3E%3Ccircle cx='258' cy='82' r='38' fill='%23fff1c7' opacity='.9'/%3E%3Cpath d='M0 372 C58 318 102 332 151 292 C211 243 264 261 342 205 L342 513 L0 513 Z' fill='%23060b12' opacity='.78'/%3E%3Cpath d='M42 406 C96 363 139 371 188 332 C238 292 281 296 314 268' fill='none' stroke='%2378f0ff' stroke-opacity='.34' stroke-width='5'/%3E%3Ctext x='171' y='462' text-anchor='middle' font-family='Arial, sans-serif' font-size='24' font-weight='700' fill='%23eef7ff' letter-spacing='3'%3EWATCHSIGNAL%3C/text%3E%3C/svg%3E";

export const demoCandidateViewModels: CandidateViewModel[] = demoCandidates.map(
  toDemoCandidateViewModel,
);

function sanitizeNarrativeCopy(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }

  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }

  const stripped = trimmed
    .replace(/\bEvidence:.*$/i, "")
    .replace(/\bTaste Lab signals:\s*\d+\.?/gi, "")
    .replace(/\b(?:[A-Z][\w-]*(?:\s+[A-Z][\w-]*){0,3}):\s*\d+(?:\.\d+)?[;,]?\s*/g, "")
    .replace(/\bEnglish audio\.?$/i, "")
    .replace(/\bfallback\.?$/i, "")
    .replace(/\s{2,}/g, " ")
    .replace(/\s+,/g, ",")
    .trim()
    .replace(/[;,:\-]\s*$/g, "")
    .trim();

  return stripped || null;
}

export function toDemoCandidateViewModel(
  candidate: DemoCandidate,
): CandidateViewModel {
  return {
    ...candidate,
    provenance: {
      poster: "local-demo-asset",
      criticScore:
        candidate.criticScore === undefined ? "not-provided" : "demo-fixture",
      descriptiveCopy: "local-demo-fixture",
    },
  };
}

export function stepHeadline(
  step: WizardStep,
  founderLabel: string,
  wifeLabel: string,
  peopleMode: PeopleMode,
): string {
  switch (step) {
    case "setup":
      return "One shared phone, one clear next step.";
    case "founder":
      return peopleMode === "wife"
        ? `${wifeLabel} is choosing now.`
        : `${founderLabel} is choosing first.`;
    case "handoff":
      return `Time to hand the phone to ${wifeLabel}.`;
    case "wife":
      return `${wifeLabel} gets the same five titles.`;
    case "results":
      return peopleMode === "couple"
        ? "Tonight's strongest shared pick."
        : "Tonight's strongest solo pick.";
    default:
      return "";
  }
}

export function formatSessionDate(date: Date): string {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  }).format(date);
}

export function rankCandidates({
  sessionMode,
  peopleMode,
  candidates,
  founderReactions,
  wifeReactions,
  rerankedSourceMovieIds,
}: {
  sessionMode: SessionMode;
  peopleMode: PeopleMode;
  candidates: CandidateViewModel[];
  founderReactions: ReactionState;
  wifeReactions: ReactionState;
  rerankedSourceMovieIds: string[];
}): RankedCandidate[] {
  const ranked = candidates
    .map((candidate) => {
      const modelScore = modelScoreForCandidate({
        candidate,
        peopleMode,
        sessionMode,
      });
      const matchIndex = calculateMatchIndex({
        modelScore,
        peopleMode,
        founderReaction: founderReactions[candidate.id],
        wifeReaction: wifeReactions[candidate.id],
      });

      return {
        ...candidate,
        profileScore: roundMatchIndexScore(modelScore * 100),
        score: matchIndex.score,
        matchIndex,
        sortScore: matchIndex.combinedRaw,
      };
    })
    .sort((first, second) => {
      if (rerankedSourceMovieIds.length > 0) {
        const apiRankById = new Map(
          rerankedSourceMovieIds.map((sourceMovieId, index) => [sourceMovieId, index]),
        );
        return (
          (apiRankById.get(first.id) ?? Number.MAX_SAFE_INTEGER) -
          (apiRankById.get(second.id) ?? Number.MAX_SAFE_INTEGER)
        );
      }

      if (second.sortScore !== first.sortScore) {
        return second.sortScore - first.sortScore;
      }

      return first.baseRank - second.baseRank;
    })
    .map(({ sortScore: _sortScore, ...candidate }) => candidate);

  if (process.env.NODE_ENV !== "production" && rerankedSourceMovieIds.length > 0) {
    for (let index = 1; index < ranked.length; index += 1) {
      if (ranked[index].matchIndex.combinedRaw > ranked[index - 1].matchIndex.combinedRaw) {
        console.warn(
          "WatchSignal Match Index diagnostic: API order contradicts the local combined signal.",
          {
            higherRankedId: ranked[index - 1].id,
            lowerRankedId: ranked[index].id,
          },
        );
      }
    }
  }

  return ranked;
}

export const SCORE_ROUNDING_EPSILON = 1e-10;

export function calculateMatchIndex({
  modelScore,
  peopleMode,
  founderReaction,
  wifeReaction,
}: {
  modelScore: number;
  peopleMode: PeopleMode;
  founderReaction: ReactionValue | undefined;
  wifeReaction: ReactionValue | undefined;
}): MatchIndexBreakdown {
  const baseSignal = clampModelScore(modelScore);
  const reactionDeltaRaw =
    peopleMode === "couple"
      ? reactionConfidenceDelta(founderReaction) +
        reactionConfidenceDelta(wifeReaction)
      : peopleMode === "founder"
        ? reactionConfidenceDelta(founderReaction)
        : reactionConfidenceDelta(wifeReaction);
  const combinedRaw = baseSignal + reactionDeltaRaw;
  const rawMinimum = peopleMode === "couple" ? -0.36 : -0.18;
  const rawMaximum = peopleMode === "couple" ? 1.24 : 1.12;
  const transformed =
    ((combinedRaw - rawMinimum) / (rawMaximum - rawMinimum)) * 100;
  const exactScore = Math.min(100, Math.max(0, transformed));

  return {
    scoreKind: "match_index_v1",
    score: roundMatchIndexScore(exactScore),
    exactScore,
    baseSignal,
    reactionDeltaRaw,
    combinedRaw,
    rawMinimum,
    rawMaximum,
  };
}

export function roundMatchIndexScore(exactScore: number): number {
  return Math.floor(exactScore + 0.5 + SCORE_ROUNDING_EPSILON);
}

export function modelScoreForCandidate({
  candidate,
  peopleMode,
  sessionMode,
}: {
  candidate: CandidateViewModel;
  peopleMode: PeopleMode;
  sessionMode: SessionMode;
}): number {
  if (candidate.groupScore !== undefined) {
    return clampModelScore(candidate.groupScore);
  }

  const founder = clampModelScore(candidate.taste.founder / 100);
  const wife = clampModelScore(candidate.taste.wife / 100);
  if (peopleMode === "founder") {
    return founder;
  }
  if (peopleMode === "wife") {
    return wife;
  }
  if (sessionMode === "founder-first") {
    return founder * 0.7 + wife * 0.3;
  }
  if (sessionMode === "wife-first") {
    return founder * 0.3 + wife * 0.7;
  }

  const leastMiseryFloor = Math.min(founder, wife);
  const average = (founder + wife) / 2;
  const compromise = leastMiseryFloor * 0.6 + average * 0.4;
  return leastMiseryFloor <= 0.35 ? compromise * 0.75 : compromise;
}

function clampModelScore(score: number): number {
  if (Number.isNaN(score)) {
    return 0;
  }
  return Math.min(1, Math.max(0, score));
}

function reactionConfidenceDelta(reaction: ReactionValue | undefined): number {
  if (reaction === "interested") {
    return 0.12;
  }

  if (reaction === "maybe") {
    return 0.04;
  }

  if (reaction === "no") {
    return -0.18;
  }

  return 0;
}

export function describeSharedWhy({
  candidate,
  founderReaction,
  wifeReaction,
  peopleMode,
  founderLabel,
  wifeLabel,
}: {
  candidate: RankedCandidate;
  founderReaction: ReactionValue | undefined;
  wifeReaction: ReactionValue | undefined;
  peopleMode: PeopleMode;
  founderLabel: string;
  wifeLabel: string;
}): string {
  const evidence = resultEvidenceClause(candidate);

  if (peopleMode !== "couple") {
    const reaction = peopleMode === "founder" ? founderReaction : wifeReaction;
    const lead = reaction
      ? `${candidate.title} leads because you marked it ${reactionLabel(reaction)}`
      : `${candidate.title} leads this shortlist`;
    return `${lead}; ${evidence}.`;
  }

  if (founderReaction === "interested" && wifeReaction === "interested") {
    return `${candidate.title} leads because both marked it Interested; ${evidence}.`;
  }

  if (founderReaction && wifeReaction && founderReaction !== wifeReaction) {
    return `${candidate.title} stays high: ${founderLabel} chose ${reactionLabel(founderReaction)}, ${wifeLabel} chose ${reactionLabel(wifeReaction)}; ${evidence}.`;
  }

  if (founderReaction === "no" && wifeReaction === "no") {
    return `${candidate.title} ranks lower because both marked it No; ${evidence}.`;
  }

  if (founderReaction === "maybe" && wifeReaction === "maybe") {
    return `${candidate.title} stays in contention because both marked it Maybe; ${evidence}.`;
  }

  return `${candidate.title} is in tonight's five; ${evidence}.`;
}

function reactionLabel(reaction: ReactionValue): "Interested" | "Maybe" | "No" {
  return reaction === "interested"
    ? "Interested"
    : reaction === "maybe"
      ? "Maybe"
      : "No";
}

function resultEvidenceClause(candidate: RankedCandidate): string {
  const evidence = candidate.dominantPositiveEvidence ?? [];
  const requestedPerson = candidate.matchedPersonNames?.find((name) =>
    evidence.some(
      (item) => item.toLowerCase() === `nudge_person:${name}`.toLowerCase(),
    ),
  );
  if (requestedPerson) {
    return `${requestedPerson} matched tonight's request`;
  }

  const tonightMatch = evidence
    .map((item) => evidenceValue(item, ["nudge_signal:include:", "tonight_intent:"]))
    .find((value): value is string => Boolean(value));
  if (tonightMatch) {
    return `${humanizeEvidenceValue(tonightMatch)} matched tonight's request`;
  }

  const savedGenre = evidence
    .map((item) => evidenceValue(item, ["profile_concept:likes:"]))
    .find((value): value is string => Boolean(value));
  if (savedGenre) {
    return `saved ${humanizeEvidenceValue(savedGenre)} taste evidence also supported it`;
  }

  if (evidence.some((item) => item.startsWith("learned_taste:"))) {
    return "saved movie history also supported it";
  }

  if (evidence.some((item) => item.startsWith("title_similarity:"))) {
    return "similarity to a saved title also supported it";
  }

  if (
    evidence.some(
      (item) =>
        item === "shared:overlap_strength" || item === "shared:bridge_value",
    )
  ) {
    return "both taste profiles also supported it";
  }

  const genres = candidate.genres.filter(Boolean).slice(0, 2);
  if (genres.length === 2) {
    return `it's the ${genres[0]} and ${genres[1]} option in this five`;
  }
  if (genres.length === 1) {
    return `it's the ${genres[0]} option in this five`;
  }
  return "it remains one of tonight's five";
}

function evidenceValue(value: string, prefixes: string[]): string | null {
  const prefix = prefixes.find((candidate) => value.startsWith(candidate));
  if (!prefix) {
    return null;
  }
  const result = value.slice(prefix.length).trim();
  return result && !result.startsWith("avoid ") ? result : null;
}

function humanizeEvidenceValue(value: string): string {
  return value
    .replaceAll("_", " ")
    .replaceAll("/", " and ")
    .replace(/\s+/g, " ")
    .trim();
}

export function reactionScore(reaction: ReactionValue | undefined) {
  if (reaction === "interested") {
    return 18;
  }

  if (reaction === "maybe") {
    return 6;
  }

  if (reaction === "no") {
    return -34;
  }

  return 0;
}

export function countReactions(reactions: ReactionState): Record<ReactionValue, number> {
  return {
    interested: Object.values(reactions).filter((reaction) => reaction === "interested")
      .length,
    maybe: Object.values(reactions).filter((reaction) => reaction === "maybe").length,
    no: Object.values(reactions).filter((reaction) => reaction === "no").length,
  };
}

export function countSeenMemories(seenMemories: SeenMemoryState): number {
  return Object.values(seenMemories).filter((memory) => memory !== undefined).length;
}

export function mergeSeenMemoryIntoOnboarding(
  onboarding: ParticipantOnboardingPayload,
  candidate: DemoCandidate,
  memory: SeenMemoryValue,
): ParticipantOnboardingPayload {
  const nextLoved = removeTitleEntry(onboarding.lovedTitleEntries, candidate.id);
  const nextFine = removeTitleEntry(onboarding.fineTitleEntries, candidate.id);
  const nextNo = removeTitleEntry(onboarding.noTitleEntries, candidate.id);

  if (memory !== "forget") {
    const entry = toResolvedTitleEntry(candidate);
    if (memory === "loved") {
      nextLoved.unshift(entry);
    } else if (memory === "fine") {
      nextFine.unshift(entry);
    } else {
      nextNo.unshift(entry);
    }
  }

  return {
    ...onboarding,
    lovedTitleEntries: nextLoved,
    fineTitleEntries: nextFine,
    noTitleEntries: nextNo,
  };
}

export function removeTitleEntry(
  entries: ParticipantOnboardingPayload["lovedTitleEntries"],
  sourceId: string,
) {
  return entries.filter((entry) => entry.candidate?.sourceId !== sourceId);
}

export function toResolvedTitleEntry(candidate: DemoCandidate) {
  return {
    rawTitle: candidate.title,
    status: "resolved" as const,
    candidate: {
      source: "tmdb",
      sourceId: candidate.id,
      title: candidate.title,
      mediaType: "movie" as const,
      releaseYear: candidate.year,
      overview: candidate.reason,
    },
  };
}

export function toOnboardingDraft(
  onboarding: ParticipantOnboardingPayload,
): OnboardingDraft {
  return {
    lovedTitleEntries: onboarding.lovedTitleEntries,
    fineTitleEntries: onboarding.fineTitleEntries,
    noTitleEntries: onboarding.noTitleEntries,
    manualLoved: "",
    manualFine: "",
    manualNo: "",
  };
}

export function suggestedSeedsForBucket(
  bucket: "loved" | "fine" | "no",
): DemoCandidate[] {
  if (bucket === "loved") {
    return [
      demoCandidates.find((candidate) => candidate.id === "arrival"),
      demoCandidates.find((candidate) => candidate.id === "knives-out"),
    ].filter((candidate): candidate is DemoCandidate => candidate !== undefined);
  }

  if (bucket === "fine") {
    return [
      demoCandidates.find((candidate) => candidate.id === "the-grand-budapest-hotel"),
      demoCandidates.find((candidate) => candidate.id === "edge-of-tomorrow"),
    ].filter((candidate): candidate is DemoCandidate => candidate !== undefined);
  }

  return [
    demoCandidates.find((candidate) => candidate.id === "past-lives"),
  ].filter((candidate): candidate is DemoCandidate => candidate !== undefined);
}

export function bucketHint(bucket: "loved" | "fine" | "no"): string {
  if (bucket === "loved") {
    return "A movie they would happily watch again.";
  }

  if (bucket === "fine") {
    return "Something they thought was decent, not special.";
  }

  return "A clear no from past experience.";
}

export function removeSeedFromDraft(
  draft: OnboardingDraft,
  sourceId: string,
): OnboardingDraft {
  return {
    ...draft,
    lovedTitleEntries: removeTitleEntry(draft.lovedTitleEntries, sourceId),
    fineTitleEntries: removeTitleEntry(draft.fineTitleEntries, sourceId),
    noTitleEntries: removeTitleEntry(draft.noTitleEntries, sourceId),
  };
}

export function removeUnresolvedSeedFromDraft(
  draft: OnboardingDraft,
  rawTitle: string,
): OnboardingDraft {
  const normalizedTitle = rawTitle.trim().toLowerCase();
  const keepEntry = (
    entry: TitleResolutionEntry,
  ) => !(entry.candidate == null && entry.rawTitle.trim().toLowerCase() === normalizedTitle);

  return {
    ...draft,
    lovedTitleEntries: draft.lovedTitleEntries.filter(keepEntry),
    fineTitleEntries: draft.fineTitleEntries.filter(keepEntry),
    noTitleEntries: draft.noTitleEntries.filter(keepEntry),
  };
}

export function prependUniqueEntry(
  entries: ParticipantOnboardingPayload["lovedTitleEntries"],
  entry: TitleResolutionEntry,
) {
  const key = entryKey(entry);
  return [entry, ...entries.filter((currentEntry) => entryKey(currentEntry) !== key)];
}

export function entryKey(entry: TitleResolutionEntry): string {
  return entry.candidate?.sourceId ?? `raw:${entry.rawTitle.trim().toLowerCase()}`;
}

export function reactionsPayload(
  candidates: DemoCandidate[],
  reactions: ReactionState,
) {
  return candidates.map((candidate) => ({
    sourceMovieId: candidate.id,
    reactionLabel: reactions[candidate.id] ?? "maybe",
  }));
}

export function toSessionCandidate(
  candidate: ShortlistCandidatePayload,
  index: number,
): CandidateViewModel {
  const fixture = candidate.sourceMovieId.startsWith("tmdb:")
    ? undefined
    : demoCandidates.find(
    (demoCandidate) =>
      demoCandidate.id === candidate.sourceMovieId ||
      demoCandidate.title.toLowerCase() === candidate.title.toLowerCase(),
  );
  const rank = candidate.candidateRank || index + 1;
  const groupScore = candidate.groupScore ?? 72;
  const runtime =
    candidate.runtime ??
    (candidate.runtimeMin ? formatRuntime(candidate.runtimeMin) : null);
  const availability =
    candidate.availability ??
    (candidate.providerNames && candidate.providerNames.length > 0
      ? `${candidate.providerNames.join(", ")}`
      : null);

  const provenance: CandidateProvenance = {
    poster: candidate.posterUrl
      ? "api-payload"
      : fixture?.posterUrl
        ? "local-demo-asset"
        : "fallback-placeholder",
    criticScore: fixture?.criticScore === undefined ? "not-provided" : "demo-fixture",
    descriptiveCopy:
      candidate.reason || candidate.whyShort
        ? "api-payload"
        : fixture?.reason
          ? "local-demo-fixture"
          : "generic-fallback",
  };

  return {
    id: candidate.sourceMovieId,
    title: candidate.title,
    year:
      candidate.year ??
      candidate.releaseYear ??
      fixture?.year ??
      new Date().getFullYear(),
    runtime: runtime ?? fixture?.runtime ?? "Runtime check needed",
    posterUrl: candidate.posterUrl ?? fixture?.posterUrl ?? fallbackPosterUrl,
    backdropUrl: candidate.backdropUrl ?? fixture?.backdropUrl,
    providerUrl: candidate.providerUrl ?? fixture?.providerUrl,
    topCast:
      candidate.topCast?.slice(0, 3) ??
      fixture?.topCast ??
      [],
    castDetails:
      candidate.castDetails?.slice(0, 3).map((member) => ({
        name: member.name,
        character: member.character ?? undefined,
        profileUrl: member.profileUrl ?? undefined,
      })) ??
      fixture?.castDetails?.slice(0, 3),
    matchedPersonNames:
      candidate.matchedPersonNames?.slice(0, 3) ??
      fixture?.matchedPersonNames,
    genres: candidate.genres ?? fixture?.genres ?? [],
    criticScore: fixture?.criticScore,
    safePickStatus: toSafePickStatus(candidate.safePickStatus),
    availability: availability ?? fixture?.availability ?? "Availability check needed",
    providerAvailability:
      candidate.providerAvailability?.length > 0
        ? candidate.providerAvailability
        : fixture?.providerAvailability,
    languageAccess:
      candidate.languageAccess ??
      fixture?.languageAccess ??
      "Audio and subtitle details need a quick check",
    tone: candidate.tone ?? candidate.fitBucket ?? fixture?.tone ?? "Balanced pick",
    reason:
      sanitizeNarrativeCopy(candidate.reason) ??
      fixture?.reason ??
      "Picked for tonight's shortlist based on the current household setup.",
    overview:
      sanitizeNarrativeCopy(candidate.overview) ??
      candidate.overview ??
      fixture?.overview ??
      sanitizeNarrativeCopy(candidate.reason) ??
      fixture?.reason,
    hook: fixture?.hook,
    whyNow: fixture?.whyNow,
    groupScore: candidate.groupScore ?? undefined,
    dominantPositiveEvidence:
      candidate.dominantPositiveEvidence ?? fixture?.dominantPositiveEvidence,
    dominantPenalties:
      candidate.dominantPenalties ?? fixture?.dominantPenalties,
    baseRank: rank,
    taste: {
      founder: candidate.founderScore ?? fixture?.taste.founder ?? groupScore,
      wife: candidate.wifeScore ?? fixture?.taste.wife ?? groupScore,
    },
    provenance,
  };
}

export function toRecoverySessionCandidate(
  candidate: RecoveryMovieDisplayPayload,
  index: number,
): CandidateViewModel {
  return {
    id: candidate.sourceMovieId,
    title: candidate.title,
    year: candidate.year ?? new Date().getFullYear(),
    runtime: candidate.runtimeLabel ?? "Runtime check needed",
    posterUrl: candidate.posterUrl ?? fallbackPosterUrl,
    backdropUrl: candidate.backdropUrl ?? undefined,
    providerUrl: candidate.providerUrl ?? undefined,
    topCast: (candidate.cast ?? []).map((member) => member.name),
    castDetails: (candidate.cast ?? []).map((member) => ({
      name: member.name,
      character: member.character ?? undefined,
      profileUrl: member.profileUrl ?? undefined,
    })),
    providerAvailability: candidate.providers ?? [],
    matchedPersonNames: candidate.matchedPersonNames ?? [],
    genres: candidate.genres ?? [],
    safePickStatus: candidate.safePickStatus ?? "Safe Pick",
    availability: candidate.availability ?? "Availability check needed",
    languageAccess:
      candidate.languageAccess
      ?? "Audio and subtitle details need a quick check",
    tone: candidate.tone ?? "Balanced pick",
    reason: "Recovered from tonight’s private shortlist.",
    overview: candidate.synopsis || undefined,
    groupScore: 0.72,
    dominantPositiveEvidence: candidate.positiveEvidence,
    dominantPenalties: candidate.penalties,
    baseRank: index + 1,
    taste: { founder: 72, wife: 72 },
    provenance: {
      poster: candidate.posterUrl ? "api-payload" : "fallback-placeholder",
      criticScore: "not-provided",
      descriptiveCopy: candidate.synopsis ? "api-payload" : "generic-fallback",
    },
  };
}

export function toSafePickStatus(
  value: string | null | undefined,
): DemoCandidate["safePickStatus"] {
  return value === "Needs Quick Check" ? "Needs Quick Check" : "Safe Pick";
}

export function createSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `session-${Date.now().toString(36)}`;
}

export function formatRuntime(runtimeMin: number): string {
  const hours = Math.floor(runtimeMin / 60);
  const minutes = runtimeMin % 60;

  if (hours === 0) {
    return `${minutes}m`;
  }

  return `${hours}h ${minutes}m`;
}

export function titleForSourceMovieId(
  shortlist: { sourceMovieId: string; title: string }[],
  sourceMovieId: string | null,
): string | null {
  if (sourceMovieId === null) {
    return null;
  }

  return (
    shortlist.find((candidate) => candidate.sourceMovieId === sourceMovieId)?.title ??
    null
  );
}

export function toDebugHistoryErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return `${error.message} Debug evidence is unavailable.`;
  }

  return "Debug history could not be loaded.";
}

export function formatDebugCandidateInput(
  candidate: DebugHistoryCandidateInputPayload,
): string {
  const providers =
    candidate.providers.length > 0 ? candidate.providers.join(", ") : "No providers";
  const genres = candidate.genres.length > 0 ? candidate.genres.join(", ") : "No genres";
  const watchState = candidate.alreadyWatched ? "watched" : "not watched";
  const interesting = candidate.isInterestingSafePick ? ", interesting safe pick" : "";

  return `${candidate.title}: ${candidate.safetyStatus}, ${watchState}${interesting}. Providers: ${providers}. Genres: ${genres}.`;
}

export function formatDebugSnapshotCandidate(
  candidate: DebugHistoryRecommendationCandidatePayload,
): string {
  const userScores = candidate.userScores
    .map((score) => `${score.userId} ${score.score}`)
    .join(", ");
  const interestingPick = candidate.isInterestingPick ? ", interesting" : "";
  const dominantPositiveEvidence = candidate.dominantPositiveEvidence ?? [];
  const dominantPenalties = candidate.dominantPenalties ?? [];
  const positiveEvidence =
    dominantPositiveEvidence.length > 0
      ? ` Positive: ${dominantPositiveEvidence.slice(0, 3).join(", ")}.`
      : "";
  const penaltyEvidence =
    dominantPenalties.length > 0
      ? ` Penalties: ${dominantPenalties.slice(0, 3).join(", ")}.`
      : "";

  return `${candidate.candidateRank}. ${candidate.title}: ${candidate.groupScore} group, ${candidate.fitBucket}, ${userScores}${interestingPick}. ${candidate.whyShort}${positiveEvidence}${penaltyEvidence}`;
}
