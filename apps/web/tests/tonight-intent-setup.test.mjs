import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  beginIntentRequest,
  canConfirmTonightIntent,
  intentPublicError,
  intentSignalChips,
  intentSummary,
  invalidateIntentRequests,
  isIntentRequestCurrent,
  removeIntentSignal,
  retainVisibleIntentSignals,
  uncertainIntentParts,
} from "../app/pass-the-phone/tonight-intent-contract.ts";

const interpreted = {
  rawText: "Thoughtful and tense, without going bleak.",
  status: "confirmation_required",
  resolution: "exact",
  confirmationText: "Thoughtful, tense, and not bleak",
  filters: {},
  softSignals: ["thoughtful", "intense"],
  excludedSignals: ["bleak"],
  confidence: "high",
};

test("S11 crystallizes two to four readable removable signals", () => {
  assert.deepEqual(intentSignalChips(interpreted), [
    { id: "wanted:thoughtful", kind: "wanted", value: "thoughtful", label: "Thoughtful" },
    { id: "wanted:intense", kind: "wanted", value: "intense", label: "Intense" },
    { id: "avoided:bleak", kind: "avoided", value: "bleak", label: "Not Bleak" },
  ]);
  const many = { ...interpreted, softSignals: ["one", "two", "three", "four", "five"] };
  assert.equal(intentSignalChips(many).length, 4);
});

test("S11 chip edits preserve the interpretation contract and gate empty confirmation", () => {
  const withoutIntensity = removeIntentSignal(interpreted, "wanted:intense");
  const withoutBleak = removeIntentSignal(withoutIntensity, "avoided:bleak");
  assert.deepEqual(withoutBleak.softSignals, ["thoughtful"]);
  assert.deepEqual(withoutBleak.excludedSignals, []);
  assert.equal(canConfirmTonightIntent(withoutBleak), true);
  assert.equal(
    canConfirmTonightIntent({ ...withoutBleak, softSignals: [], filters: {} }),
    false,
  );
});

test("S11 removing Comedy atomically removes its equivalent genre filter", () => {
  const comedy = {
    ...interpreted,
    filters: { genres: ["Comedy"] },
    softSignals: ["comedy"],
    excludedSignals: [],
  };
  assert.deepEqual(intentSignalChips(comedy), [
    { id: "wanted:comedy", kind: "wanted", value: "Comedy", label: "Comedy" },
  ]);

  const removed = removeIntentSignal(comedy, "wanted:comedy");
  assert.deepEqual(removed.filters, {});
  assert.deepEqual(removed.softSignals, []);
  assert.equal(canConfirmTonightIntent(removed), false);
});

test("S11 mixed chip removal preserves only the criteria still shown", () => {
  const mixed = {
    ...interpreted,
    filters: {
      genres: ["Comedy", "Drama"],
      release_year_min: 1990,
      release_year_max: 1999,
      max_runtime_minutes: 120,
      language: "German",
    },
    softSignals: ["comedy", "drama", "1990s", "comforting"],
    excludedSignals: [],
  };
  const visibleOnly = retainVisibleIntentSignals(mixed);
  assert.equal(intentSignalChips(visibleOnly).length, 4);
  assert.equal("language" in visibleOnly.filters, false);
  assert.equal(visibleOnly.softSignals.includes("comforting"), false);

  const withoutComedy = removeIntentSignal(visibleOnly, "wanted:comedy");
  assert.deepEqual(withoutComedy.filters.genres, ["Drama"]);
  assert.equal(withoutComedy.softSignals.includes("comedy"), false);
  assert.equal(withoutComedy.softSignals.includes("drama"), true);
  assert.equal(canConfirmTonightIntent(withoutComedy), true);
});

test("S11 never confirms non-visible or hidden-only intent state", () => {
  const hiddenOnly = {
    ...interpreted,
    filters: {},
    softSignals: ["open-ended", "tonight", "person-request"],
    excludedSignals: [],
  };
  assert.deepEqual(intentSignalChips(hiddenOnly), []);
  assert.equal(canConfirmTonightIntent(hiddenOnly), false);
});

test("S11 pending and confirmed summaries remain separate", () => {
  assert.equal(intentSummary(null), "Optional");
  assert.equal(intentSummary(interpreted), "Thoughtful · Intense");
});

test("S11 stale interpretation responses are invalidated by edits and clear", () => {
  const guard = { sequence: 0 };
  const first = beginIntentRequest(guard, "sad");
  const second = beginIntentRequest(guard, "comforting");
  assert.equal(isIntentRequestCurrent(guard, first), false);
  assert.equal(isIntentRequestCurrent(guard, second), true);
  invalidateIntentRequests(guard);
  assert.equal(isIntentRequestCurrent(guard, second), false);
});

test("S11 highlights only the materially uncertain phrase", () => {
  assert.deepEqual(uncertainIntentParts("I feel sad, but not bleak"), {
    before: "I feel ",
    uncertain: "sad",
    after: ", but not bleak",
  });
  assert.equal(uncertainIntentParts("Funny and short").uncertain, null);
});

test("S11 offline and failure copy retains input without implementation jargon", () => {
  const offline = intentPublicError(false);
  const failed = intentPublicError(true);
  assert.match(offline, /offline.*still here/i);
  assert.match(failed, /couldn.*still here/i);
  assert.doesNotMatch(`${offline} ${failed}`, /api|backend|model|llm|server/i);
});

test("S11 setup surface keeps explicit confirm, editable sentence, one clarification, and clear", async () => {
  const source = await readFile(
    new URL("../app/pass-the-phone/tonight-intent-setup.tsx", import.meta.url),
    "utf8",
  );
  const steering = await readFile(
    new URL("../app/pass-the-phone/use-pass-the-phone-intent-steering.ts", import.meta.url),
    "utf8",
  );
  assert.match(source, /<textarea/);
  assert.match(source, /Confirm tonight/);
  assert.match(source, /onRemoveSignal/);
  assert.match(source, /Clear/);
  assert.match(source, /Skip/);
  assert.match(source, /AccessibleModal/);
  assert.match(steering, /clarificationUsedRef/);
  assert.match(steering, /Still too broad/);
  assert.match(steering, /isIntentRequestCurrent/);
  assert.doesNotMatch(source, /chat|model|LLM|API|backend/i);
});

test("S11 every sheet exit invalidates in-flight interpretation", async () => {
  const modal = await readFile(
    new URL("../app/ui/accessible-modal.tsx", import.meta.url),
    "utf8",
  );
  const source = await readFile(
    new URL("../app/pass-the-phone/tonight-intent-setup.tsx", import.meta.url),
    "utf8",
  );
  const setup = await readFile(
    new URL("../app/pass-the-phone-components.tsx", import.meta.url),
    "utf8",
  );
  const steering = await readFile(
    new URL("../app/pass-the-phone/use-pass-the-phone-intent-steering.ts", import.meta.url),
    "utf8",
  );

  assert.match(source, /<AccessibleModal[\s\S]*?onClose=\{onClose\}/);
  assert.match(source, /aria-label="Close tonight mood"/);
  assert.match(source, /onClick=\{onClose\}>\{activeIntent \? "Done" : "Skip"\}/);
  assert.match(modal, /shouldCloseTopModal\(event\.key/);
  assert.match(modal, /event\.target === event\.currentTarget[\s\S]*?onCloseRef\.current\(\)/);
  assert.match(
    setup,
    /function closeTonightIntent\(\)[\s\S]*?onCancelTonightIntentInterpretation\(\)[\s\S]*?setSetupUtility\(null\)/,
  );
  const productionIntentSetup = setup.match(
    /<TonightIntentSetup[\s\S]*?\/>/,
  )?.[0];
  assert.ok(productionIntentSetup, "production TonightIntentSetup must be rendered");
  assert.match(productionIntentSetup, /onClose=\{closeTonightIntent\}/);
  assert.doesNotMatch(productionIntentSetup, /onClose=\{\(\) => setSetupUtility\(null\)\}/);
  assert.match(
    steering,
    /function cancelTonightIntentInterpretation\(\)[\s\S]*?invalidateIntentRequests\(tonightRequestGuard\.current\)[\s\S]*?finishTonightIntentInterpretation\(\)/,
  );

  for (const closePath of ["header", "Escape", "backdrop", "Skip"]) {
    const guard = { sequence: 0 };
    const ticket = beginIntentRequest(guard, closePath);
    const lateResults = [];
    const delayedResponse = new Promise((resolve) => {
      setTimeout(() => {
        if (isIntentRequestCurrent(guard, ticket)) {
          lateResults.push(`${closePath}-repopulated`);
        }
        resolve();
      }, 5);
    });
    invalidateIntentRequests(guard);
    await delayedResponse;
    assert.equal(isIntentRequestCurrent(guard, ticket), false, closePath);
    assert.deepEqual(lateResults, [], `${closePath} must ignore a late response`);
  }
});

test("S11 confirmed intent is the only value forwarded into session start", async () => {
  const wizard = await readFile(
    new URL("../app/pass-the-phone-wizard.tsx", import.meta.url),
    "utf8",
  );
  const steering = await readFile(
    new URL("../app/pass-the-phone/use-pass-the-phone-intent-steering.ts", import.meta.url),
    "utf8",
  );
  assert.match(wizard, /activeTonightIntents/);
  assert.match(wizard, /continueWithTonightIntents\(activeTonightIntents\)/);
  assert.doesNotMatch(wizard, /tonightIntents:\s*\[?pendingTonightIntent/);
  assert.match(steering, /const visibleIntent = retainVisibleIntentSignals/);
  assert.match(steering, /if \(!canConfirmTonightIntent\(visibleIntent\)\)/);
  assert.match(steering, /activeIntents: \[visibleIntent\]/);
});

test("S11 CSS meets phone, text, touch, and resilience contracts", async () => {
  const css = await readFile(
    new URL("../app/pass-the-phone/tonight-intent-setup.module.css", import.meta.url),
    "utf8",
  );
  const pixelFonts = [...css.matchAll(/font(?:-size|:)\s*(?:\d+\s+)?(\d+)px/g)]
    .map((match) => Number(match[1]));
  assert.ok(pixelFonts.every((size) => size >= 12));
  assert.match(css, /width:\s*min\(100%, 430px\)/);
  assert.match(css, /min-height:\s*44px/);
  assert.match(css, /min-height:\s*54px/);
  assert.match(css, /max-height:\s*568px/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /prefers-reduced-transparency: reduce/);
  assert.match(css, /forced-colors: active/);
});
