import assert from "node:assert/strict";
import test from "node:test";

import {
  focusLoopDecision,
  isolateModalBackgrounds,
  restoreModalBackgrounds,
  restoreModalOpener,
  shouldCloseTopModal,
  uniqueModalBackgroundTargets,
} from "../app/ui/accessible-modal-contract.ts";

function background(attributes = {}) {
  const values = new Map(Object.entries(attributes));
  return {
    getAttribute: (name) => values.get(name) ?? null,
    hasAttribute: (name) => values.has(name),
    setAttribute: (name, value) => values.set(name, value),
    removeAttribute: (name) => values.delete(name),
  };
}

test("S08/S09 isolate explicit content and all outside body siblings including footer", () => {
  const startup = background();
  const appMain = background({ "aria-hidden": "false" });
  const footer = background({ inert: "", "aria-hidden": "credits-state" });
  const targets = uniqueModalBackgroundTargets(startup, [appMain, footer, startup]);
  assert.deepEqual(targets, [startup, appMain, footer]);

  const records = isolateModalBackgrounds(targets);
  for (const target of targets) {
    assert.equal(target.getAttribute("aria-hidden"), "true");
    assert.equal(target.hasAttribute("inert"), true);
  }

  restoreModalBackgrounds(records);
  assert.equal(startup.getAttribute("aria-hidden"), null);
  assert.equal(startup.hasAttribute("inert"), false);
  assert.equal(appMain.getAttribute("aria-hidden"), "false");
  assert.equal(appMain.hasAttribute("inert"), false);
  assert.equal(footer.getAttribute("aria-hidden"), "credits-state");
  assert.equal(footer.hasAttribute("inert"), true);
});

test("S08/S09 modal contract traps in both directions and only top Escape closes", () => {
  assert.equal(focusLoopDecision({ focusableCount: 4, activeIndex: 3, shiftKey: false }), "first");
  assert.equal(focusLoopDecision({ focusableCount: 4, activeIndex: 0, shiftKey: true }), "last");
  assert.equal(shouldCloseTopModal("Escape", true), true);
  assert.equal(shouldCloseTopModal("Escape", false), false);
  assert.equal(shouldCloseTopModal("Enter", true), false);
});

test("S08/S09 close restores the exact invoking opener", () => {
  let focusCount = 0;
  const opener = { isConnected: true, focus: () => { focusCount += 1; } };
  assert.equal(restoreModalOpener(opener), true);
  assert.equal(focusCount, 1);
  assert.equal(restoreModalOpener({ isConnected: false, focus: () => { focusCount += 1; } }), false);
  assert.equal(focusCount, 1);
});
