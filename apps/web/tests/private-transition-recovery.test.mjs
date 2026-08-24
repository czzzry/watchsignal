import assert from "node:assert/strict";
import test from "node:test";

import { demoCandidates } from "../app/session-fixtures.ts";
import { PRIVATE_TRANSITION_CHECKPOINT_KEY, createPrivateTransitionCheckpoint, privateTransitionCheckpointContainsSensitiveKeys } from "../app/pass-the-phone/private-transition-checkpoint.ts";
import { createPrivateTransitionRecoveryCoordinator } from "../app/pass-the-phone/private-transition-recovery-coordinator.ts";
import { rankCandidates } from "../app/pass-the-phone-helpers.ts";

const now = 1_800_000_000_000;
const ids = ["gaslight", "dog-day", "nightcrawler", "simple-plan", "europa"];
const scores = [0.7502, 0.7444, 0.7432, 0.7376, 0.7253];

function storage() {
  const values = new Map();
  return { values, getItem: (key) => values.get(key) ?? null, removeItem: (key) => values.delete(key), setItem: (key, value) => values.set(key, value) };
}

function candidates() {
  return demoCandidates.slice(0, 5).map((candidate, index) => ({ ...candidate, id: ids[index], provenance: { poster: "api-payload", criticScore: "not-provided", descriptiveCopy: "api-payload" } }));
}

function snapshot() { return ids.map((sourceMovieId, index) => ({ sourceMovieId, title: `Movie ${index + 1}` })); }
function shortlist() { return ids.map((sourceMovieId, index) => ({ sourceMovieId, title: `Movie ${index + 1}`, candidateRank: index + 1, profileScore: scores[index] })); }
function ballot(values) { return ids.map((sourceMovieId, index) => ({ sourceMovieId, reactionLabel: values[index] })); }
function session(overrides = {}) {
  const founderReactions = ballot(["interested", "maybe", "maybe", "interested", "interested"]);
  const wifeReactions = ballot(["maybe", "maybe", "maybe", "maybe", "maybe"]);
  return { activeMode: "compromise", batchCount: 1, bestPickSourceMovieId: "gaslight", founderReactions, householdId: "household-1", participantIds: ["founder", "wife"], previousFounderReactions: [], previousShortlist: [], previousWifeReactions: [], rerankedShortlist: shortlist(), rerankedSourceMovieIds: [...ids], sessionId: "session-1", shortlist: shortlist(), shownSourceMovieIds: [...ids], state: "reranked", wifeReactions, ...overrides };
}
function resultProjection() {
  return { kind: "result_ready", canonicalSessionId: "session-1", recipientLabel: "Sophie", resultSource: "shared", displaySnapshot: snapshot(), finalReactions: session().wifeReactions.map(({ sourceMovieId, reactionLabel }) => ({ sourceMovieId, reaction: reactionLabel })) };
}
function gateway({ projections = [resultProjection()], shared = session(), failSeal = false } = {}) {
  const calls = { consume: 0, loadSession: 0, resume: 0, seal: [] };
  return { calls,
    seal: async (_token, command) => { calls.seal.push(command); if (failSeal) throw new Error("lost response"); return { version: 1, expiresAtMs: now + 30_000 }; },
    resume: async () => { calls.resume += 1; return projections.shift() ?? null; },
    consume: async () => { calls.consume += 1; },
    loadSharedSession: async () => { calls.loadSession += 1; return shared; },
  };
}
function make(remote, saved = storage(), extra = {}) {
  const sleeps = [];
  return { saved, sleeps, recovery: createPrivateTransitionRecoveryCoordinator({ gateway: remote, storage: saved, createToken: () => "A".repeat(43), createCommandId: () => "b".repeat(64), clock: { now: () => now, sleep: async (milliseconds) => { sleeps.push(milliseconds); } }, ...extra }) };
}
function checkpoint(saved) { saved.setItem(PRIVATE_TRANSITION_CHECKPOINT_KEY, JSON.stringify(createPrivateTransitionCheckpoint({ recoveryToken: "A".repeat(43) }, now))); }

test("coordinator owns token-only storage, sanitizes a first seal, and retries by observation", async () => {
  const remote = gateway({ projections: [{ kind: "handoff_ready", recipientLabel: "Sophie", canBegin: true }], failSeal: true });
  const run = make(remote);
  assert.deepEqual(await run.recovery.sealFirstPass({ canonicalSessionId: "session-1", candidates: candidates(), reactions: Object.fromEntries(ids.map((id) => [id, "interested"])) }), { kind: "handoff", recipientLabel: "Sophie", ready: true });
  const serialized = run.saved.values.get(PRIVATE_TRANSITION_CHECKPOINT_KEY);
  assert.equal(privateTransitionCheckpointContainsSensitiveKeys(serialized), false);
  assert.deepEqual(Object.keys(JSON.parse(serialized)).sort(), ["expiresAt", "recoveryToken", "version"]);
  assert.equal(remote.calls.seal.length, 1);
  assert.equal(remote.calls.seal[0].commandId, "b".repeat(64));
  assert.deepEqual(remote.calls.seal[0].ballot.map((item) => item.sourceMovieId), ids);
  assert.doesNotMatch(JSON.stringify(remote.calls.seal[0].displaySnapshot), /"taste"|"groupScore"|"reason"/u);
  await run.recovery.resume();
  assert.equal(remote.calls.seal.length, 1, "resume must never reseal");
});

test("coordinator bounds pending polls and safely fails an unresolved match", async () => {
  const remote = gateway({ projections: Array.from({ length: 5 }, () => ({ kind: "matching_pending", recipientLabel: "Sophie" })) });
  const saved = storage(); checkpoint(saved);
  const run = make(remote, saved, { pollAttempts: 4, pollIntervalMs: 9 });
  assert.deepEqual(await run.recovery.resume(), { kind: "matching-failed", recipientLabel: "Sophie" });
  assert.equal(remote.calls.resume, 5);
  assert.deepEqual(run.sleeps, [9, 9, 9, 9]);
});

test("coordinator turns a timed-out handoff into a retryable, escapable handoff", async () => {
  const remote = gateway({ projections: Array.from({ length: 3 }, () => ({ kind: "handoff_pending", recipientLabel: "Sophie", canBegin: false })) });
  const saved = storage(); checkpoint(saved);
  const run = make(remote, saved, { pollAttempts: 2, pollIntervalMs: 9 });
  assert.deepEqual(await run.recovery.resume(), {
    kind: "handoff",
    recipientLabel: "Sophie",
    ready: false,
  });
  assert.deepEqual(run.sleeps, [9, 9]);
});

test("clearing recovery aborts an in-flight browser poll", async () => {
  const previousWindow = globalThis.window;
  const cancelled = [];
  globalThis.window = {
    setTimeout: () => 17,
    clearTimeout: (timer) => cancelled.push(timer),
  };
  try {
    const remote = gateway({ projections: [{ kind: "handoff_pending", recipientLabel: "Sophie", canBegin: false }] });
    const saved = storage(); checkpoint(saved);
    const run = { recovery: createPrivateTransitionRecoveryCoordinator({ gateway: remote, storage: saved }) };
    const pending = run.recovery.resume();
    await Promise.resolve();
    await run.recovery.clear();
    await assert.rejects(pending, /temporarily unavailable/i);
    assert.deepEqual(cancelled, [17]);
  } finally {
    globalThis.window = previousWindow;
  }
});

test("clearing recovery during a seal cannot restore a checkpoint or apply an outcome", async () => {
  let finishSeal;
  const remote = gateway({ projections: [{ kind: "handoff_ready", recipientLabel: "Sophie", canBegin: true }] });
  remote.seal = async (_token, command) => {
    remote.calls.seal.push(command);
    return await new Promise((resolve) => {
      finishSeal = resolve;
    });
  };
  const run = make(remote);
  const pending = run.recovery.sealFirstPass({
    canonicalSessionId: "session-1",
    candidates: candidates(),
    reactions: Object.fromEntries(ids.map((id) => [id, "interested"])),
  });
  await Promise.resolve();
  await run.recovery.clear();
  finishSeal({ version: 1, expiresAtMs: now + 30_000 });

  await assert.rejects(pending, /temporarily unavailable/i);
  assert.equal(run.saved.values.size, 0);
  assert.equal(remote.calls.resume, 0);
});

test("clearing recovery during resume prevents a stale handoff outcome", async () => {
  let finishResume;
  const remote = gateway();
  remote.resume = async () => {
    remote.calls.resume += 1;
    return await new Promise((resolve) => {
      finishResume = resolve;
    });
  };
  const saved = storage();
  checkpoint(saved);
  const run = make(remote, saved);
  const pending = run.recovery.resume();
  await Promise.resolve();
  await run.recovery.clear();
  finishResume({ kind: "handoff_ready", recipientLabel: "Sophie", canBegin: true });

  await assert.rejects(pending, /temporarily unavailable/i);
  assert.equal(run.saved.values.size, 0);
  assert.equal(remote.calls.loadSession, 0);
});

test("clearing recovery during canonical session load prevents a stale result outcome", async () => {
  let finishLoad;
  const remote = gateway();
  remote.loadSharedSession = async () => {
    remote.calls.loadSession += 1;
    return await new Promise((resolve) => {
      finishLoad = resolve;
    });
  };
  const saved = storage();
  checkpoint(saved);
  const run = make(remote, saved);
  const pending = run.recovery.resume();
  await Promise.resolve();
  await Promise.resolve();
  await run.recovery.clear();
  finishLoad(session());

  await assert.rejects(pending, /temporarily unavailable/i);
  assert.equal(run.saved.values.size, 0);
});

test("coordinator maps only a canonical shared result and clears it after completion", async () => {
  const remote = gateway(); const saved = storage(); checkpoint(saved);
  const run = make(remote, saved);
  const outcome = await run.recovery.resume();
  assert.equal(outcome.kind, "result");
  if (outcome.kind !== "result") return;
  assert.equal(remote.calls.loadSession, 1);
  const ranked = rankCandidates({ sessionMode: "compromise", peopleMode: "couple", candidates: outcome.session.candidates, founderReactions: outcome.session.founderReactions, wifeReactions: outcome.session.wifeReactions, rerankedSourceMovieIds: outcome.session.sharedSession.rerankedSourceMovieIds });
  assert.deepEqual(ranked.map((candidate) => candidate.score), [79, 74, 74, 79, 78]);
  await run.recovery.clear();
  assert.equal(saved.values.size, 0);
  assert.equal(remote.calls.consume, 1);
});

for (const [label, shared, projection] of [
  ["incomplete", session({ state: "wife_reacting", wifeReactions: [] }), resultProjection()],
  ["mismatched", session(), { ...resultProjection(), finalReactions: [{ sourceMovieId: ids[0], reaction: "no" }, ...resultProjection().finalReactions.slice(1)] }],
  ["duplicate", session(), { ...resultProjection(), finalReactions: [...resultProjection().finalReactions.slice(0, 4), { sourceMovieId: ids[0], reaction: "maybe" }]}],
  ["non-reranked", session({ rerankedSourceMovieIds: [] }), resultProjection()],
  ["wrong-session-id", session({ sessionId: "session-other" }), resultProjection()],
]) {
  test(`coordinator rejects ${label} result`, async () => {
    const remote = gateway({ projections: [projection], shared }); const saved = storage(); checkpoint(saved);
    await assert.rejects(make(remote, saved).recovery.resume(), /temporarily unavailable/i);
  });
}
