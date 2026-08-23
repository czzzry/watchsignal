import assert from "node:assert/strict";
import test from "node:test";
import gauntletStatus from "../public/redesign-gauntlet-status.json" with { type: "json" };

import {
  isReviewOnlyRoute,
  shouldHideReviewOnlyRoute,
} from "../app/review-route-policy.ts";

test("S23 status normalizes to twenty-three accepted slices", () => {
  assert.equal(gauntletStatus.completed, gauntletStatus.total);
  assert.equal(gauntletStatus.total, 23);
  assert.deepEqual(gauntletStatus.blockers, []);
  assert.equal(
    gauntletStatus.slices.every((slice) => slice.status === "accepted"),
    true,
  );
});

test("S23 production hides prototype and progress routes", () => {
  for (const pathname of [
    "/prototype",
    "/prototype/redesign-gauntlet",
    "/prototype/north-star-result",
    "/redesign-gauntlet-status.json",
  ]) {
    assert.equal(isReviewOnlyRoute(pathname), true);
    assert.equal(shouldHideReviewOnlyRoute(pathname, "production"), true);
    assert.equal(shouldHideReviewOnlyRoute(pathname, "development"), false);
    assert.equal(shouldHideReviewOnlyRoute(pathname, "test"), false);
  }
});

test("S23 production route policy does not hide consumer or lookalike routes", () => {
  for (const pathname of [
    "/",
    "/login",
    "/setup",
    "/taste-lab",
    "/credits",
    "/api/session",
    "/showcase",
    "/showcase/flow",
    "/prototype-notes",
    "/showcaseable",
  ]) {
    assert.equal(isReviewOnlyRoute(pathname), false);
    assert.equal(shouldHideReviewOnlyRoute(pathname, "production"), false);
  }
});
