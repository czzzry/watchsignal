import assert from "node:assert/strict";
import test from "node:test";

import {
  buildProfileMemorySnapshot,
  householdMemorySummary,
  profileMemoryPublicMessage,
} from "../app/pass-the-phone/profile-memory-snapshot-contract.ts";

function summary(profileId, overrides = {}) {
  return {
    householdId: "default-household",
    profileId,
    sharedSavedCount: 0,
    savedByProfileCount: 0,
    recentReactionCount: 0,
    watchedCount: 0,
    ratedCount: 0,
    visibleAppMemoryCount: 0,
    privateCalibrationCount: 0,
    signals: [],
    ...overrides,
  };
}

function event(eventId, profileId, overrides = {}) {
  return {
    eventId,
    householdId: "default-household",
    profileId,
    eventType: "taste_lab_rating",
    source: "taste_lab",
    sourceMovieId: `movie-${eventId}`,
    title: `Movie ${eventId}`,
    genres: ["Drama"],
    sentimentLabel: "loved",
    status: "saved",
    occurredAt: "2026-08-13T10:00:00Z",
    ...overrides,
  };
}

test("S16 maps labels by profile id and never counts another profile's events", () => {
  const result = buildProfileMemorySnapshot(
    summary("partner"),
    [event("own", "partner"), event("other-1", "founder"), event("other-2", "founder")],
    "Sophie",
  );
  assert.equal(result.profileId, "partner");
  assert.equal(result.label, "Sophie");
  assert.equal(result.evidenceCount, 1);
  assert.equal(result.confidence, "learning");
  assert.deepEqual(result.likes, ["Drama"]);
});

test("S16 deduplicates profile evidence and avoids double-counting summary and event views", () => {
  const duplicate = event("same", "founder");
  const result = buildProfileMemorySnapshot(
    summary("founder", { visibleAppMemoryCount: 3, privateCalibrationCount: 2 }),
    [duplicate, duplicate, event("seen", "founder", { eventType: "seen_before" })],
    "Cezary",
  );
  assert.equal(result.evidenceCount, 3);
  assert.equal(result.confidence, "early");
});

test("S16 keeps weak signals uncertain and only promotes growing evidence at eight", () => {
  const learning = buildProfileMemorySnapshot(summary("a"), [], "A");
  const early = buildProfileMemorySnapshot(
    summary("a", {
      privateCalibrationCount: 3,
      signals: [{ label: "Mystery", count: 3, source: "private_calibration", positiveCount: 3, neutralCount: 0, negativeCount: 0 }],
    }),
    [],
    "A",
  );
  const growing = buildProfileMemorySnapshot(
    summary("a", {
      privateCalibrationCount: 8,
      signals: [{ label: "Mystery", count: 8, source: "private_calibration", positiveCount: 8, neutralCount: 0, negativeCount: 0 }],
    }),
    [],
    "A",
  );
  assert.equal(learning.headline, "Still learning");
  assert.equal(early.headline, "Early signal for Mystery");
  assert.equal(growing.headline, "Leaning toward Mystery");
  assert.doesNotMatch(`${learning.headline} ${early.headline}`, /loves|hates|definitely/i);
  assert.equal(householdMemorySummary([learning, growing]), "Still learning your shared taste");
});

test("S16 never turns negative-only or neutral-only calibration into a preference", () => {
  const negative = buildProfileMemorySnapshot(
    summary("a", {
      privateCalibrationCount: 8,
      signals: [{ label: "Horror", count: 8, source: "private_calibration", positiveCount: 0, neutralCount: 0, negativeCount: 8 }],
    }),
    [],
    "A",
  );
  const neutral = buildProfileMemorySnapshot(
    summary("a", {
      privateCalibrationCount: 8,
      signals: [{ label: "Drama", count: 8, source: "private_calibration", positiveCount: 0, neutralCount: 8, negativeCount: 0 }],
    }),
    [],
    "A",
  );
  const mixed = buildProfileMemorySnapshot(
    summary("a", {
      privateCalibrationCount: 8,
      signals: [{ label: "Action", count: 8, source: "private_calibration", positiveCount: 4, neutralCount: 0, negativeCount: 4 }],
    }),
    [],
    "A",
  );
  assert.deepEqual(negative.likes, []);
  assert.deepEqual(negative.avoids, ["Horror"]);
  assert.equal(negative.headline, "Clearer boundary around Horror");
  assert.deepEqual(neutral.likes, []);
  assert.equal(neutral.headline, "Still taking shape");
  assert.deepEqual(mixed.likes, []);
  assert.deepEqual(mixed.avoids, []);
  assert.equal(mixed.headline, "Still taking shape");
  assert.doesNotMatch(`${negative.headline} ${neutral.headline} ${mixed.headline}`, /leaning toward/i);
});

test("S16 removes contradictory genres from both preference directions", () => {
  const result = buildProfileMemorySnapshot(
    summary("a", { visibleAppMemoryCount: 8 }),
    [
      event("positive-action", "a", { genres: ["Action"], sentimentLabel: "loved" }),
      event("negative-action", "a", { genres: ["Action"], sentimentLabel: "hated" }),
      event("positive-drama", "a", { genres: ["Drama"], sentimentLabel: "liked" }),
    ],
    "A",
  );
  assert.deepEqual(result.likes, ["Drama"]);
  assert.deepEqual(result.avoids, []);
  assert.equal(result.headline, "Still taking shape");
  assert.equal(result.detail, "Mixed signals around Action.");
});

test("S16 loading and error copy stay public and retryable", () => {
  assert.equal(profileMemoryPublicMessage("loading", null), "Reading taste memory…");
  assert.equal(
    profileMemoryPublicMessage("failed", null),
    "Couldn’t load taste memory. Try again.",
  );
});
