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
