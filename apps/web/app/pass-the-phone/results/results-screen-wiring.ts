import type {
  ResultsScreenActions,
  ResultsScreenModel,
} from "./results-screen";

export type ResultsScreenActionSources = {
  startNewNight: ResultsScreenActions["result"]["startNewNight"];
  refreshProfileMemory: ResultsScreenActions["household"]["refreshProfileMemory"];
  changeContinuationText: ResultsScreenActions["continuation"]["changeText"];
  interpretContinuation: ResultsScreenActions["continuation"]["interpret"];
  changeContinuationClarificationText: ResultsScreenActions["continuation"]["changeClarificationText"];
  answerContinuationClarification: ResultsScreenActions["continuation"]["answerClarification"];
  addContinuation: ResultsScreenActions["continuation"]["add"];
  applyContinuation: ResultsScreenActions["continuation"]["apply"];
  showMore: ResultsScreenActions["continuation"]["showMore"];
  loadDebugHistory: ResultsScreenActions["diagnostics"]["loadDebugHistory"];
};

export type ResultsScreenWiringInput = {
  model: ResultsScreenModel;
  actionSources: ResultsScreenActionSources;
};

export function createResultsScreenWiring({
  model,
  actionSources,
}: ResultsScreenWiringInput): {
  model: ResultsScreenModel;
  actions: ResultsScreenActions;
} {
  return {
    model,
    actions: {
      household: {
        refreshProfileMemory: actionSources.refreshProfileMemory,
      },
      result: {
        startNewNight: actionSources.startNewNight,
      },
      continuation: {
        changeText: actionSources.changeContinuationText,
        interpret: actionSources.interpretContinuation,
        changeClarificationText: actionSources.changeContinuationClarificationText,
        answerClarification: actionSources.answerContinuationClarification,
        add: actionSources.addContinuation,
        apply: actionSources.applyContinuation,
        showMore: actionSources.showMore,
      },
      diagnostics: {
        loadDebugHistory: actionSources.loadDebugHistory,
      },
    },
  };
}
