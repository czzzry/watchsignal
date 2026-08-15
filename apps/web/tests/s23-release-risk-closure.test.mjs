import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
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

test("S23 production wizard consumes the session marker and contains no ordinary source strip", async () => {
  const [wizard, page, components, css] = await Promise.all([
    readFile(new URL("../app/pass-the-phone-wizard.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/pass-the-phone-components.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
  ]);

  assert.match(wizard, /window\.sessionStorage\.getItem\(launchStingStorageKey\)/);
  assert.match(wizard, /prefers-reduced-motion: reduce/);
  assert.match(wizard, /setShowLaunchSting\(false\), plan\.durationMs/);
  assert.match(css, /\.launchSting\s*\{[\s\S]*animation:\s*launchFade 900ms/);
  assert.match(css, /prefers-reduced-motion: reduce[\s\S]*\.launchSting\s*\{[\s\S]*animation-duration:\s*1ms/);

  const ordinaryShell = `${wizard}\n${page}`;
  for (const leakedCopy of [
    "Demo recommendations",
    "recommendation testing",
    "ask the backend",
    "configuredRecommendationSource",
  ]) {
    assert.doesNotMatch(ordinaryShell, new RegExp(leakedCopy, "i"));
  }
  assert.match(components, /reviewMode \? \([\s\S]*label="Review source"/);
  assert.doesNotMatch(components, /label="Backend"/);
});
