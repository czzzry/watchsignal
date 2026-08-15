import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  availabilityChoices,
  commitTonightDefaultsTransaction,
  defaultsStatus,
  languageChoices,
  sessionModeChoices,
  tonightDefaultsSummary,
} from "../app/pass-the-phone/tonight-defaults-contract.ts";

test("S09 keeps existing language and availability values behind readable labels", () => {
  assert.deepEqual(languageChoices.map((choice) => choice.value), [
    "english",
    "subtitles-ok",
    "anything",
  ]);
  assert.deepEqual(availabilityChoices.map((choice) => choice.value), [
    "Prime Video Germany",
    "Any streaming Germany",
  ]);
  assert.deepEqual(sessionModeChoices("Cezary", "Partner").map((choice) => choice.value), [
    "compromise",
    "founder-first",
    "wife-first",
  ]);
});

test("S09 produces a concise setup summary for couple and solo sessions", () => {
  assert.equal(
    tonightDefaultsSummary({
      peopleMode: "couple",
      languageMode: "english",
      availabilityRegion: "Prime Video Germany",
      sessionMode: "compromise",
    }),
    "English · Prime Video · Balanced",
  );
  assert.match(
    tonightDefaultsSummary({
      peopleMode: "wife",
      languageMode: "anything",
      availabilityRegion: "Any streaming Germany",
      sessionMode: "wife-first",
    }),
    /Solo$/,
  );
});

test("S09 disconnected and failure states remain honest without implementation vocabulary", () => {
  const local = defaultsStatus(false, "Setup API is unavailable at 127.0.0.1");
  const failed = defaultsStatus(true, "Setup could not be saved by the backend");
  assert.equal(local, "Changes apply to this phone tonight.");
  assert.equal(failed, "Couldn’t save remotely. Your choices are still here.");
  assert.doesNotMatch(`${local} ${failed}`, /api|backend|127\.0\.0\.1/i);
});

test("S09 stages choices and has one Save and continue action", async () => {
  const source = await readFile(
    new URL("../app/pass-the-phone/tonight-defaults-setup.tsx", import.meta.url),
    "utf8",
  );
  assert.match(source, /draftLanguage/);
  assert.match(source, /draftAvailability/);
  assert.match(source, /draftSessionMode/);
  assert.match(source, /await onSave/);
  assert.match(source, /saveLockedRef/);
  assert.match(source, /result\.status === "failed"/);
  assert.match(source, /setSaveError\(result\.message\)/);
  assert.match(source, /onClose\(\)/);
  assert.equal((source.match(/Save and continue/g) ?? []).length, 1);
  assert.doesNotMatch(source, /server address|backend|API/i);
  assert.match(source, /AccessibleModal/);
});

test("S09 failure retains every draft and Retry applies atomically once", async () => {
  const draft = {
    languageMode: "anything",
    availabilityRegion: "Any streaming Germany",
    sessionMode: "wife-first",
  };
  const applied = [];
  let attempts = 0;
  const persist = async () => {
    attempts += 1;
    return attempts === 1
      ? { status: "failed", message: "Couldn’t save remotely. Your choices are still here." }
      : { status: "saved" };
  };

  const failure = await commitTonightDefaultsTransaction(draft, persist, (value) => applied.push(value));
  assert.equal(failure.status, "failed");
  assert.deepEqual(applied, []);
  assert.deepEqual(draft, {
    languageMode: "anything",
    availabilityRegion: "Any streaming Germany",
    sessionMode: "wife-first",
  });

  const retry = await commitTonightDefaultsTransaction(draft, persist, (value) => applied.push(value));
  assert.deepEqual(retry, { status: "saved" });
  assert.deepEqual(applied, [draft]);
});

test("S09 local-only outcome applies all choices with honest copy", async () => {
  const draft = {
    languageMode: "subtitles-ok",
    availabilityRegion: "Prime Video Germany",
    sessionMode: "founder-first",
  };
  const applied = [];
  const result = await commitTonightDefaultsTransaction(
    draft,
    async () => ({ status: "local-only" }),
    (value) => applied.push(value),
  );
  assert.deepEqual(result, { status: "local-only" });
  assert.deepEqual(applied, [draft]);
  assert.equal(defaultsStatus(false, null), "Changes apply to this phone tonight.");
});

test("S09 persistence and board integration have no premature mutation path", async () => {
  const hook = await readFile(
    new URL("../app/pass-the-phone/use-pass-the-phone-onboarding-setup-state.ts", import.meta.url),
    "utf8",
  );
  const setup = await readFile(
    new URL("../app/pass-the-phone-components.tsx", import.meta.url),
    "utf8",
  );
  const saveSlice = hook.slice(
    hook.indexOf("async function saveAvailabilityRegion"),
    hook.indexOf("async function refreshOnboardingCompletion"),
  );
  assert.match(saveSlice, /if \(!result\.canPersist\)/);
  assert.match(saveSlice, /return \{ status: "failed", message \}/);
  assert.ok(
    saveSlice.indexOf("if (!result.canPersist)") <
    saveSlice.lastIndexOf("setCurrentSetup(result.setup)"),
  );
  assert.match(setup, /onSave=\{onSaveTonightDefaults\}/);
  assert.doesNotMatch(setup, /onLanguageModeChange=\{|onSessionModeChange=\{|onAvailabilityRegionChange=\{/);
});

test("S09 CSS meets compact phone and resilience floors", async () => {
  const css = await readFile(
    new URL("../app/pass-the-phone/tonight-defaults-setup.module.css", import.meta.url),
    "utf8",
  );
  const pixelFonts = [...css.matchAll(/font-size:\s*(\d+)px/g)].map((match) => Number(match[1]));
  assert.ok(pixelFonts.every((size) => size >= 12));
  assert.match(css, /width:\s*44px/);
  assert.match(css, /min-height:\s*5[246]px/);
  assert.match(css, /max-height:\s*568px/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /prefers-reduced-transparency: reduce/);
  assert.match(css, /forced-colors: active/);
});
