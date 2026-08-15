import assert from "node:assert/strict";
import test from "node:test";

import {
  launchStingMaximumMs,
  launchStingPlan,
} from "../app/pass-the-phone/launch-sting-contract.ts";

test("S23 launch sting is session-once, bounded to 900ms, and skipped for reduced motion", () => {
  assert.equal(launchStingMaximumMs, 900);
  assert.deepEqual(
    launchStingPlan({ alreadyShown: false, reducedMotion: false }),
    { show: true, durationMs: 900, markAsSeen: true },
  );
  assert.deepEqual(
    launchStingPlan({ alreadyShown: true, reducedMotion: false }),
    { show: false, durationMs: 0, markAsSeen: false },
  );
  assert.deepEqual(
    launchStingPlan({ alreadyShown: false, reducedMotion: true }),
    { show: false, durationMs: 0, markAsSeen: true },
  );
});
