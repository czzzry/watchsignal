import type {
  DebugHistoryStatus,
  SessionSource,
  SyncStatus,
} from "../pass-the-phone-model";
import type {
  DebugHistorySessionPayload,
  HouseholdHistoryDetailPayload,
  HouseholdHistorySummaryPayload,
  SharedSessionPayload,
  TasteProfileSummaryPayload,
  TonightIntentInterpretationPayload,
} from "../session-client";

export type SessionFlowState = {
  sessionSource: SessionSource;
  movieSource: "live" | "local";
  persistenceSource: "shared" | "local";
  recommendationSource: string;
  syncStatus: SyncStatus;
  apiError: string | null;
  sharedSession: SharedSessionPayload | null;
  liveSessionId: string | null;
  shownSourceMovieIds: string[];
};

export type TonightIntentFlowState = {
  text: string;
  clarificationText: string;
  pendingIntent: TonightIntentInterpretationPayload | null;
  activeIntents: TonightIntentInterpretationPayload[];
  status: SyncStatus;
  message: string | null;
};

export type ResultsFlowState = {
  steerText: string;
  steerClarificationText: string;
  pendingSteerIntent: TonightIntentInterpretationPayload | null;
  steerMessage: string | null;
  debugHistory: DebugHistorySessionPayload | null;
  tasteProfileSummaries: TasteProfileSummaryPayload[];
  debugHistoryStatus: DebugHistoryStatus;
  debugHistoryMessage: string | null;
};

export type HistoryPanelState = {
  recentSessions: HouseholdHistorySummaryPayload[];
  recentSessionsStatus: DebugHistoryStatus;
  recentSessionsMessage: string | null;
  selectedHistory: HouseholdHistoryDetailPayload | null;
  selectedHistoryStatus: DebugHistoryStatus;
  selectedHistoryMessage: string | null;
};

export type PassThePhoneFlowState = {
  session: SessionFlowState;
  tonightIntent: TonightIntentFlowState;
  results: ResultsFlowState;
  historyPanel: HistoryPanelState;
};

export type PassThePhoneFlowAction =
  | { type: "flow.reset"; apiConnected: boolean }
  | { type: "session.progressReset"; apiConnected: boolean }
  | { type: "session.syncStarted"; status: "loading" | "saving" }
  | { type: "session.syncFinished" }
  | {
      type: "session.updated";
      updates: Partial<Omit<SessionFlowState, "syncStatus">>;
    }
  | { type: "session.shownMoviesAdded"; sourceMovieIds: string[] }
  | { type: "session.demoFallback" }
  | { type: "tonightIntent.started" }
  | { type: "tonightIntent.finished" }
  | {
      type: "tonightIntent.updated";
      updates: Partial<Omit<TonightIntentFlowState, "status">>;
    }
  | { type: "results.updated"; updates: Partial<ResultsFlowState> }
  | { type: "historyPanel.updated"; updates: Partial<HistoryPanelState> };

const DISCONNECTED_SESSION_MESSAGE =
  "Tonight is in local mode and stays on this phone. Your choices are still here.";
const DEMO_DEBUG_HISTORY_MESSAGE =
  "Debug evidence is unavailable because the session fell back to demo mode.";

export function createPassThePhoneFlowState(
  apiConnected: boolean,
): PassThePhoneFlowState {
  return {
    session: initialSessionFlowState(apiConnected),
    tonightIntent: initialTonightIntentFlowState(),
    results: initialResultsFlowState(),
    historyPanel: initialHistoryPanelState(),
  };
}

export function passThePhoneFlowReducer(
  state: PassThePhoneFlowState,
  action: PassThePhoneFlowAction,
): PassThePhoneFlowState {
  switch (action.type) {
    case "flow.reset":
      return createPassThePhoneFlowState(action.apiConnected);
    case "session.progressReset":
      return {
        ...state,
        session: initialSessionFlowState(action.apiConnected),
        results: initialResultsFlowState(),
      };
    case "session.syncStarted":
      return {
        ...state,
        session: {
          ...state.session,
          syncStatus: action.status,
          apiError: null,
        },
      };
    case "session.syncFinished":
      return {
        ...state,
        session: { ...state.session, syncStatus: "ready" },
      };
    case "session.updated":
      return {
        ...state,
        session: { ...state.session, ...action.updates },
      };
    case "session.shownMoviesAdded":
      return {
        ...state,
        session: {
          ...state.session,
          shownSourceMovieIds: Array.from(
            new Set([
              ...state.session.shownSourceMovieIds,
              ...action.sourceMovieIds,
            ]),
          ),
        },
      };
    case "session.demoFallback":
      return {
        ...state,
        session: {
          ...state.session,
          sessionSource: "demo",
          persistenceSource: "local",
        },
        results: {
          ...state.results,
          debugHistoryStatus: "failed",
          debugHistoryMessage: DEMO_DEBUG_HISTORY_MESSAGE,
        },
      };
    case "tonightIntent.started":
      return {
        ...state,
        tonightIntent: {
          ...state.tonightIntent,
          status: "loading",
          message: null,
        },
      };
    case "tonightIntent.finished":
      return {
        ...state,
        tonightIntent: { ...state.tonightIntent, status: "ready" },
      };
    case "tonightIntent.updated":
      return {
        ...state,
        tonightIntent: { ...state.tonightIntent, ...action.updates },
      };
    case "results.updated":
      return {
        ...state,
        results: { ...state.results, ...action.updates },
      };
    case "historyPanel.updated":
      return {
        ...state,
        historyPanel: { ...state.historyPanel, ...action.updates },
      };
  }
}

function initialSessionFlowState(apiConnected: boolean): SessionFlowState {
  return {
    sessionSource: apiConnected ? "api" : "demo",
    movieSource: apiConnected ? "live" : "local",
    persistenceSource: "local",
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
