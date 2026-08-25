import assert from "node:assert/strict";
import test from "node:test";

import {
  createStandaloneBackHandlerRegistry,
  createStandaloneBackNavigationController,
  standaloneHandoffContinueAction,
  standaloneRouteBackAction,
  standaloneSurfaceBackAction,
  standaloneUnhandledBackAction,
  standaloneWizardBackAction,
  standaloneBackGuardStateKey,
  standaloneWizardRecoveryBlocksBack,
} from "../app/pass-the-phone/standalone-back-navigation-contract.ts";
import { matchingTransitionBackAction } from "../app/pass-the-phone/matching-transition-contract.ts";
import {
  resultUtilityBackHandlerActive,
  resultUtilityPersistenceBlocksBack,
} from "../app/pass-the-phone/results/result-utility-navigation-contract.ts";

function backHarness(initialState = { __NA: true }) {
  let state = initialState;
  const pushedStates = [];
  const listeners = new Set();
  const history = {
    get state() {
      return state;
    },
    pushState(nextState) {
      state = nextState;
      pushedStates.push(nextState);
    },
  };

  return {
    history,
    pushedStates,
    listen(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    leaveGuard() {
      state = { __NA: true };
      for (const listener of listeners) listener();
    },
    listenerCount() {
      return listeners.size;
    },
  };
}

test("standalone Back stays inside WatchSignal and remains armed", () => {
  const harness = backHarness();
  let handled = 0;
  const controller = createStandaloneBackNavigationController({
    standalone: true,
    history: harness.history,
    listen: harness.listen,
    onBack: () => {
      handled += 1;
    },
  });

  controller.start();

  assert.equal(harness.pushedStates.length, 1);
  assert.equal(harness.pushedStates[0].__NA, true);
  assert.equal(harness.pushedStates[0][standaloneBackGuardStateKey], true);

  harness.leaveGuard();
  assert.equal(handled, 1);
  assert.equal(harness.pushedStates.length, 2);
  assert.equal(harness.pushedStates[1][standaloneBackGuardStateKey], true);

  harness.leaveGuard();
  assert.equal(handled, 2);
  assert.equal(harness.pushedStates.length, 3);

  controller.stop();
  assert.equal(harness.listenerCount(), 0);
});

test("ordinary browser tabs keep their native Back behavior", () => {
  const harness = backHarness();
  let handled = 0;
  const controller = createStandaloneBackNavigationController({
    standalone: false,
    history: harness.history,
    listen: harness.listen,
    onBack: () => {
      handled += 1;
    },
  });

  controller.start();
  harness.leaveGuard();

  assert.equal(handled, 0);
  assert.equal(harness.pushedStates.length, 0);
  assert.equal(harness.listenerCount(), 0);
});

test("remounting on an existing guard does not add duplicate history", () => {
  const harness = backHarness({
    __NA: true,
    [standaloneBackGuardStateKey]: true,
  });
  const controller = createStandaloneBackNavigationController({
    standalone: true,
    history: harness.history,
    listen: harness.listen,
    onBack: () => undefined,
  });

  controller.start();

  assert.equal(harness.pushedStates.length, 0);
  assert.equal(harness.listenerCount(), 1);
});

test("the deepest active surface handles Back before the page", () => {
  const registry = createStandaloneBackHandlerRegistry();
  const calls = [];
  const removePage = registry.register(() => calls.push("page"), 0);
  const removeSheet = registry.register(() => calls.push("sheet"), 20);
  const removeNestedView = registry.register(() => calls.push("nested"), 30);

  assert.equal(registry.handleBack(), true);
  assert.deepEqual(calls, ["nested"]);

  removeNestedView();
  assert.equal(registry.handleBack(), true);
  assert.deepEqual(calls, ["nested", "sheet"]);

  removeSheet();
  removePage();
  assert.equal(registry.handleBack(), false);
});

test("wizard Back never crosses a sealed private boundary", () => {
  const action = (step, cardIndex = 0) => standaloneWizardBackAction({
    blocked: false,
    dismissibleOverlay: false,
    step,
    cardIndex,
  });

  assert.equal(action("setup"), "stay");
  assert.equal(action("founder", 0), "home");
  assert.equal(action("founder", 2), "previous-card");
  assert.equal(action("handoff"), "home");
  assert.equal(action("wife", 0), "handoff");
  assert.equal(action("wife", 2), "previous-card");
  assert.equal(action("results"), "home");

  assert.equal(standaloneWizardBackAction({
    blocked: true,
    dismissibleOverlay: false,
    step: "results",
    cardIndex: 0,
  }), "stay");
  assert.equal(standaloneWizardBackAction({
    blocked: false,
    dismissibleOverlay: true,
    step: "results",
    cardIndex: 0,
  }), "close-overlay");
});

test("in-flight private recovery consumes Back until handoff is safe", () => {
  assert.equal(standaloneWizardRecoveryBlocksBack("sealing"), true);
  assert.equal(standaloneWizardRecoveryBlocksBack("handoff_pending"), true);
  assert.equal(standaloneWizardRecoveryBlocksBack("matching_pending"), true);
  assert.equal(standaloneWizardRecoveryBlocksBack("handoff_ready"), false);
  assert.equal(standaloneWizardRecoveryBlocksBack("handoff_retry"), false);
  assert.equal(standaloneWizardRecoveryBlocksBack("second_pass_ready"), false);
  assert.equal(standaloneWizardRecoveryBlocksBack("matching_failed"), false);
  assert.equal(standaloneWizardRecoveryBlocksBack(null), false);
});

test("handoff reopens an existing second pass without reconciliation", () => {
  const reactions = { arrival: "interested" };
  const pass = { step: "handoff", index: 0, reactions };
  const action = standaloneHandoffContinueAction({
    recoveryStage: "second_pass_ready",
    apiSession: true,
  });

  if (action === "reopen-second-pass") pass.step = "wife";

  assert.equal(pass.step, "wife");
  assert.equal(pass.index, 0);
  assert.equal(pass.reactions, reactions);
  assert.deepEqual(pass.reactions, { arrival: "interested" });
});

test("child surfaces retain busy state and unwind local navigation first", () => {
  const registry = createStandaloneBackHandlerRegistry();
  const calls = [];
  let busy = true;
  let detailOpen = true;
  registry.register(() => calls.push("parent-close"), 10);
  registry.register(() => {
    const action = standaloneSurfaceBackAction({
      blocked: busy,
      hasPrevious: detailOpen,
    });
    if (action === "previous") {
      detailOpen = false;
      calls.push("local-back");
    }
    if (action === "close") calls.push("child-close");
  }, 20);

  assert.equal(registry.handleBack(), true);
  assert.deepEqual(calls, []);

  busy = false;
  assert.equal(registry.handleBack(), true);
  assert.deepEqual(calls, ["local-back"]);
  assert.equal(detailOpen, false);

  assert.equal(registry.handleBack(), true);
  assert.deepEqual(calls, ["local-back", "child-close"]);
});

test("matching failure returns Home while active matching consumes Back", () => {
  assert.equal(matchingTransitionBackAction("saving"), "stay");
  assert.equal(matchingTransitionBackAction("matching"), "stay");
  assert.equal(matchingTransitionBackAction("failed"), "close");
});

test("direct installed routes preserve drafts and pending saves", () => {
  assert.equal(standaloneRouteBackAction({ blocked: true, hasUnsaved: false }), "stay");
  assert.equal(standaloneRouteBackAction({ blocked: false, hasUnsaved: true }), "review-unsaved");
  assert.equal(standaloneRouteBackAction({ blocked: false, hasUnsaved: false }), "home");
});

test("unhandled installed routes return Home without moving Home itself", () => {
  assert.equal(standaloneUnhandledBackAction("/credits"), "home");
  assert.equal(standaloneUnhandledBackAction("/login"), "home");
  assert.equal(standaloneUnhandledBackAction("/"), "stay");
});

test("result utility owns Back only while nested or persisting", () => {
  assert.equal(resultUtilityBackHandlerActive({ busy: false, view: "home" }), false);
  assert.equal(resultUtilityBackHandlerActive({ busy: false, view: "watchlist" }), true);
  assert.equal(resultUtilityBackHandlerActive({ busy: true, view: "home" }), true);
  assert.equal(resultUtilityBackHandlerActive({ busy: true, view: "outcome" }), true);
});

test("all result writes block Back until they settle", () => {
  const idle = {
    watchlistStatus: "idle",
    watchlistEntryBusyCount: 0,
    outcomeBusy: false,
    feedbackBusy: false,
  };
  assert.equal(resultUtilityPersistenceBlocksBack(idle), false);
  assert.equal(resultUtilityPersistenceBlocksBack({ ...idle, watchlistStatus: "loading" }), false);
  assert.equal(resultUtilityPersistenceBlocksBack({ ...idle, watchlistStatus: "saving" }), true);
  assert.equal(resultUtilityPersistenceBlocksBack({ ...idle, watchlistStatus: "removing" }), true);
  assert.equal(resultUtilityPersistenceBlocksBack({ ...idle, watchlistStatus: "marking" }), true);
  assert.equal(resultUtilityPersistenceBlocksBack({ ...idle, watchlistEntryBusyCount: 1 }), true);
  assert.equal(resultUtilityPersistenceBlocksBack({ ...idle, outcomeBusy: true }), true);
  assert.equal(resultUtilityPersistenceBlocksBack({ ...idle, feedbackBusy: true }), true);
});
