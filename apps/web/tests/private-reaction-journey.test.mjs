import assert from "node:assert/strict";
import test from "node:test";

import {
  activePrivateReactionCandidateId,
  advancePrivateReactionAfterAnswer,
  canNavigatePrivateReactionBack,
  canNavigatePrivateReactionForward,
  createPrivateReactionJourney,
  navigatePrivateReactionBack,
  navigatePrivateReactionForwardOrSkip,
  privateReactionCompletedCount,
  privateReactionSwipeAction,
} from "../app/pass-the-phone/private-reaction-journey.ts";

const candidateIds = ["arrival", "serious-man", "high-and-low", "fargo", "heat"];

test("a first skip defers the movie without inventing a reaction", () => {
  const start = createPrivateReactionJourney(candidateIds);
  const result = navigatePrivateReactionForwardOrSkip({
    journey: start,
    candidateIds,
    reactions: {},
  });

  assert.equal(result.outcome, "deferred");
  assert.equal(activePrivateReactionCandidateId(result.journey), "serious-man");
  assert.deepEqual(result.journey.deferredCandidateIds, ["arrival"]);
  assert.equal(privateReactionCompletedCount(candidateIds, {}), 0);
});

test("skipped movies return only after the untouched movies", () => {
  let journey = createPrivateReactionJourney(candidateIds);
  let reactions = {};

  journey = navigatePrivateReactionForwardOrSkip({
    journey,
    candidateIds,
    reactions,
  }).journey;
  journey = navigatePrivateReactionForwardOrSkip({
    journey,
    candidateIds,
    reactions,
  }).journey;

  assert.deepEqual(journey.deferredCandidateIds, ["arrival", "serious-man"]);
  assert.equal(activePrivateReactionCandidateId(journey), "high-and-low");

  for (const candidateId of ["high-and-low", "fargo", "heat"]) {
    reactions = { ...reactions, [candidateId]: "maybe" };
    const result = advancePrivateReactionAfterAnswer({
      journey,
      candidateIds,
      reactions,
    });
    journey = result.journey;
  }

  assert.equal(activePrivateReactionCandidateId(journey), "arrival");
  reactions = { ...reactions, arrival: "interested" };
  journey = advancePrivateReactionAfterAnswer({
    journey,
    candidateIds,
    reactions,
  }).journey;
  assert.equal(activePrivateReactionCandidateId(journey), "serious-man");
});

test("a second skip attempt holds the movie and requires an explicit answer", () => {
  let journey = createPrivateReactionJourney(["arrival", "heat"]);
  journey = navigatePrivateReactionForwardOrSkip({
    journey,
    candidateIds: ["arrival", "heat"],
    reactions: {},
  }).journey;

  const reactions = { heat: "maybe" };
  journey = advancePrivateReactionAfterAnswer({
    journey,
    candidateIds: ["arrival", "heat"],
    reactions,
  }).journey;
  assert.equal(activePrivateReactionCandidateId(journey), "arrival");

  const secondSkip = navigatePrivateReactionForwardOrSkip({
    journey,
    candidateIds: ["arrival", "heat"],
    reactions,
  });
  assert.equal(secondSkip.outcome, "decision-required");
  assert.equal(activePrivateReactionCandidateId(secondSkip.journey), "arrival");
  assert.deepEqual(secondSkip.journey.forcedCandidateIds, ["arrival"]);

  const repeatedAttempt = navigatePrivateReactionForwardOrSkip({
    journey: secondSkip.journey,
    candidateIds: ["arrival", "heat"],
    reactions,
  });
  assert.equal(repeatedAttempt.outcome, "decision-required");
  assert.deepEqual(repeatedAttempt.journey.forcedCandidateIds, ["arrival"]);
});

test("the pass completes only after every movie has an explicit reaction", () => {
  let journey = createPrivateReactionJourney(["arrival", "heat"]);
  let reactions = { arrival: "interested" };
  let result = advancePrivateReactionAfterAnswer({
    journey,
    candidateIds: ["arrival", "heat"],
    reactions,
  });
  assert.equal(result.outcome, "advanced");

  journey = result.journey;
  reactions = { ...reactions, heat: "no" };
  result = advancePrivateReactionAfterAnswer({
    journey,
    candidateIds: ["arrival", "heat"],
    reactions,
  });
  assert.equal(result.outcome, "complete");
  assert.equal(privateReactionCompletedCount(["arrival", "heat"], reactions), 2);
});

test("Back and forward revisit history without converting the movie into a skip", () => {
  let journey = createPrivateReactionJourney(["arrival", "heat"]);
  journey = advancePrivateReactionAfterAnswer({
    journey,
    candidateIds: ["arrival", "heat"],
    reactions: { arrival: "interested" },
  }).journey;

  assert.equal(canNavigatePrivateReactionBack(journey), true);
  journey = navigatePrivateReactionBack(journey);
  assert.equal(activePrivateReactionCandidateId(journey), "arrival");
  assert.equal(canNavigatePrivateReactionForward(journey), true);

  const forward = navigatePrivateReactionForwardOrSkip({
    journey,
    candidateIds: ["arrival", "heat"],
    reactions: { arrival: "interested" },
  });
  assert.equal(forward.outcome, "forward");
  assert.equal(activePrivateReactionCandidateId(forward.journey), "heat");
  assert.deepEqual(forward.journey.deferredCandidateIds, []);
  assert.equal(canNavigatePrivateReactionForward(forward.journey), false);
});

test("horizontal swipe intent ignores short and mostly vertical gestures", () => {
  assert.equal(
    privateReactionSwipeAction({ deltaX: -80, deltaY: 12, blocked: false }),
    "skip",
  );
  assert.equal(
    privateReactionSwipeAction({ deltaX: 80, deltaY: 12, blocked: false }),
    "back",
  );
  assert.equal(
    privateReactionSwipeAction({ deltaX: 40, deltaY: 2, blocked: false }),
    "none",
  );
  assert.equal(
    privateReactionSwipeAction({ deltaX: -70, deltaY: 68, blocked: false }),
    "none",
  );
  assert.equal(
    privateReactionSwipeAction({ deltaX: -90, deltaY: 0, blocked: true }),
    "none",
  );
});
