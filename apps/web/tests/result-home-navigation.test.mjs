import assert from "node:assert/strict";
import test from "node:test";

import { completedResultNavigationActions } from "../app/pass-the-phone/results/completed-result-navigation.ts";

test("completed-result home and new-night actions both restart the session", () => {
  let restartCount = 0;
  const actions = completedResultNavigationActions(() => {
    restartCount += 1;
  });

  assert.equal(actions.home.ariaLabel, "WatchSignal home, start a new night");
  assert.equal(actions.newNight.label, "New night");

  actions.home.activate();
  actions.newNight.activate();

  assert.equal(restartCount, 2);
});
