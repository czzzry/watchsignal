import assert from "node:assert/strict";
import test from "node:test";

import { publicResultSynopsis } from "../app/pass-the-phone/results/result-details-contract.ts";

test("ranked result details use the live synopsis when available", () => {
  assert.equal(
    publicResultSynopsis({ title: "Arrival", overview: "  A linguist meets visitors.  " }),
    "A linguist meets visitors.",
  );
});

test("ranked result details never expose scorer prose as a synopsis", () => {
  const hostileReason = "Fits compromise mode with signal from Comedy; score 99.";
  const synopsis = publicResultSynopsis({
    title: "Arrival",
    overview: "   ",
    reason: hostileReason,
  });

  assert.equal(synopsis, "More details for Arrival are not available yet.");
  assert.doesNotMatch(synopsis, /compromise|signal|score/i);
});
