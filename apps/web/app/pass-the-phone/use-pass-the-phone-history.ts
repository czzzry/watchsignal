"use client";

import { toDebugHistoryErrorMessage } from "../pass-the-phone-helpers";
import type { SessionSource } from "../pass-the-phone-model";
import {
  getRecentSessions,
  getSessionDebugHistory,
  getTasteProfileSummary,
  type SharedSessionPayload,
  type TasteProfileSummaryPayload,
} from "../session-client";
import type {
  HistoryPanelState,
  ResultsFlowState,
} from "./pass-the-phone-flow-reducer";

type PassThePhoneHistoryOptions = {
  apiConnected: boolean;
  sessionSource: SessionSource;
  sharedSession: SharedSessionPayload | null;
  updateResults: (updates: Partial<ResultsFlowState>) => void;
  updateHistoryPanel: (updates: Partial<HistoryPanelState>) => void;
  backendDebugHistoryOnlyMessage: string;
  recentHistoryUnavailableMessage: string;
};

export function usePassThePhoneHistory({
  apiConnected,
  sessionSource,
  sharedSession,
  updateResults,
  updateHistoryPanel,
  backendDebugHistoryOnlyMessage,
  recentHistoryUnavailableMessage,
}: PassThePhoneHistoryOptions) {
  async function tasteProfileSummariesForSession(
    householdId: string,
    profileIds: string[],
  ): Promise<TasteProfileSummaryPayload[]> {
    return Promise.all(
      profileIds.map((profileId) =>
        getTasteProfileSummary(householdId, profileId),
      ),
    );
  }

  async function loadTasteProfileSummariesForSession(
    session: SharedSessionPayload,
  ): Promise<void> {
    await loadSoloTasteProfileSummaries(
      session.householdId,
      session.participantIds,
    );
  }

  async function loadSoloTasteProfileSummaries(
    householdId: string,
    profileIds: string[],
  ): Promise<void> {
    try {
      updateResults({
        tasteProfileSummaries: await tasteProfileSummariesForSession(
          householdId,
          profileIds,
        ),
      });
    } catch {
      updateResults({ tasteProfileSummaries: [] });
    }
  }

  async function loadDebugHistory(): Promise<void> {
    if (sessionSource !== "api" || sharedSession === null) {
      updateResults({
        debugHistory: null,
        tasteProfileSummaries: [],
        debugHistoryStatus: "failed",
        debugHistoryMessage: backendDebugHistoryOnlyMessage,
      });
      return;
    }

    updateResults({ debugHistoryStatus: "loading", debugHistoryMessage: null });
    try {
      const history = await getSessionDebugHistory(sharedSession.sessionId);
      const summaries = await tasteProfileSummariesForSession(
        history.householdId,
        history.participantIds,
      );
      updateResults({
        debugHistory: history,
        tasteProfileSummaries: summaries,
        debugHistoryStatus: "ready",
      });
    } catch (error) {
      updateResults({
        debugHistory: null,
        tasteProfileSummaries: [],
        debugHistoryStatus: "failed",
        debugHistoryMessage: toDebugHistoryErrorMessage(error),
      });
    }
  }

  async function loadRecentSessions(): Promise<void> {
    if (!apiConnected) {
      updateHistoryPanel({
        recentSessions: [],
        recentSessionsStatus: "failed",
        recentSessionsMessage: recentHistoryUnavailableMessage,
      });
      return;
    }

    updateHistoryPanel({
      recentSessionsStatus: "loading",
      recentSessionsMessage: null,
    });
    try {
      const sessions = await getRecentSessions("default-household", 6);
      updateHistoryPanel({
        recentSessions: sessions,
        recentSessionsStatus: "ready",
      });
    } catch (error) {
      updateHistoryPanel({
        recentSessions: [],
        recentSessionsStatus: "failed",
        recentSessionsMessage: toDebugHistoryErrorMessage(error),
      });
    }
  }

  async function loadRecentSessionDetail(sessionId: string): Promise<void> {
    updateHistoryPanel({
      selectedHistoryStatus: "loading",
      selectedHistoryMessage: null,
    });
    try {
      const history = await getSessionDebugHistory(sessionId);
      updateHistoryPanel({
        selectedHistory: history,
        selectedHistoryStatus: "ready",
      });
    } catch (error) {
      updateHistoryPanel({
        selectedHistory: null,
        selectedHistoryStatus: "failed",
        selectedHistoryMessage: toDebugHistoryErrorMessage(error),
      });
    }
  }

  return {
    loadDebugHistory,
    loadTasteProfileSummariesForSession,
    loadSoloTasteProfileSummaries,
    loadRecentSessions,
    loadRecentSessionDetail,
  };
}
