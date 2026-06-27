"use client";

import type { ReactionValue, SessionMode } from "./session-fixtures";

export type ApiSessionMode = "compromise" | "husband_first" | "wife_first";

export type SharedSessionPayload = {
  sessionId: string;
  householdId: string;
  activeMode: ApiSessionMode;
  participantIds: string[];
  state: "founder_reacting" | "handoff" | "wife_reacting" | "reranked";
  shortlist: SessionShortlistItemPayload[];
  founderReactions: SessionReactionPayload[];
  wifeReactions: SessionReactionPayload[];
  rerankedSourceMovieIds: string[];
  bestPickSourceMovieId: string | null;
};

export type SessionShortlistItemPayload = {
  sourceMovieId: string;
  title: string;
  candidateRank: number;
};

export type SessionReactionPayload = {
  sourceMovieId: string;
  reactionLabel: ReactionValue;
};

export type DebugHistorySessionPayload = {
  sessionId: string;
  householdId: string;
  activeMode: ApiSessionMode;
  state: string;
  participantIds: string[];
  shortlist: SessionShortlistItemPayload[];
  founderReactions: DebugHistoryReactionPayload[];
  wifeReactions: DebugHistoryReactionPayload[];
  rerankedSourceMovieIds: string[];
  bestPickSourceMovieId: string | null;
  postWatchFeedback: DebugHistoryFeedbackPayload[];
  recommendationSnapshot: DebugHistoryRecommendationSnapshotPayload | null;
  unavailableEvidence: string[];
};

export type DebugHistoryReactionPayload = {
  participantId: string;
  sourceMovieId: string;
  reactionLabel: string;
};

export type DebugHistoryFeedbackPayload = {
  userId: string;
  sourceMovieId: string;
  feedbackLabel: string;
  hasFreeTextNote: boolean;
};

export type DebugHistoryUserScorePayload = {
  userId: string;
  score: number;
};

export type DebugHistoryRecommendationCandidatePayload = {
  sourceMovieId: string;
  title: string;
  candidateRank: number;
  fitBucket: string;
  groupScore: number;
  userScores: DebugHistoryUserScorePayload[];
  whyShort: string;
  hardFilterPass: boolean;
  isInterestingPick: boolean;
};

export type DebugHistoryRecommendationSnapshotPayload = {
  sessionId: string;
  candidates: DebugHistoryRecommendationCandidatePayload[];
  isUncertain: boolean;
  uncertaintyReason: string | null;
  recommendedFollowUp: string | null;
  interestingSafePickId: string | null;
};

export type CreateSessionRequest = {
  householdId: string;
  activeMode: ApiSessionMode;
  participantIds: string[];
  shortlist: SessionShortlistItemPayload[];
};

export type SubmitReactionsRequest = {
  participantId: string;
  reactions: SessionReactionPayload[];
};

export function toApiSessionMode(mode: SessionMode): ApiSessionMode {
  if (mode === "founder-first") {
    return "husband_first";
  }

  if (mode === "wife-first") {
    return "wife_first";
  }

  return "compromise";
}

export async function createSharedSession(
  request: CreateSessionRequest,
): Promise<SharedSessionPayload> {
  return postJson("/api/session", request);
}

export async function submitSessionReactions(
  sessionId: string,
  request: SubmitReactionsRequest,
): Promise<SharedSessionPayload> {
  return postJson(`/api/session/${encodeURIComponent(sessionId)}/reactions`, request);
}

export async function advanceSessionHandoff(
  sessionId: string,
): Promise<SharedSessionPayload> {
  return postJson(`/api/session/${encodeURIComponent(sessionId)}/advance-handoff`, {});
}

export async function getSessionDebugHistory(
  sessionId: string,
): Promise<DebugHistorySessionPayload> {
  return getJson(
    `/api/session/${encodeURIComponent(sessionId)}/debug-history`,
  );
}

async function postJson<TResponse>(
  url: string,
  body: unknown,
): Promise<TResponse> {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  const payload = (await response.json().catch(() => null)) as unknown;

  if (!response.ok) {
    throw new Error(parseApiError(payload, response.status));
  }

  return payload as TResponse;
}

async function getJson<TResponse>(url: string): Promise<TResponse> {
  const response = await fetch(url, {
    method: "GET",
  });

  const payload = (await response.json().catch(() => null)) as unknown;

  if (!response.ok) {
    throw new Error(parseApiError(payload, response.status));
  }

  return payload as TResponse;
}

function parseApiError(payload: unknown, status: number): string {
  if (
    typeof payload === "object" &&
    payload !== null &&
    "detail" in payload &&
    typeof payload.detail === "string"
  ) {
    return payload.detail;
  }

  return `Session API returned HTTP ${status}.`;
}
