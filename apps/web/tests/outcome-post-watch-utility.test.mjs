import assert from "node:assert/strict";
import test from "node:test";

import {
  createOutcomeSubmissionTransaction,
  feedbackDraftCanSave,
  feedbackDraftFingerprint,
  outcomeDraftCanSave,
  outcomeDraftFingerprint,
  pendingFeedbackProfileIds,
  publicOutcomeError,
  selectedOutcomeMovieId,
  settlePendingFeedback,
} from "../app/pass-the-phone/results/outcome-contract.ts";

test("outcome gate permits only the winner, a real shortlist alternative, or nothing", () => {
  const ids = ["arrival", "knives-out"];
  assert.equal(outcomeDraftCanSave({ outcomeType: "watched_recommended", otherPickId: null, note: "" }, "arrival", true, ids), true);
  assert.equal(outcomeDraftCanSave({ outcomeType: "watched_other", otherPickId: "made-up", note: "" }, "arrival", true, ids), false);
  assert.equal(outcomeDraftCanSave({ outcomeType: "watched_other", otherPickId: "knives-out", note: "" }, "arrival", true, ids), true);
  assert.equal(outcomeDraftCanSave({ outcomeType: "watched_nothing", otherPickId: null, note: "" }, "arrival", true, ids), true);
  assert.equal(outcomeDraftCanSave({ outcomeType: "watched_nothing", otherPickId: null, note: "" }, "arrival", false, ids), false);
  assert.equal(selectedOutcomeMovieId({ outcomeType: "watched_nothing", otherPickId: null, note: "" }, "arrival"), null);
});

test("a successful outcome fingerprint blocks identical double submit until the draft changes", async () => {
  const transaction = createOutcomeSubmissionTransaction();
  const original = outcomeDraftFingerprint(
    "session-1",
    { outcomeType: "watched_nothing", otherPickId: null, note: "" },
    "arrival",
  );
  assert.ok(original);

  let releaseRequest;
  let posts = 0;
  const first = transaction.start(original, async () => {
    posts += 1;
    await new Promise((resolve) => { releaseRequest = resolve; });
    return { outcomeType: "watched_nothing" };
  });
  const duplicateWhileSaving = transaction.start(original, async () => {
    posts += 1;
    return { outcomeType: "watched_nothing" };
  });

  assert.equal(first.status, "started");
  assert.deepEqual(duplicateWhileSaving, { status: "blocked", reason: "in_flight" });
  assert.equal(posts, 1);
  releaseRequest();
  const saved = await first.completion;
  assert.equal(saved.status, "saved");
  assert.equal(transaction.isConfirmed(original), true);

  const duplicateAfterSuccess = transaction.start(original, async () => {
    posts += 1;
    return { outcomeType: "watched_nothing" };
  });
  assert.deepEqual(duplicateAfterSuccess, { status: "blocked", reason: "confirmed" });
  assert.equal(posts, 1);

  const edited = outcomeDraftFingerprint(
    "session-1",
    { outcomeType: "watched_nothing", otherPickId: null, note: "We were tired" },
    "arrival",
  );
  assert.ok(edited);
  assert.equal(transaction.isConfirmed(edited), false);
  const resave = transaction.start(edited, async () => {
    posts += 1;
    return { outcomeType: "watched_nothing" };
  });
  assert.equal(resave.status, "started");
  assert.equal((await resave.completion).status, "saved");
  assert.equal(posts, 2);
});

test("a failed outcome keeps the fingerprint retryable and never claims confirmation", async () => {
  const transaction = createOutcomeSubmissionTransaction();
  const fingerprint = outcomeDraftFingerprint(
    "session-1",
    { outcomeType: "watched_nothing", otherPickId: null, note: "" },
    "arrival",
  );
  assert.ok(fingerprint);

  let posts = 0;
  const failed = transaction.start(fingerprint, async () => {
    posts += 1;
    throw new Error("offline");
  });
  assert.equal(failed.status, "started");
  assert.equal((await failed.completion).status, "failed");
  assert.equal(transaction.isConfirmed(fingerprint), false);

  const retry = transaction.start(fingerprint, async () => {
    posts += 1;
    return { outcomeType: "watched_nothing" };
  });
  assert.equal(retry.status, "started");
  assert.equal((await retry.completion).status, "saved");
  assert.equal(posts, 2);
});

test("feedback cannot save without a persisted watched title and all participating profiles", () => {
  assert.equal(feedbackDraftCanSave(null, ["husband", "wife"], { husband: "loved", wife: "fine" }), false);
  assert.equal(feedbackDraftCanSave("arrival", ["husband", "wife"], { husband: "loved" }), false);
  assert.equal(feedbackDraftCanSave("arrival", ["husband", "wife"], { husband: "loved", wife: "fine" }), true);
});

test("saved feedback disables unchanged submission, then edits resave only that profile", () => {
  const participants = ["husband", "wife"];
  const ratings = { husband: "loved", wife: "fine" };
  const notes = { husband: "Great", wife: "Okay" };
  const husbandSaved = {
    husband: feedbackDraftFingerprint(ratings.husband, notes.husband),
  };
  assert.deepEqual(pendingFeedbackProfileIds(participants, ratings, notes, {}), participants);
  assert.deepEqual(pendingFeedbackProfileIds(participants, ratings, notes, husbandSaved), ["wife"]);
  const allSaved = {
    ...husbandSaved,
    wife: feedbackDraftFingerprint(ratings.wife, notes.wife),
  };
  assert.deepEqual(pendingFeedbackProfileIds(participants, ratings, notes, allSaved), []);
  assert.equal(feedbackDraftCanSave("arrival", participants, ratings, notes, allSaved), false);
  assert.deepEqual(pendingFeedbackProfileIds(participants, ratings, { ...notes, wife: "Changed" }, allSaved), ["wife"]);
});

test("partial feedback failure retries only the unresolved profile", async () => {
  const calls = [];
  const first = await settlePendingFeedback(["husband", "wife"], async (profileId) => {
    calls.push(profileId);
    if (profileId === "wife") throw new Error("offline");
    return `${profileId}-saved`;
  });
  assert.deepEqual(first.saved, [{ profileId: "husband", value: "husband-saved" }]);
  assert.deepEqual(first.failedProfileIds, ["wife"]);

  const retry = await settlePendingFeedback(first.failedProfileIds, async (profileId) => {
    calls.push(profileId);
    return `${profileId}-saved`;
  });
  assert.deepEqual(retry.saved, [{ profileId: "wife", value: "wife-saved" }]);
  assert.deepEqual(calls, ["husband", "wife", "wife"]);
});

test("failed transactional saves retain a clear retry path", () => {
  assert.match(publicOutcomeError("outcome"), /choices are still here/i);
  assert.match(publicOutcomeError("feedback"), /choices are still here/i);
});
