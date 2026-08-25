import assert from "node:assert/strict";
import test from "node:test";

import {
  createStandaloneBackHandlerRegistry,
  createStandaloneBackNavigationController,
  standaloneWizardBackAction,
  standaloneBackGuardStateKey,
} from "../app/pass-the-phone/standalone-back-navigation-contract.ts";

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
