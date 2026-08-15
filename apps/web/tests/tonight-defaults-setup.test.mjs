import assert from "node:assert/strict";
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
