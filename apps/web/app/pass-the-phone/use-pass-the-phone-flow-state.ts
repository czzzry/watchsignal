"use client";

import { useReducer } from "react";

import {
  createPassThePhoneFlowState,
  passThePhoneFlowReducer,
  type HistoryPanelState,
  type ResultsFlowState,
  type SessionFlowState,
  type TonightIntentFlowState,
} from "./pass-the-phone-flow-reducer";

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

export function usePassThePhoneFlowState({
  apiConnected,
}: PassThePhoneFlowStateOptions) {
  const [state, dispatch] = useReducer(
    passThePhoneFlowReducer,
    apiConnected,
    createPassThePhoneFlowState,
  );

  function updateSession(
    updates: Partial<Omit<SessionFlowState, "syncStatus">>,
  ): void {
    dispatch({ type: "session.updated", updates });
  }

  function startSessionSync(status: "loading" | "saving"): void {
    dispatch({ type: "session.syncStarted", status });
  }

  function finishSessionSync(): void {
    dispatch({ type: "session.syncFinished" });
  }

  function addShownMovieIds(sourceMovieIds: string[]): void {
    dispatch({ type: "session.shownMoviesAdded", sourceMovieIds });
  }

  function updateTonightIntent(
    updates: Partial<Omit<TonightIntentFlowState, "status">>,
  ): void {
    dispatch({ type: "tonightIntent.updated", updates });
  }

  function startTonightIntentInterpretation(): void {
    dispatch({ type: "tonightIntent.started" });
  }

  function finishTonightIntentInterpretation(): void {
    dispatch({ type: "tonightIntent.finished" });
  }

  function updateResults(updates: Partial<ResultsFlowState>): void {
    dispatch({ type: "results.updated", updates });
  }

  function updateHistoryPanel(updates: Partial<HistoryPanelState>): void {
    dispatch({ type: "historyPanel.updated", updates });
  }

  function resetAllFlowState(): void {
    dispatch({ type: "flow.reset", apiConnected });
  }

  function resetSessionProgress(): void {
    dispatch({ type: "session.progressReset", apiConnected });
  }

  function setDemoDebugFallback(): void {
    dispatch({ type: "session.demoFallback" });
  }

  return {
    ...state,
    updateSession,
    startSessionSync,
    finishSessionSync,
    addShownMovieIds,
    updateTonightIntent,
    startTonightIntentInterpretation,
    finishTonightIntentInterpretation,
    updateResults,
    updateHistoryPanel,
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
