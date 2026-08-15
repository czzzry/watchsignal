import assert from "node:assert/strict";
import test from "node:test";
import {
  keepSetupOnPhone,
  loadSetupFromPhone,
  updateSetupProfile,
} from "../app/setup-local-state.ts";

test("S20 stores, reloads, edits, and keeps the complete setup without mapping drift", () => {
  const records = new Map();
  const storage = {
    getItem: (key) => records.get(key) ?? null,
    setItem: (key, value) => records.set(key, value),
    removeItem: (key) => records.delete(key),
  };
  const original = {
    householdLabel: "Household",
    activeProfileId: "founder-stable-id",
    partnerProfileId: "partner-stable-id",
    profiles: [
      { id: "founder-stable-id", label: "Alex", order: 1, avatarKey: "spark", colorKey: "cyan" },
      { id: "partner-stable-id", label: "Sam", order: 2, avatarKey: "moon", colorKey: "rose" },
    ],
    defaults: {
      availabilityRegion: "Prime Video Germany",
      avoidAlreadyWatched: true,
      inputMode: "Pass the phone",
      languageAccess: "English audio or verified subtitles",
      sessionType: "Movie night",
      shortlistSize: 5,
    },
  };

  keepSetupOnPhone(storage, original);
  const reloaded = loadSetupFromPhone(storage);
  assert.deepEqual(reloaded, original);
  const edited = updateSetupProfile(reloaded, "partner-stable-id", {
    label: "Samira",
    avatarKey: "comet",
    colorKey: "violet",
  });
  keepSetupOnPhone(storage, edited);
  const kept = loadSetupFromPhone(storage);
  assert.equal(kept.activeProfileId, "founder-stable-id");
  assert.equal(kept.partnerProfileId, "partner-stable-id");
  assert.equal(kept.profiles[1].id, "partner-stable-id");
  assert.equal(kept.profiles[1].label, "Samira");
  assert.deepEqual(kept.defaults, original.defaults);
  assert.deepEqual(Object.keys(kept.defaults).sort(), [
    "availabilityRegion",
    "avoidAlreadyWatched",
    "inputMode",
    "languageAccess",
    "sessionType",
    "shortlistSize",
  ]);
});
