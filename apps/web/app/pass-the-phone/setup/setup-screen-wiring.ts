import type {
  SetupScreenActions,
  SetupScreenModel,
} from "./setup-screen";

export type SetupScreenActionSources = {
  changePeopleMode: SetupScreenActions["household"]["changePeopleMode"];
  chooseActiveProfile: SetupScreenActions["household"]["chooseActiveProfile"];
  choosePartnerProfile: SetupScreenActions["household"]["choosePartnerProfile"];
  createProfile: SetupScreenActions["household"]["createProfile"];
  saveDefaults: SetupScreenActions["tonight"]["saveDefaults"];
  changeIntentText: SetupScreenActions["tonight"]["intent"]["changeText"];
  changeIntentClarificationText: SetupScreenActions["tonight"]["intent"]["changeClarificationText"];
  interpretIntent: SetupScreenActions["tonight"]["intent"]["interpret"];
  answerIntentClarification: SetupScreenActions["tonight"]["intent"]["answerClarification"];
  removeIntentSignal: SetupScreenActions["tonight"]["intent"]["removeSignal"];
  applyIntent: SetupScreenActions["tonight"]["intent"]["apply"];
  clearIntent: SetupScreenActions["tonight"]["intent"]["clear"];
  cancelIntent: SetupScreenActions["tonight"]["intent"]["cancel"];
  selectTasteLens: SetupScreenActions["tonight"]["tasteLens"]["select"];
  start: SetupScreenActions["readiness"]["start"];
  beginOnboarding: SetupScreenActions["readiness"]["beginOnboarding"];
  loadMemory: SetupScreenActions["memory"]["load"];
  loadHistory: SetupScreenActions["history"]["load"];
  selectHistory: SetupScreenActions["history"]["select"];
};

export type SetupScreenWiringInput = {
  model: SetupScreenModel;
  actionSources: SetupScreenActionSources;
};

export function createSetupScreenWiring({
  model,
  actionSources,
}: SetupScreenWiringInput): {
  model: SetupScreenModel;
  actions: SetupScreenActions;
} {
  return {
    model,
    actions: {
      household: {
        changePeopleMode: actionSources.changePeopleMode,
        chooseActiveProfile: actionSources.chooseActiveProfile,
        choosePartnerProfile: actionSources.choosePartnerProfile,
        createProfile: actionSources.createProfile,
      },
      tonight: {
        saveDefaults: actionSources.saveDefaults,
        intent: {
          changeText: actionSources.changeIntentText,
          changeClarificationText: actionSources.changeIntentClarificationText,
          interpret: actionSources.interpretIntent,
          answerClarification: actionSources.answerIntentClarification,
          removeSignal: actionSources.removeIntentSignal,
          apply: actionSources.applyIntent,
          clear: actionSources.clearIntent,
          cancel: actionSources.cancelIntent,
        },
        tasteLens: {
          select: actionSources.selectTasteLens,
        },
      },
      readiness: {
        start: actionSources.start,
        beginOnboarding: actionSources.beginOnboarding,
      },
      memory: {
        load: actionSources.loadMemory,
      },
      history: {
        load: actionSources.loadHistory,
        select: actionSources.selectHistory,
      },
    },
  };
}
