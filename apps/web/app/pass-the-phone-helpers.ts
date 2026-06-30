import type {
  DebugHistoryCandidateInputPayload,
  DebugHistoryRecommendationCandidatePayload,
  ParticipantOnboardingPayload,
  ShortlistCandidatePayload,
} from "./session-client";
import { demoCandidates, type DemoCandidate, type ReactionValue, type SessionMode } from "./session-fixtures";
import type {
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
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 342 513'%3E%3Crect width='342' height='513' fill='%23e1eef2'/%3E%3Crect x='42' y='78' width='258' height='357' rx='18' fill='%23ffffff' stroke='%23245f73' stroke-width='8'/%3E%3Ccircle cx='126' cy='184' r='32' fill='%23245f73'/%3E%3Ccircle cx='216' cy='184' r='32' fill='%23245f73'/%3E%3Cpath d='M102 306h138' stroke='%23245f73' stroke-width='16' stroke-linecap='round'/%3E%3C/svg%3E";

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
  candidates: DemoCandidate[];
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
): DemoCandidate {
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
    genres: fixture?.genres ?? [],
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
