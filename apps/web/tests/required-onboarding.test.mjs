import assert from "node:assert/strict";
import test from "node:test";

import {
  addManualOnboardingSeed,
  addSuggestedOnboardingSeed,
  advanceOnboardingFlow,
  entriesForOnboardingBucket,
  firstIncompleteOnboardingBucket,
  manualValueForOnboardingBucket,
  onboardingBucketCopy,
  onboardingBuckets,
  onboardingCompletionCount,
  onboardingDraftComplete,
  onboardingEntryKey,
  onboardingHomeStatusCopy,
  onboardingPublicMessage,
  removeOnboardingSeed,
  reverseOnboardingFlow,
} from "../app/pass-the-phone/required-onboarding-contract.ts";
import { demoCandidates } from "../app/session-fixtures.ts";

const entry = (rawTitle, status = "resolved") => ({ rawTitle, status });
const draft = (overrides = {}) => ({
  lovedTitleEntries: [],
  fineTitleEntries: [],
  noTitleEntries: [],
  manualLoved: "",
  manualFine: "",
  manualNo: "",
  ...overrides,
});

test("S10 uses the exact three preference buckets and never treats familiarity as preference", () => {
  assert.deepEqual(onboardingBuckets, ["loved", "fine", "no"]);
  assert.deepEqual(Object.values(onboardingBucketCopy).map((item) => item.label), [
    "Loved",
    "It was fine",
    "Not for me",
  ]);
  assert.doesNotMatch(JSON.stringify(onboardingBucketCopy), /seen|familiar|watched/i);
});

test("S10 hard gate requires all three buckets before profile completion", () => {
  const partial = draft({
    lovedTitleEntries: [entry("Arrival")],
    fineTitleEntries: [entry("Knives Out")],
  });
  const complete = { ...partial, noTitleEntries: [entry("Movie 43")] };
  assert.equal(onboardingDraftComplete(partial), false);
  assert.equal(onboardingCompletionCount(partial), 2);
  assert.equal(firstIncompleteOnboardingBucket(partial), "no");
  assert.equal(onboardingDraftComplete(complete), true);
  assert.equal(onboardingCompletionCount(complete), 3);
  assert.equal(firstIncompleteOnboardingBucket(complete), null);
});

test("S10 bucket access preserves exact API draft fields including unresolved input", () => {
  const value = draft({
    lovedTitleEntries: [entry("A very long unresolved movie title", "unresolved")],
    manualLoved: "A very long unresolved movie title",
  });
  assert.equal(entriesForOnboardingBucket(value, "loved")[0].status, "unresolved");
  assert.equal(manualValueForOnboardingBucket(value, "loved"), "A very long unresolved movie title");
});

test("S10 errors are public and promise retained picks", () => {
  const message = onboardingPublicMessage("FastAPI network timeout at 127.0.0.1");
  assert.equal(message, "Couldn’t save this taste setup. Your picks are still here.");
  assert.doesNotMatch(message, /api|backend|127\.0\.0\.1/i);
});

test("S23 initial onboarding reads never masquerade as a save or known zero completion", () => {
  assert.deepEqual(
    onboardingHomeStatusCopy("loading", null, 2),
    {
      busyLabel: "Checking",
      progressLabel: "Checking taste setup",
      completionKnown: false,
    },
  );
  assert.deepEqual(
    onboardingHomeStatusCopy("failed", null, 2),
    {
      busyLabel: null,
      progressLabel: "Setup check needed",
      completionKnown: false,
    },
  );
  assert.deepEqual(
    onboardingHomeStatusCopy("saving", 1, 2),
    {
      busyLabel: "Saving",
      progressLabel: "1 of 2 ready",
      completionKnown: true,
    },
  );
});

test("S10 traverses quick result, manual unresolved, summary, and Back editing", () => {
  let currentDraft = draft();
  let flow = { phase: "intro", bucket: "loved" };

  flow = advanceOnboardingFlow(flow, currentDraft);
  assert.deepEqual(flow, { phase: "bucket", bucket: "loved" });

  const arrival = demoCandidates.find((candidate) => candidate.id === "arrival");
  const edge = demoCandidates.find((candidate) => candidate.id === "edge-of-tomorrow");
  const pastLives = demoCandidates.find((candidate) => candidate.id === "past-lives");
  assert.ok(arrival && edge && pastLives);

  currentDraft = addSuggestedOnboardingSeed(currentDraft, "loved", arrival);
  assert.equal(currentDraft.lovedTitleEntries[0].status, "resolved");
  flow = advanceOnboardingFlow(flow, currentDraft);
  assert.deepEqual(flow, { phase: "bucket", bucket: "fine" });

  currentDraft = { ...currentDraft, manualFine: "A title only I remember" };
  currentDraft = addManualOnboardingSeed(currentDraft, "fine");
  assert.equal(currentDraft.fineTitleEntries[0].status, "unresolved");
  assert.match(currentDraft.fineTitleEntries[0].unresolvedReason, /Manual seed entry/);
  flow = advanceOnboardingFlow(flow, currentDraft);
  assert.deepEqual(flow, { phase: "bucket", bucket: "no" });

  currentDraft = addSuggestedOnboardingSeed(currentDraft, "no", pastLives);
  flow = advanceOnboardingFlow(flow, currentDraft);
  assert.deepEqual(flow, { phase: "summary", bucket: "no" });
  assert.equal(onboardingDraftComplete(currentDraft), true);

  flow = reverseOnboardingFlow(flow);
  assert.deepEqual(flow, { phase: "bucket", bucket: "no" });
  flow = reverseOnboardingFlow(flow);
  assert.deepEqual(flow, { phase: "bucket", bucket: "fine" });
  const oldFineKey = onboardingEntryKey(currentDraft.fineTitleEntries[0]);
  currentDraft = removeOnboardingSeed(currentDraft, "fine", oldFineKey);
  assert.equal(onboardingDraftComplete(currentDraft), false);
  currentDraft = addSuggestedOnboardingSeed(currentDraft, "fine", edge);
  assert.equal(onboardingDraftComplete(currentDraft), true);
});

test("S10 duplicate movie identity can belong to only one preference bucket", () => {
  const arrival = demoCandidates.find((candidate) => candidate.id === "arrival");
  assert.ok(arrival);
  const loved = addSuggestedOnboardingSeed(draft(), "loved", arrival);
  const moved = addSuggestedOnboardingSeed(loved, "no", arrival);
  assert.equal(moved.lovedTitleEntries.length, 0);
  assert.equal(moved.noTitleEntries.length, 1);

  const firstManual = addManualOnboardingSeed(
    { ...draft(), manualLoved: "Unresolved duplicate" },
    "loved",
  );
  const movedManual = addManualOnboardingSeed(
    { ...firstManual, manualNo: " unresolved DUPLICATE " },
    "no",
  );
  assert.equal(movedManual.lovedTitleEntries.length, 0);
  assert.equal(movedManual.noTitleEntries.length, 1);
});
