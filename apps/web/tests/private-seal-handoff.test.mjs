import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  PRIVACY_SEAL_DURATION_MS,
  PRIVACY_SEAL_MAX_MS,
  createPrivacySealCompletionController,
  privateHandoffCopy,
  privacySafeBackTarget,
  privacySealCopy,
  sealTransitionMeetsBudget,
} from "../app/pass-the-phone/private-seal-contract.ts";
import {
  passThePhoneNavigationReducer,
} from "../app/pass-the-phone/pass-the-phone-navigation-reducer.ts";

test("privacy seal is a bounded visual transition with no fake progress", () => {
  assert.equal(PRIVACY_SEAL_DURATION_MS, 520);
  assert.equal(PRIVACY_SEAL_MAX_MS, 650);
  assert.equal(sealTransitionMeetsBudget(PRIVACY_SEAL_DURATION_MS), true);
  assert.equal(sealTransitionMeetsBudget(651), false);
  assert.deepEqual(privacySealCopy("Husband"), {
    title: "Sealing your picks",
    detail: "Husband's answers stay private.",
  });
});

test("privacy seal completes once by the deadline when animationend never arrives", () => {
  const scheduled = [];
  const cancelled = [];
  let completionCount = 0;
  const controller = createPrivacySealCompletionController(
    () => { completionCount += 1; },
    (callback, delayMs) => {
      const token = { callback, delayMs };
      scheduled.push(token);
      return token;
    },
    (token) => { cancelled.push(token); },
  );

  assert.equal(scheduled.length, 1);
  assert.equal(scheduled[0].delayMs, PRIVACY_SEAL_MAX_MS);
  assert.equal(completionCount, 0);

  scheduled[0].callback();
  controller.complete();
  scheduled[0].callback();

  assert.equal(completionCount, 1);
  assert.deepEqual(cancelled, [scheduled[0]]);
});

test("privacy seal cleanup cancels its deadline without completing a removed transition", () => {
  let completionCount = 0;
  let scheduledCallback = () => {};
  let cancellationCount = 0;
  const controller = createPrivacySealCompletionController(
    () => { completionCount += 1; },
    (callback) => {
      scheduledCallback = callback;
      return 17;
    },
    () => { cancellationCount += 1; },
  );

  controller.dispose();
  scheduledCallback();
  controller.complete();

  assert.equal(completionCount, 0);
  assert.equal(cancellationCount, 1);
});

test("handoff copy names the recipient without exposing any ballot detail", () => {
  assert.deepEqual(privateHandoffCopy("Husband", "Wife"), {
    title: "Ready for Wife",
    detail: "Husband's picks are sealed. Only Wife's choices appear next.",
    action: "Begin Wife's picks",
  });
});

test("handoff back navigation cannot reopen the first private ballot", () => {
  assert.equal(privacySafeBackTarget("handoff"), "handoff");
  assert.deepEqual(
    passThePhoneNavigationReducer(
      { step: "handoff" },
      { type: "navigation.back" },
    ),
    { step: "handoff" },
  );
  assert.deepEqual(
    passThePhoneNavigationReducer(
      { step: "wife" },
      { type: "navigation.back" },
    ),
    { step: "handoff" },
  );
});

test("private handoff source has one begin action and receives no movie or vote payload", async () => {
  const source = await readFile(
    new URL("../app/pass-the-phone/private-seal-handoff.tsx", import.meta.url),
    "utf8",
  );
  assert.doesNotMatch(source, /candidate|posterUrl|selectedReaction|founderReactions|wifeReactions/);
  assert.doesNotMatch(source, />Back</);
  assert.match(source, /copy\.action/);
  assert.match(source, /No earlier answers are shown/);
});

test("private transition CSS keeps controls readable and supports resilience modes", async () => {
  const css = await readFile(
    new URL("../app/pass-the-phone/private-seal-handoff.module.css", import.meta.url),
    "utf8",
  );
  const pixelFonts = [...css.matchAll(/font-size:\s*(\d+)px/g)].map((match) => Number(match[1]));
  assert.ok(pixelFonts.every((size) => size >= 12));
  assert.match(css, /min-height:\s*54px/);
  assert.match(css, /@media \(max-height: 620px\)/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /prefers-reduced-transparency: reduce/);
  assert.match(css, /forced-colors: active/);
});
