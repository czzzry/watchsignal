import assert from "node:assert/strict";
import { stat } from "node:fs/promises";
import test from "node:test";
import { onboardingHomeStatusCopy } from "../app/pass-the-phone/required-onboarding-contract.ts";
import { publicErrorMessage } from "../app/pass-the-phone/public-error-message.ts";
import { tasteLabQueueState } from "../app/taste-lab/taste-lab-contract.ts";

const assetUrl = new URL("../public/watchsignal-startup-signal.webp", import.meta.url);

test("S23-C startup art stays within the public asset budget", async () => {
  const asset = await stat(assetUrl);

  assert.ok(asset.size > 0);
  assert.ok(asset.size <= 300_000, `startup asset is ${asset.size} bytes`);
});

test("S23-C household states stay consumer-safe across setup and recovery", () => {
  assert.deepEqual(onboardingHomeStatusCopy("loading", null, 2), {
    busyLabel: "Checking",
    progressLabel: "Checking taste setup",
    completionKnown: false,
  });
  assert.equal(tasteLabQueueState(0, 4, false), "exhausted");
  assert.doesNotMatch(
    publicErrorMessage("initial-shortlist", new Error("backend HTTP 500")),
    /backend|http|500/i,
  );
});
