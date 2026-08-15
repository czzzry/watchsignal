import assert from "node:assert/strict";
import test from "node:test";

import {
  createOnboardingTruthfulController,
  onboardingHomePresentation,
} from "../app/pass-the-phone/onboarding-truthful-state.ts";

const lockedCompletion = {
  completedProfileIds: ["alex"],
  incompleteProfileIds: ["sam"],
  requiredProfileIds: ["alex", "sam"],
  sharedRecommendationLocked: true,
  sharedRecommendationUnlocked: false,
};

const unlockedCompletion = {
  completedProfileIds: ["alex", "sam"],
  incompleteProfileIds: [],
  requiredProfileIds: ["alex", "sam"],
  sharedRecommendationLocked: false,
  sharedRecommendationUnlocked: true,
};

test("delayed completion check renders unknown Checking state before enabling Start", async () => {
  const completion = deferred();
  const controller = createOnboardingTruthfulController({
    getCompletion: () => completion.promise,
    saveProfile: async (_profileId, onboarding) => onboarding,
  });

  const checking = controller.check(["alex", "sam"]);
  assert.deepEqual(
    presentation(controller),
    {
      busyLabel: "Checking",
      progressLabel: "Checking taste setup",
      completionKnown: false,
      primaryLabel: "Set up tastes",
      primaryDisabled: true,
    },
  );
  assert.doesNotMatch(JSON.stringify(presentation(controller)), /Saving|0 of 2/);

  completion.resolve(unlockedCompletion);
  assert.deepEqual(await checking, unlockedCompletion);
  assert.deepEqual(
    presentation(controller),
    {
      busyLabel: null,
      progressLabel: "2 of 2 ready",
      completionKnown: true,
      primaryLabel: "Start first pass",
      primaryDisabled: false,
    },
  );
});

test("pending profile save after known completion renders Saving without losing the count", async () => {
  const save = deferred();
  const controller = createOnboardingTruthfulController({
    getCompletion: async () => lockedCompletion,
    saveProfile: () => save.promise,
  });
  await controller.check(["alex", "sam"]);

  const pendingSave = controller.save("sam", completeOnboarding("sam"));
  assert.deepEqual(
    presentation(controller),
    {
      busyLabel: "Saving",
      progressLabel: "1 of 2 ready",
      completionKnown: true,
      primaryLabel: "Finish setup",
      primaryDisabled: true,
    },
  );

  save.resolve(completeOnboarding("sam"));
  assert.equal((await pendingSave).status, "saved");
});

for (const [label, failure] of [
  ["rejected", new Error("Session API returned HTTP 500")],
  ["aborted", new DOMException("The operation was aborted", "AbortError")],
]) {
  test(`${label} completion check renders fixed recovery without false completion`, async () => {
    const controller = createOnboardingTruthfulController({
      getCompletion: async () => {
        throw failure;
      },
      saveProfile: async (_profileId, onboarding) => onboarding,
    });

    assert.equal(await controller.check(["alex", "sam"]), null);
    const snapshot = controller.getSnapshot();
    assert.equal(
      snapshot.message,
      "Couldn’t load taste setup. Your current setup is unchanged. Try again.",
    );
    assert.equal(snapshot.completion, null);
    assert.deepEqual(
      presentation(controller),
      {
        busyLabel: null,
        progressLabel: "Setup check needed",
        completionKnown: false,
        primaryLabel: "Set up tastes",
        primaryDisabled: false,
      },
    );
    assert.doesNotMatch(JSON.stringify(snapshot), /500|API|0 of 2/);
  });
}

function presentation(controller) {
  const snapshot = controller.getSnapshot();
  return onboardingHomePresentation({
    state: snapshot,
    onboardingRequired:
      snapshot.completion?.sharedRecommendationLocked ?? snapshot.status !== "ready",
    onboardingPromptLabel: null,
    isSyncing: false,
    isCoupleSession: true,
  });
}

function completeOnboarding(profileId) {
  return {
    profileId,
    lovedTitleEntries: [{ rawTitle: "Arrival", status: "resolved" }],
    fineTitleEntries: [{ rawTitle: "Knives Out", status: "resolved" }],
    noTitleEntries: [{ rawTitle: "Movie 43", status: "resolved" }],
    constraints: { horrorExclusion: false, subtitleIntolerance: false },
    isComplete: true,
  };
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}
