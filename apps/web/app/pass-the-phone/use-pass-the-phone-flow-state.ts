"use client";

import { useState } from "react";

import type {
  DebugHistoryStatus,
  SessionSource,
  SyncStatus,
} from "../pass-the-phone-model";
import type {
  DebugHistorySessionPayload,
  RecentSessionSummaryPayload,
  SharedSessionPayload,
  TasteProfileSummaryPayload,
  TonightIntentInterpretationPayload,
} from "../session-client";

type SessionFlowState = {
  sessionSource: SessionSource;
  recommendationSource: string;
  syncStatus: SyncStatus;
  apiError: string | null;
  sharedSession: SharedSessionPayload | null;
  liveSessionId: string | null;
  shownSourceMovieIds: string[];
};

type TonightIntentFlowState = {
  text: string;
  clarificationText: string;
  pendingIntent: TonightIntentInterpretationPayload | null;
  activeIntents: TonightIntentInterpretationPayload[];
  status: SyncStatus;
  message: string | null;
};

type ResultsFlowState = {
  steerText: string;
  steerClarificationText: string;
  pendingSteerIntent: TonightIntentInterpretationPayload | null;
  steerMessage: string | null;
  debugHistory: DebugHistorySessionPayload | null;
  tasteProfileSummaries: TasteProfileSummaryPayload[];
  debugHistoryStatus: DebugHistoryStatus;
  debugHistoryMessage: string | null;
};

type HistoryPanelState = {
  recentSessions: RecentSessionSummaryPayload[];
  recentSessionsStatus: DebugHistoryStatus;
  recentSessionsMessage: string | null;
  selectedHistory: DebugHistorySessionPayload | null;
  selectedHistoryStatus: DebugHistoryStatus;
  selectedHistoryMessage: string | null;
};

type PassThePhoneFlowStateOptions = {
  apiConnected: boolean;
};

const DISCONNECTED_SESSION_MESSAGE =
  "Live session sync is unavailable, so tonight is running in local mode.";
const DEMO_DEBUG_HISTORY_MESSAGE =
  "Debug evidence is unavailable because the session fell back to demo mode.";
const BACKEND_DEBUG_HISTORY_MESSAGE =
  "Debug evidence is only available for backend-backed sessions.";
const RECENT_HISTORY_UNAVAILABLE_MESSAGE =
  "Recent history is only available when the backend API is connected.";

function initialSessionFlowState(apiConnected: boolean): SessionFlowState {
  return {
    sessionSource: apiConnected ? "api" : "demo",
    recommendationSource: "demo",
    syncStatus: "ready",
    apiError: apiConnected ? null : DISCONNECTED_SESSION_MESSAGE,
    sharedSession: null,
    liveSessionId: null,
    shownSourceMovieIds: [],
  };
}

function initialTonightIntentFlowState(): TonightIntentFlowState {
  return {
    text: "",
    clarificationText: "",
    pendingIntent: null,
    activeIntents: [],
    status: "ready",
    message: null,
  };
}

function initialResultsFlowState(): ResultsFlowState {
  return {
    steerText: "",
    steerClarificationText: "",
    pendingSteerIntent: null,
    steerMessage: null,
    debugHistory: null,
    tasteProfileSummaries: [],
    debugHistoryStatus: "idle",
    debugHistoryMessage: null,
  };
}

function initialHistoryPanelState(): HistoryPanelState {
  return {
    recentSessions: [],
    recentSessionsStatus: "idle",
    recentSessionsMessage: null,
    selectedHistory: null,
    selectedHistoryStatus: "idle",
    selectedHistoryMessage: null,
  };
}

function resolvePatch<TState>(
  current: TState,
  patch:
    | Partial<TState>
    | ((current: TState) => Partial<TState>),
): TState {
  const nextPatch = typeof patch === "function" ? patch(current) : patch;
  return { ...current, ...nextPatch };
}

export function usePassThePhoneFlowState({
  apiConnected,
}: PassThePhoneFlowStateOptions) {
  const [session, setSessionState] = useState<SessionFlowState>(() =>
    initialSessionFlowState(apiConnected),
  );
  const [tonightIntent, setTonightIntentState] = useState<TonightIntentFlowState>(
    initialTonightIntentFlowState,
  );
  const [results, setResultsState] = useState<ResultsFlowState>(
    initialResultsFlowState,
  );
  const [historyPanel, setHistoryPanelState] = useState<HistoryPanelState>(
    initialHistoryPanelState,
  );

  function patchSession(
    patch:
      | Partial<SessionFlowState>
      | ((current: SessionFlowState) => Partial<SessionFlowState>),
  ): void {
    setSessionState((current) => resolvePatch(current, patch));
  }

  function patchTonightIntent(
    patch:
      | Partial<TonightIntentFlowState>
      | ((current: TonightIntentFlowState) => Partial<TonightIntentFlowState>),
  ): void {
    setTonightIntentState((current) => resolvePatch(current, patch));
  }

  function patchResults(
    patch:
      | Partial<ResultsFlowState>
      | ((current: ResultsFlowState) => Partial<ResultsFlowState>),
  ): void {
    setResultsState((current) => resolvePatch(current, patch));
  }

  function patchHistoryPanel(
    patch:
      | Partial<HistoryPanelState>
      | ((current: HistoryPanelState) => Partial<HistoryPanelState>),
  ): void {
    setHistoryPanelState((current) => resolvePatch(current, patch));
  }

  function resetAllFlowState(): void {
    setSessionState(initialSessionFlowState(apiConnected));
    setTonightIntentState(initialTonightIntentFlowState());
    setResultsState(initialResultsFlowState());
    setHistoryPanelState(initialHistoryPanelState());
  }

  function resetSessionProgress(): void {
    setSessionState((current) => ({
      ...current,
      sessionSource: apiConnected ? "api" : "demo",
      recommendationSource: "demo",
      syncStatus: "ready",
      apiError: apiConnected ? null : DISCONNECTED_SESSION_MESSAGE,
      sharedSession: null,
      liveSessionId: null,
      shownSourceMovieIds: [],
    }));
    setResultsState((current) => ({
      ...current,
      debugHistory: null,
      tasteProfileSummaries: [],
      debugHistoryStatus: "idle",
      debugHistoryMessage: null,
      steerText: "",
      steerClarificationText: "",
      pendingSteerIntent: null,
      steerMessage: null,
    }));
  }

  function setDemoDebugFallback(): void {
    patchSession({ sessionSource: "demo" });
    patchResults({
      debugHistoryStatus: "failed",
      debugHistoryMessage: DEMO_DEBUG_HISTORY_MESSAGE,
    });
  }

  return {
    session,
    tonightIntent,
    results,
    historyPanel,
    patchSession,
    patchTonightIntent,
    patchResults,
    patchHistoryPanel,
    resetAllFlowState,
    resetSessionProgress,
    setDemoDebugFallback,
    messages: {
      disconnectedSession: DISCONNECTED_SESSION_MESSAGE,
      demoDebugFallback: DEMO_DEBUG_HISTORY_MESSAGE,
      backendDebugHistoryOnly: BACKEND_DEBUG_HISTORY_MESSAGE,
      recentHistoryUnavailable: RECENT_HISTORY_UNAVAILABLE_MESSAGE,
    },
  };
}
