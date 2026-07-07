import type {
  DebugHistoryCandidateInputPayload,
  DebugHistoryRecommendationCandidatePayload,
  ParticipantOnboardingPayload,
  ShortlistCandidatePayload,
} from "./session-client";
import { demoCandidates, type DemoCandidate, type ReactionValue, type SessionMode } from "./session-fixtures";
import type {
  CandidateProvenance,
  CandidateViewModel,
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
  const localRanked = candidates
    .map((candidate) => {
      const founderReaction = founderReactions[candidate.id];
      const wifeReaction = wifeReactions[candidate.id];
      const founderScore = candidate.taste.founder + reactionScore(founderReaction);
      const wifeScore = candidate.taste.wife + reactionScore(wifeReaction);
      const noPenalty =
        founderReaction === "no" || wifeReaction === "no"
          ? sessionMode === "compromise"
            ? 38
            : 24
          : 0;
      const statusPenalty = candidate.safePickStatus === "Needs Quick Check" ? 14 : 0;
      const modeScore =
        peopleMode === "founder"
          ? founderScore
          : peopleMode === "wife"
            ? wifeScore
            : sessionMode === "founder-first"
              ? founderScore * 0.58 + wifeScore * 0.42
              : sessionMode === "wife-first"
                ? founderScore * 0.42 + wifeScore * 0.58
                : Math.min(founderScore, wifeScore) * 0.65 +
                  ((founderScore + wifeScore) / 2) * 0.35;

      return {
        ...candidate,
        score: Math.max(
          0,
          Math.round(
            modeScore -
              statusPenalty -
              (peopleMode === "couple" ? noPenalty : 0),
          ),
        ),
      };
    })
    .sort((first, second) => {
      if (second.score !== first.score) {
        return second.score - first.score;
      }

      return first.baseRank - second.baseRank;
    });

  if (rerankedSourceMovieIds.length === 0) {
    return localRanked;
  }

  const apiRankById = new Map(
    rerankedSourceMovieIds.map((sourceMovieId, index) => [sourceMovieId, index]),
  );

  return localRanked
    .slice()
    .sort(
      (first, second) =>
        (apiRankById.get(first.id) ?? Number.MAX_SAFE_INTEGER) -
        (apiRankById.get(second.id) ?? Number.MAX_SAFE_INTEGER),
    );
}

export function toMatchTier(score: number): "Epic" | "Strong" | "Warm" {
  if (score >= 95) {
    return "Epic";
  }

  if (score >= 85) {
    return "Strong";
  }

  return "Warm";
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
  if (peopleMode !== "couple") {
    if (candidate.whyNow) {
      return candidate.whyNow;
    }

    return `${candidate.title} rises because it matches the pace and tone this session leaned toward tonight.`;
  }

  if (founderReaction === "interested" && wifeReaction === "interested") {
    return `${founderLabel} and ${wifeLabel} both pushed this up, and the ${candidate.tone.toLowerCase()} energy makes it easy to start right now.`;
  }

  if (founderReaction === "interested" || wifeReaction === "interested") {
    return `One of you really wanted this, the other didn’t block it, and ${candidate.title} still looks like a strong shared bet for tonight.`;
  }

  if (candidate.criticScore && candidate.criticScore >= 94) {
    return `Neither of you spiked hard on it, but the trust signal is high and ${candidate.title} still looks like the cleanest overlap.`;
  }

  return `This one balances tonight’s overlap best: approachable pace, strong payoff, and fewer reasons for either of you to bounce off.`;
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
  memory: Exclude<SeenMemoryValue, "forget">,
): ParticipantOnboardingPayload {
  const nextLoved = removeTitleEntry(onboarding.lovedTitleEntries, candidate.id);
  const nextFine = removeTitleEntry(onboarding.fineTitleEntries, candidate.id);
  const nextNo = removeTitleEntry(onboarding.noTitleEntries, candidate.id);
  const entry = toResolvedTitleEntry(candidate);

  if (memory === "loved") {
    nextLoved.unshift(entry);
  } else if (memory === "fine") {
    nextFine.unshift(entry);
  } else {
    nextNo.unshift(entry);
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
  const fixture = demoCandidates.find(
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
    topCast:
      candidate.topCast?.slice(0, 3) ??
      fixture?.topCast ??
      [],
    matchedPersonNames:
      candidate.matchedPersonNames?.slice(0, 3) ??
      fixture?.matchedPersonNames,
    genres: candidate.genres ?? fixture?.genres ?? [],
    criticScore: fixture?.criticScore,
    safePickStatus: toSafePickStatus(candidate.safePickStatus),
    availability: availability ?? fixture?.availability ?? "Availability check needed",
    languageAccess:
      candidate.languageAccess ??
      fixture?.languageAccess ??
      "Audio and subtitle details need a quick check",
    tone: candidate.tone ?? candidate.fitBucket ?? fixture?.tone ?? "Balanced pick",
    reason:
      candidate.reason ??
      fixture?.reason ??
      "Picked for tonight's shortlist based on the current household setup.",
    hook: fixture?.hook,
    whyNow: fixture?.whyNow,
    baseRank: rank,
    taste: {
      founder: candidate.founderScore ?? fixture?.taste.founder ?? groupScore,
      wife: candidate.wifeScore ?? fixture?.taste.wife ?? groupScore,
    },
    provenance,
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

export function toErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return `${error.message} Continuing in demo mode.`;
  }

  return "Session API failed. Continuing in demo mode.";
}

export function toSessionCreationErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    if (error.message.includes("completed onboarding")) {
      return "Shared profile setup is not wired into the phone flow yet, so this round is using the same shortlist in local mode.";
    }

    return error.message;
  }

  return "Session setup could not be saved to the API.";
}

export function toSeenMemoryErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "Seen-memory save failed.";
}

export function toOnboardingErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "Onboarding could not be loaded.";
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

  return `${candidate.candidateRank}. ${candidate.title}: ${candidate.groupScore} group, ${candidate.fitBucket}, ${userScores}${interestingPick}. ${candidate.whyShort}`;
}
