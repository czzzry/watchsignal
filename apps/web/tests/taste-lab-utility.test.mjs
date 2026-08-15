import assert from "node:assert/strict";
import test from "node:test";

import {
  tasteLabChoiceGroups,
  tasteLabLabelIsPreference,
  tasteLabQueueState,
} from "../app/taste-lab/taste-lab-contract.ts";

test("S18 preserves every API label and keeps familiarity separate", () => {
  assert.deepEqual(
    tasteLabChoiceGroups.preference.map((choice) => choice.value),
    ["loved", "liked", "meh", "hated"],
  );
  assert.equal(tasteLabChoiceGroups.familiarity.value, "havent_seen");
  assert.equal(tasteLabLabelIsPreference("havent_seen"), false);
  for (const label of ["loved", "liked", "meh", "hated"]) {
    assert.equal(tasteLabLabelIsPreference(label), true);
  }
});

test("S18 distinguishes ready, empty, exhausted, and local exhaustion", () => {
  assert.equal(tasteLabQueueState(4, 0, false), "ready");
  assert.equal(tasteLabQueueState(0, 0, false), "empty");
  assert.equal(tasteLabQueueState(0, 8, false), "exhausted");
  assert.equal(tasteLabQueueState(4, 0, true), "local");
  assert.equal(tasteLabQueueState(0, 0, true), "local-exhausted");
});
