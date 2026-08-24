import type {
  RecoveryMovieDisplayPayload,
  RecoveryReactionPayload,
} from "../api-contract.generated.ts";
import type { SharedSessionPayload } from "../session-client.ts";
import { toRecoverySessionCandidate } from "../pass-the-phone-helpers.ts";
import type {
  CandidateViewModel,
  ReactionState,
} from "../pass-the-phone-model.ts";

type CanonicalShortlistItem = SharedSessionPayload["shortlist"][number];

export type CanonicalResultInputs = {
  candidates: CandidateViewModel[];
  founderReactions: ReactionState;
  wifeReactions: ReactionState;
};

export function canonicalRecoveryCandidates(
  displaySnapshot: RecoveryMovieDisplayPayload[],
  canonicalShortlist: CanonicalShortlistItem[],
): CandidateViewModel[] {
  requireFive(displaySnapshot, "display snapshot");
  requireFive(canonicalShortlist, "canonical shortlist");

  const scoreById = new Map(
    canonicalShortlist.map((item) => {
      if (
        typeof item.profileScore !== "number"
        || !Number.isFinite(item.profileScore)
        || item.profileScore < 0
        || item.profileScore > 1
      ) {
        throw new Error("The verified result is missing a canonical profile score.");
      }
      return [item.sourceMovieId, item.profileScore] as const;
    }),
  );
  requireSameMovieIds(
    displaySnapshot.map((item) => item.sourceMovieId),
    canonicalShortlist.map((item) => item.sourceMovieId),
    "The verified result does not match the canonical shortlist.",
  );

  return displaySnapshot.map((candidate, index) => {
    const profileScore = scoreById.get(candidate.sourceMovieId);
    if (profileScore === undefined) {
      throw new Error("The verified result is missing a canonical profile score.");
    }
    return toRecoverySessionCandidate(candidate, index, profileScore);
  });
}

export function canonicalSecondPassInputs({
  displaySnapshot,
  session,
}: {
  displaySnapshot: RecoveryMovieDisplayPayload[];
  session: SharedSessionPayload;
}): Omit<CanonicalResultInputs, "wifeReactions"> {
  if (
    session.state !== "wife_reacting"
    || session.founderReactions.length !== 5
    || session.wifeReactions.length !== 0
  ) {
    throw new Error("The verified second pass is not ready.");
  }
  requireBallotIds(session.founderReactions, session.shortlist, "founder");
  return {
    candidates: canonicalRecoveryCandidates(displaySnapshot, session.shortlist),
    founderReactions: toReactionState(session.founderReactions),
  };
}

export function canonicalResultInputs({
  displaySnapshot,
  finalReactions,
  session,
}: {
  displaySnapshot: RecoveryMovieDisplayPayload[];
  finalReactions: RecoveryReactionPayload[];
  session: SharedSessionPayload;
}): CanonicalResultInputs {
  if (
    session.state !== "reranked"
    || session.founderReactions.length !== 5
    || session.wifeReactions.length !== 5
    || finalReactions.length !== 5
    || session.rerankedShortlist.length !== 5
    || session.rerankedSourceMovieIds.length !== 5
  ) {
    throw new Error("The verified result is not ready. Both complete ballots and a server rerank are required.");
  }

  requireBallotIds(session.founderReactions, session.shortlist, "founder");
  requireBallotIds(session.wifeReactions, session.shortlist, "partner");
  requireSameMovieIds(
    finalReactions.map((item) => item.sourceMovieId),
    session.wifeReactions.map((item) => item.sourceMovieId),
    "The sealed final ballot does not match the server ballot.",
  );
  requireSameMovieIds(
    displaySnapshot.map((item) => item.sourceMovieId),
    session.rerankedSourceMovieIds,
    "The verified result order does not match the server rerank.",
    true,
  );

  const canonicalWifeBallot = new Map(
    session.wifeReactions.map((item) => [item.sourceMovieId, item.reactionLabel]),
  );
  for (const item of finalReactions) {
    if (canonicalWifeBallot.get(item.sourceMovieId) !== item.reaction) {
      throw new Error("The sealed final ballot does not match the server ballot.");
    }
  }

  return {
    candidates: canonicalRecoveryCandidates(
      displaySnapshot,
      session.rerankedShortlist,
    ),
    founderReactions: toReactionState(session.founderReactions),
    wifeReactions: toReactionState(session.wifeReactions),
  };
}

export function canonicalSharedResultReady(
  session: SharedSessionPayload | null,
): boolean {
  if (
    session === null
    || session.state !== "reranked"
    || session.founderReactions.length !== 5
    || session.wifeReactions.length !== 5
    || session.rerankedSourceMovieIds.length !== 5
  ) {
    return false;
  }
  try {
    requireBallotIds(session.founderReactions, session.shortlist, "founder");
    requireBallotIds(session.wifeReactions, session.shortlist, "partner");
    return true;
  } catch {
    return false;
  }
}

function toReactionState(
  reactions: Array<{
    sourceMovieId: string;
    reactionLabel: "interested" | "maybe" | "no" | "seen";
  }>,
): ReactionState {
  return Object.fromEntries(
    reactions.map((item) => [
      item.sourceMovieId,
      item.reactionLabel === "seen" ? "maybe" : item.reactionLabel,
    ]),
  );
}

function requireBallotIds(
  reactions: Array<{ sourceMovieId: string }>,
  shortlist: Array<{ sourceMovieId: string }>,
  actor: string,
): void {
  requireSameMovieIds(
    reactions.map((item) => item.sourceMovieId),
    shortlist.map((item) => item.sourceMovieId),
    `The verified ${actor} ballot does not match the canonical shortlist.`,
  );
}

function requireSameMovieIds(
  actual: string[],
  expected: string[],
  message: string,
  ordered = false,
): void {
  const matches = ordered
    ? actual.length === expected.length
      && actual.every((value, index) => value === expected[index])
    : actual.length === expected.length
      && new Set(actual).size === actual.length
      && actual.every((value) => expected.includes(value));
  if (!matches) throw new Error(message);
}

function requireFive(value: unknown[], label: string): void {
  if (value.length !== 5) {
    throw new Error(`The verified ${label} must contain exactly five movies.`);
  }
}
