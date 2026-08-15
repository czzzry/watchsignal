import assert from "node:assert/strict";
import test from "node:test";

import {
  commitSeenMemory,
  persistSeenMemory,
} from "../app/pass-the-phone/session-lifecycle.ts";
import {
  canBeginSeenMemorySave,
  seenMemoryConfirmationLabel,
  seenMemoryOptions,
  seenMemoryValues,
} from "../app/pass-the-phone/seen-memory-contract.ts";

const candidate = {
  id: "arrival",
  title: "Arrival",
  year: 2016,
  reason: "Thoughtful shared fit.",
};

function lifecyclePorts() {
  const events = [];
  return {
    events,
    value: {
      startSessionSync: (status) => events.push(["start", status]),
      finishSessionSync: () => events.push(["finish"]),
      updateSession: (updates) => events.push(["update", updates]),
    },
  };
}

function onboarding(profileId) {
  return {
    profileId,
    constraints: null,
    lovedTitleEntries: [],
    fineTitleEntries: [],
    noTitleEntries: [],
    isComplete: true,
  };
}

test("seen-memory keeps the four exact persistence values and consumer labels", () => {
  assert.deepEqual(seenMemoryValues, ["loved", "fine", "no", "forget"]);
  assert.deepEqual(
    seenMemoryOptions.map(({ value, label }) => [value, label]),
    [
      ["loved", "Loved"],
      ["fine", "It was fine"],
      ["no", "Not for me"],
      ["forget", "I forget"],
    ],
  );
});

test("seen-memory save gate prevents empty, concurrent, and duplicate submissions", () => {
  assert.equal(canBeginSeenMemorySave({ selected: null, saving: false, locked: false }), false);
  assert.equal(canBeginSeenMemorySave({ selected: "loved", saving: true, locked: false }), false);
  assert.equal(canBeginSeenMemorySave({ selected: "loved", saving: false, locked: true }), false);
  assert.equal(canBeginSeenMemorySave({ selected: "loved", saving: false, locked: false }), true);
});

test("seen-memory persistence binds the wife actor to the wife profile", async () => {
  const ports = lifecyclePorts();
  let savedProfile = null;
  let savedOnboarding = null;

  const result = await persistSeenMemory(
    {
      apiConnected: true,
      peopleMode: "couple",
      participantIds: ["founder-profile", "wife-profile"],
      actor: "wife",
      candidate,
      memory: "loved",
    },
    ports.value,
    {
      getOnboarding: async (profileId) => onboarding(profileId),
      saveOnboarding: async (profileId, request) => {
        savedProfile = profileId;
        savedOnboarding = request;
        return request;
      },
      submitReactions: async () => { throw new Error("not used"); },
      advanceHandoff: async () => { throw new Error("not used"); },
    },
  );

  assert.deepEqual(result, { status: "saved" });
  assert.equal(savedProfile, "wife-profile");
  assert.equal(savedOnboarding.lovedTitleEntries[0].candidate.sourceId, "arrival");
  assert.deepEqual(ports.events, [["start", "saving"], ["finish"]]);
});

test("seen-memory failure stays retryable and an unmatched actor never writes", async () => {
  const ports = lifecyclePorts();
  let writes = 0;
  const dependencies = {
    getOnboarding: async () => onboarding("profile"),
    saveOnboarding: async () => {
      writes += 1;
      throw new Error("network down");
    },
    submitReactions: async () => { throw new Error("not used"); },
    advanceHandoff: async () => { throw new Error("not used"); },
  };

  const failed = await persistSeenMemory(
    {
      apiConnected: true,
      peopleMode: "founder",
      participantIds: ["founder-profile"],
      actor: "founder",
      candidate,
      memory: "fine",
    },
    ports.value,
    dependencies,
  );
  const unmatched = await persistSeenMemory(
    {
      apiConnected: true,
      peopleMode: "wife",
      participantIds: ["wife-profile"],
      actor: "founder",
      candidate,
      memory: "no",
    },
    ports.value,
    dependencies,
  );

  assert.equal(writes, 1);
  assert.equal(failed.status, "failed");
  assert.match(failed.message, /choice is still here/i);
  assert.equal(unmatched.status, "failed");
});

test("failed memory save preserves the previous confirmation through Cancel", async () => {
  const ports = lifecyclePorts();
  let confirmedMemory = "loved";
  const confirmations = [];

  const result = await commitSeenMemory(
    {
      apiConnected: true,
      peopleMode: "founder",
      participantIds: ["founder-profile"],
      actor: "founder",
      candidate,
      memory: "fine",
    },
    ports.value,
    (confirmation) => {
      confirmations.push(confirmation);
      confirmedMemory = confirmation.memory;
    },
    {
      getOnboarding: async () => onboarding("founder-profile"),
      saveOnboarding: async () => { throw new Error("network down"); },
      submitReactions: async () => { throw new Error("not used"); },
      advanceHandoff: async () => { throw new Error("not used"); },
    },
  );

  assert.equal(result.status, "failed");
  assert.equal(confirmedMemory, "loved");
  assert.deepEqual(confirmations, []);
});

test("failed memory save confirms exactly once after a successful Retry", async () => {
  const ports = lifecyclePorts();
  const confirmations = [];
  let attempts = 0;
  const dependencies = {
    getOnboarding: async () => onboarding("founder-profile"),
    saveOnboarding: async (_profileId, request) => {
      attempts += 1;
      if (attempts === 1) {
        throw new Error("network down");
      }
      return request;
    },
    submitReactions: async () => { throw new Error("not used"); },
    advanceHandoff: async () => { throw new Error("not used"); },
  };
  const input = {
    apiConnected: true,
    peopleMode: "founder",
    participantIds: ["founder-profile"],
    actor: "founder",
    candidate,
    memory: "fine",
  };

  const first = await commitSeenMemory(input, ports.value, (value) => confirmations.push(value), dependencies);
  const retry = await commitSeenMemory(input, ports.value, (value) => confirmations.push(value), dependencies);

  assert.equal(first.status, "failed");
  assert.deepEqual(retry, { status: "saved" });
  assert.equal(attempts, 2);
  assert.deepEqual(confirmations, [
    {
      actor: "founder",
      candidateId: "arrival",
      memory: "fine",
      persistence: "saved",
    },
  ]);
});

test("local-only completion is explicitly confirmed as phone-only", async () => {
  const ports = lifecyclePorts();
  const confirmations = [];

  const result = await commitSeenMemory(
    {
      apiConnected: false,
      peopleMode: "wife",
      participantIds: ["wife-profile"],
      actor: "wife",
      candidate,
      memory: "no",
    },
    ports.value,
    (value) => confirmations.push(value),
  );

  assert.deepEqual(result, { status: "local-only" });
  assert.equal(confirmations[0].persistence, "local-only");
  assert.equal(seenMemoryConfirmationLabel(true), "Seen on this phone");
  assert.equal(seenMemoryConfirmationLabel(false), "Seen saved");
});

test("I forget durably removes the title from every taste bucket", async () => {
  const ports = lifecyclePorts();
  let savedOnboarding = null;
  const seeded = onboarding("wife-profile");
  const arrivalEntry = { candidate: { sourceId: "arrival" } };
  seeded.lovedTitleEntries = [arrivalEntry];
  seeded.fineTitleEntries = [arrivalEntry];
  seeded.noTitleEntries = [arrivalEntry];

  const result = await persistSeenMemory(
    {
      apiConnected: true,
      peopleMode: "wife",
      participantIds: ["wife-profile"],
      actor: "wife",
      candidate,
      memory: "forget",
    },
    ports.value,
    {
      getOnboarding: async () => seeded,
      saveOnboarding: async (_profileId, request) => {
        savedOnboarding = request;
        return request;
      },
      submitReactions: async () => { throw new Error("not used"); },
      advanceHandoff: async () => { throw new Error("not used"); },
    },
  );

  assert.deepEqual(result, { status: "saved" });
  assert.deepEqual(savedOnboarding.lovedTitleEntries, []);
  assert.deepEqual(savedOnboarding.fineTitleEntries, []);
  assert.deepEqual(savedOnboarding.noTitleEntries, []);
});
