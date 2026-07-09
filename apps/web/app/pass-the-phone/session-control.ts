"use client";

import { useState } from "react";
import type {
  CandidateViewModel,
  ReactionState,
  SeenMemoryPromptState,
  SeenMemoryState,
} from "../pass-the-phone-model";
import type {
  ScoringSessionReactionPayload,
  SharedSessionPayload,
  TonightIntentInterpretationPayload,
} from "../session-client";

export function scoringReactionSignals(
  session: SharedSessionPayload,
): ScoringSessionReactionPayload[] {
  const titlesBySourceId = new Map(
    [...session.previousShortlist, ...session.shortlist].map((item) => [
      item.sourceMovieId,
      item.title,
    ]),
  );
  return [
    ...session.previousFounderReactions,
    ...session.previousWifeReactions,
    ...session.founderReactions,
    ...session.wifeReactions,
  ].map((reaction) => ({
    ...reaction,
    title: titlesBySourceId.get(reaction.sourceMovieId) ?? null,
  }));
}

export function scoringReactionSignalsFromLocal({
  sessionId,
  participantId,
  candidates,
  reactions,
}: {
  sessionId: string;
  participantId: string;
  candidates: CandidateViewModel[];
  reactions: ReactionState;
}): ScoringSessionReactionPayload[] {
  return candidates
    .filter((candidate) => reactions[candidate.id] !== undefined)
    .map((candidate) => ({
      sourceMovieId: candidate.id,
      reactionLabel: reactions[candidate.id]!,
      title: candidate.title,
    }));
}

export function sessionShortlistFromCandidates(candidates: CandidateViewModel[]) {
  return candidates.map((candidate, index) => ({
    sourceMovieId: candidate.id,
    title: candidate.title,
    candidateRank: index + 1,
    profileScore: Math.max(0, Math.min(1, candidate.groupScore ?? 0)),
  }));
}

export function continuationExcludedSourceMovieIds(
  session: SharedSessionPayload,
  currentCandidates: CandidateViewModel[],
): string[] {
  return session.shownSourceMovieIds.length > 0
    ? session.shownSourceMovieIds
    : currentCandidates.map((candidate) => candidate.id);
}

export function latestTonightIntent(
  tonightIntents: TonightIntentInterpretationPayload[],
): TonightIntentInterpretationPayload | null {
  return tonightIntents.length > 0
    ? tonightIntents[tonightIntents.length - 1]
    : null;
}

export function usePassThePhoneSessionControl(
  initialCandidates: CandidateViewModel[],
) {
  const [founderIndex, setFounderIndex] = useState(0);
  const [wifeIndex, setWifeIndex] = useState(0);
  const [sessionCandidates, setSessionCandidates] =
    useState<CandidateViewModel[]>(initialCandidates);
  const [founderReactions, setFounderReactions] = useState<ReactionState>({});
  const [wifeReactions, setWifeReactions] = useState<ReactionState>({});
  const [founderSeenMemories, setFounderSeenMemories] = useState<SeenMemoryState>({});
  const [wifeSeenMemories, setWifeSeenMemories] = useState<SeenMemoryState>({});
  const [seenMemoryPrompt, setSeenMemoryPrompt] =
    useState<SeenMemoryPromptState>(null);

  function resetBatch(nextCandidates = initialCandidates): void {
    setFounderIndex(0);
    setWifeIndex(0);
    setSessionCandidates(nextCandidates);
    setFounderReactions({});
    setWifeReactions({});
    setFounderSeenMemories({});
    setWifeSeenMemories({});
    setSeenMemoryPrompt(null);
  }

  return {
    founderIndex,
    setFounderIndex,
    wifeIndex,
    setWifeIndex,
    sessionCandidates,
    setSessionCandidates,
    founderReactions,
    setFounderReactions,
    wifeReactions,
    setWifeReactions,
    founderSeenMemories,
    setFounderSeenMemories,
    wifeSeenMemories,
    setWifeSeenMemories,
    seenMemoryPrompt,
    setSeenMemoryPrompt,
    resetBatch,
  };
}
