import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  PRIVATE_TRANSITION_CHECKPOINT_TTL_MS,
  createPrivateTransitionCheckpoint,
  parsePrivateTransitionCheckpoint,
  privateTransitionCheckpointContainsSensitiveKeys,
} from "../app/pass-the-phone/private-transition-checkpoint.ts";
import {
  createPrivateTransitionRecoveryClient,
} from "../app/pass-the-phone/private-transition-recovery.ts";
import { privateTransitionRestorePlan } from "../app/pass-the-phone/private-transition-restore-plan.ts";
import { passThePhoneNavigationReducer } from "../app/pass-the-phone/pass-the-phone-navigation-reducer.ts";

const now = 1_800_000_000_000;

test("browser checkpoint has a strict privacy-safe schema and bounded TTL", () => {
  const checkpoint = createPrivateTransitionCheckpoint(
    {
      recoveryToken: "A".repeat(43),
    },
    now,
  );
  const serialized = JSON.stringify(checkpoint);

  assert.equal(checkpoint.expiresAt, now + PRIVATE_TRANSITION_CHECKPOINT_TTL_MS);
  assert.equal(privateTransitionCheckpointContainsSensitiveKeys(serialized), false);
  assert.deepEqual(parsePrivateTransitionCheckpoint(serialized, now), checkpoint);
  assert.equal(parsePrivateTransitionCheckpoint(serialized, checkpoint.expiresAt), null);
});

test("checkpoint rejects unknown or ballot-bearing browser fields", () => {
  const base = createPrivateTransitionCheckpoint(
    {
      recoveryToken: "A".repeat(43),
    },
    now,
  );
  const unsafe = JSON.stringify({ ...base, reactions: { movie: "interested" } });

  assert.equal(privateTransitionCheckpointContainsSensitiveKeys(unsafe), true);
  assert.equal(parsePrivateTransitionCheckpoint(unsafe, now), null);
  assert.equal(parsePrivateTransitionCheckpoint("not-json", now), null);
});

test("deep recovery client owns token-only storage and body-only transport", async () => {
  const stored = new Map();
  const calls = [];
  const client = createPrivateTransitionRecoveryClient({
    createToken: () => "A".repeat(43),
    now: () => now,
    storage: {
      getItem: (key) => stored.get(key) ?? null,
      removeItem: (key) => stored.delete(key),
      setItem: (key, value) => stored.set(key, value),
    },
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return Response.json({ version: 1, expiresAtMs: now + 30_000 });
    },
  });

  await client.save({
    kind: "open_second_pass",
    workflowVersion: 1,
    payloadVersion: 1,
    commandId: "b".repeat(64),
  });

  const serialized = [...stored.values()][0];
  assert.deepEqual(JSON.parse(serialized), {
    version: 1,
    recoveryToken: "A".repeat(43),
    expiresAt: now + 30_000,
  });
  assert.doesNotMatch(
    serialized,
    /session|stage|actor|people|title|movie|candidate|reaction|ballot|score|profile|household/iu,
  );
  assert.equal(calls[0].url, "/api/private-transition-recovery/seal");
  assert.equal(calls[0].init.headers["X-WatchSignal-Recovery"], "1");
  assert.equal(new URL(calls[0].url, "https://watchsignal.test").search, "");
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    token: "A".repeat(43),
    command: {
      kind: "open_second_pass",
      workflowVersion: 1,
      payloadVersion: 1,
      commandId: "b".repeat(64),
    },
  });
});

test("deep recovery client resumes and consumes through the same opaque handle", async () => {
  const stored = new Map();
  const calls = [];
  const client = createPrivateTransitionRecoveryClient({
    createToken: () => "A".repeat(43),
    now: () => now,
    storage: {
      getItem: (key) => stored.get(key) ?? null,
      removeItem: (key) => stored.delete(key),
      setItem: (key, value) => stored.set(key, value),
    },
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      if (String(url).endsWith("/seal")) {
        return Response.json({ version: 1, expiresAtMs: now + 30_000 });
      }
      if (String(url).endsWith("/resume")) {
        return Response.json({
          kind: "handoff_ready",
          recipientLabel: "Sophie",
          canBegin: true,
        });
      }
      return new Response(null, { status: 204 });
    },
  });

  await client.save({
    kind: "open_second_pass",
    workflowVersion: 1,
    payloadVersion: 1,
    commandId: "b".repeat(64),
  });
  assert.deepEqual(await client.load(), {
    kind: "handoff_ready",
    recipientLabel: "Sophie",
    canBegin: true,
  });
  await client.clear();

  assert.equal(stored.size, 0);
  assert.equal(calls[1].url, "/api/private-transition-recovery/resume");
  assert.equal(calls[2].url, "/api/private-transition-recovery/consume");
  assert.deepEqual(JSON.parse(calls[1].init.body), { token: "A".repeat(43) });
  assert.deepEqual(JSON.parse(calls[2].init.body), { token: "A".repeat(43) });
});

test("deep recovery client rejects a result with unrecognized reaction data", async () => {
  const checkpoint = JSON.stringify(createPrivateTransitionCheckpoint(
    { recoveryToken: "A".repeat(43) },
    now,
  ));
  const client = createPrivateTransitionRecoveryClient({
    now: () => now,
    storage: {
      getItem: () => checkpoint,
      removeItem: () => undefined,
      setItem: () => undefined,
    },
    fetchImpl: async () => Response.json({
      kind: "result_ready",
      canonicalSessionId: "session-private",
      resultSource: "shared",
      displaySnapshot: Array.from({ length: 5 }, (_, index) => ({
        sourceMovieId: `movie-${index}`,
      })),
      finalReactions: Array.from({ length: 5 }, (_, index) => ({
        sourceMovieId: `movie-${index}`,
        reaction: index === 4 ? "internal-score" : "interested",
      })),
    }),
  });

  await assert.rejects(client.load(), /invalid response/);
});

test("navigation can restore only a named privacy-safe transition step", () => {
  assert.deepEqual(
    passThePhoneNavigationReducer(
      { step: "setup" },
      { type: "session.recovered", step: "handoff" },
    ),
    { step: "handoff" },
  );
});

test("recovery projections drive one executable handoff, pass, matching, or result plan", () => {
  assert.deepEqual(
    privateTransitionRestorePlan({
      kind: "handoff_pending",
      recipientLabel: "Sophie",
      canBegin: false,
    }),
    {
      kind: "handoff",
      stage: "handoff_pending",
      recipientLabel: "Sophie",
      canBegin: false,
      shouldPoll: true,
    },
  );
  assert.deepEqual(
    privateTransitionRestorePlan({
      kind: "matching_failed",
      canRetry: true,
      canUseLocal: true,
    }),
    {
      kind: "matching",
      stage: "matching_failed",
      phase: "failed",
      shouldPoll: false,
    },
  );
  const displaySnapshot = Array.from({ length: 5 }, (_, index) => ({
    sourceMovieId: `movie-${index}`,
    title: `Movie ${index}`,
  }));
  assert.deepEqual(
    privateTransitionRestorePlan({
      kind: "second_pass_ready",
      displaySnapshot,
    }),
    {
      kind: "second_pass",
      stage: "second_pass_ready",
      displaySnapshot,
    },
  );
  const finalReactions = displaySnapshot.map((movie) => ({
    sourceMovieId: movie.sourceMovieId,
    reaction: "interested",
  }));
  assert.deepEqual(
    privateTransitionRestorePlan({
      kind: "result_ready",
      canonicalSessionId: "session-private",
      resultSource: "local",
      displaySnapshot,
      finalReactions,
    }),
    {
      kind: "result",
      stage: "result_ready",
      canonicalSessionId: "session-private",
      resultSource: "local",
      displaySnapshot,
      finalReactions,
    },
  );
});

test("sensitive recovery uses the authenticated body-only durable route", async () => {
  const client = await readFile(
    new URL("../app/pass-the-phone/private-transition-recovery.ts", import.meta.url),
    "utf8",
  );

  assert.match(client, /private-transition-recovery\/(?:seal|resume|consume)/);
  assert.doesNotMatch(client, /\?token=|private-transition-vault|localStorage|history\./);
});

test("production flow clears recovery at boundaries and gates forced failure to review mode", async () => {
  const source = await readFile(
    new URL("../app/pass-the-phone-wizard.tsx", import.meta.url),
    "utf8",
  );

  assert.match(source, /function resetSession\(\) \{\s*clearTransitionRecovery\(\)/);
  assert.match(source, /async function startSession\(\) \{\s*clearTransitionRecovery\(\)/);
  assert.match(source, /params\.get\("matchingFailure"\) === "1"[\s\S]*params\.get\("review"\) === "1"/);
  assert.match(
    source,
    /dispatchNavigation\(\{ type: "session\.recovered", step: "results" \}\);[\s\S]*requestAnimationFrame\(\(\) => void clearTransitionRecovery\(\)\)/,
  );
  assert.match(
    source,
    /kind: "open_second_pass"[\s\S]*commandId: createPrivateTransitionCommandId\(\)/,
  );
  assert.doesNotMatch(
    source,
    /kind: "open_second_pass"[\s\S]{0,240}canonicalSessionId/,
  );
  assert.match(source, /kind: "use_local_result"[\s\S]*restorePrivateTransition\(projection\)/);
  assert.match(
    source,
    /kind: "seal_final_ballot"[\s\S]{0,240}commandId: createPrivateTransitionCommandId\(\)/,
  );
});
