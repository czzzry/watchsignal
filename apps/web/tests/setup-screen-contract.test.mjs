import assert from "node:assert/strict";
import test from "node:test";

import {
  requestSetupPrimaryAction,
  setupScreenPresentation,
  shouldLoadRecentSessions,
} from "../app/pass-the-phone/setup/setup-screen-contract.ts";
import { createSetupScreenWiring } from "../app/pass-the-phone/setup/setup-screen-wiring.ts";

function setupScreenModel() {
  return {
    household: {
      founderLabel: "Alex",
      wifeLabel: "Sam",
      profiles: [],
      availabilityRegion: "Prime Video Germany",
      canPersist: true,
      peopleMode: "couple",
      activeProfileId: "alex",
      partnerProfileId: "sam",
      profileSetupBusy: false,
      profileSetupMessage: null,
    },
    tonight: {
      sessionMode: "compromise",
      languageMode: "english",
      intent: { text: "", pending: null, active: null, clarificationText: "", busy: false, message: null },
      tasteLensSelection: null,
    },
    readiness: {
      isSyncing: false,
      onboardingStatus: "ready",
      onboardingRequired: false,
      onboardingCompletion: null,
      onboardingMessage: null,
      onboardingPrompt: null,
    },
    memory: { summaries: [], events: [], message: null, status: "ready" },
    history: {
      sessions: [],
      sessionsStatus: "idle",
      sessionsMessage: null,
      selected: null,
      selectedStatus: "idle",
      selectedMessage: null,
    },
    review: { enabled: false, apiConnected: true },
  };
}

test("wizard setup wiring keeps named operations connected to their owned behavior", () => {
  const calls = [];
  const opener = {};
  const wiring = createSetupScreenWiring({
    model: setupScreenModel(),
    actionSources: {
      changePeopleMode: () => calls.push("people"),
      chooseActiveProfile: () => calls.push("active-profile"),
      choosePartnerProfile: () => calls.push("partner-profile"),
      createProfile: () => calls.push("create-profile"),
      saveDefaults: async () => ({ status: "saved" }),
      changeIntentText: () => calls.push("intent-text"),
      changeIntentClarificationText: () => calls.push("intent-clarification"),
      interpretIntent: () => calls.push("interpret-intent"),
      answerIntentClarification: () => calls.push("answer-intent"),
      removeIntentSignal: () => calls.push("remove-intent"),
      applyIntent: () => calls.push("apply-intent"),
      clearIntent: () => calls.push("clear-intent"),
      cancelIntent: () => calls.push("cancel-intent"),
      selectTasteLens: () => calls.push("taste-lens"),
      start: () => calls.push("start"),
      beginOnboarding: (receivedOpener) => calls.push(receivedOpener === opener ? "onboarding" : "wrong-opener"),
      loadMemory: () => calls.push("memory"),
      loadHistory: () => calls.push("history"),
      selectHistory: () => calls.push("history-detail"),
    },
  });

  requestSetupPrimaryAction({
    onboardingRequired: false,
    opener,
    onStart: wiring.actions.readiness.start,
    onBeginOnboarding: wiring.actions.readiness.beginOnboarding,
  });
  requestSetupPrimaryAction({
    onboardingRequired: true,
    opener,
    onStart: wiring.actions.readiness.start,
    onBeginOnboarding: wiring.actions.readiness.beginOnboarding,
  });
  wiring.actions.household.changePeopleMode("couple");
  wiring.actions.household.chooseActiveProfile("a");
  wiring.actions.household.choosePartnerProfile("b");
  wiring.actions.household.createProfile("Casey");
  wiring.actions.tonight.intent.changeText("warm mystery");
  wiring.actions.tonight.intent.interpret();
  wiring.actions.tonight.tasteLens.select(null);
  wiring.actions.memory.load();
  wiring.actions.history.load();
  wiring.actions.history.select("night-1");

  assert.deepEqual(calls, [
    "start",
    "onboarding",
    "people",
    "active-profile",
    "partner-profile",
    "create-profile",
    "intent-text",
    "interpret-intent",
    "taste-lens",
    "memory",
    "history",
    "history-detail",
  ]);
});

test("opening history requests the list only from its idle state", () => {
  assert.equal(shouldLoadRecentSessions("idle"), true);
  assert.equal(shouldLoadRecentSessions("loading"), false);
  assert.equal(shouldLoadRecentSessions("ready"), false);
  assert.equal(shouldLoadRecentSessions("failed"), false);
});

test("the visible Taste Lens summary and footer follow the chosen lens", () => {
  const selected = setupScreenPresentation({
    selection: {
      curatorId: "curator:bong-joon-ho",
      curatorName: "Bong Joon-ho",
      sourceLabel: "Sight and Sound",
      mode: "exact-list",
      usageScope: "product",
    },
    utilityLine: "We'll take turns. No duplicates.",
  });
  const unselected = setupScreenPresentation({
    selection: null,
    utilityLine: "We'll take turns. No duplicates.",
  });

  assert.equal(selected.tasteLensSummary, "Bong Joon-ho · Published shelf");
  assert.match(selected.footerNote, /Only Bong Joon-ho's published shelf/);
  assert.deepEqual(unselected, {
    tasteLensSummary: "Try a filmmaker",
    footerNote: "We'll take turns. No duplicates.",
  });
});
