import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  handlePrivateTransitionRecoveryMaintenance,
} from "../app/api/maintenance/private-transition-recovery/maintenance-route.ts";

function request(authorization = "Bearer cron-secret") {
  return new Request(
    "https://watchsignal.test/api/maintenance/private-transition-recovery",
    { headers: { Authorization: authorization } },
  );
}

test("R2 scheduled cleanup requires its cron secret and forwards both server secrets", async () => {
  const calls = [];
  const response = await handlePrivateTransitionRecoveryMaintenance(request(), {
    environment: {
      API_BASE_URL: "https://api.watchsignal.test/base/",
      BACKEND_SERVICE_TOKEN: "backend-secret",
      CRON_SECRET: "cron-secret",
    },
    fetchImpl: async (url, init) => {
      calls.push({ url: String(url), init });
      return Response.json({ deleted: 7 });
    },
  });

  assert.equal(response.status, 200);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.deepEqual(await response.json(), { deleted: 7 });
  assert.equal(calls.length, 1);
  assert.equal(
    calls[0].url,
    "https://api.watchsignal.test/maintenance/private-transition-recoveries",
  );
  assert.equal(calls[0].init.method, "POST");
  assert.equal(calls[0].init.headers.Authorization, "Bearer backend-secret");
  assert.equal(calls[0].init.headers["X-WatchSignal-Cron-Secret"], "cron-secret");
});

test("R2 scheduled cleanup fails closed and never reflects upstream detail", async () => {
  let fetchCount = 0;
  for (const environment of [
    { BACKEND_SERVICE_TOKEN: "backend-secret", CRON_SECRET: "" },
    { BACKEND_SERVICE_TOKEN: "", CRON_SECRET: "cron-secret" },
  ]) {
    const response = await handlePrivateTransitionRecoveryMaintenance(request(), {
      environment,
      fetchImpl: async () => {
        fetchCount += 1;
        return Response.json({ deleted: 0 });
      },
    });
    assert.equal(response.status, 503);
    assert.equal(response.headers.get("cache-control"), "no-store");
  }
  assert.equal(fetchCount, 0);

  const unauthorized = await handlePrivateTransitionRecoveryMaintenance(
    request("Bearer wrong-secret"),
    {
      environment: {
        BACKEND_SERVICE_TOKEN: "backend-secret",
        CRON_SECRET: "cron-secret",
      },
      fetchImpl: async () => {
        fetchCount += 1;
        return Response.json({ deleted: 0 });
      },
    },
  );
  assert.equal(unauthorized.status, 401);
  assert.equal(fetchCount, 0);

  for (const fetchImpl of [
    async () => Response.json({ detail: "raw token movie household" }, { status: 500 }),
    async () => {
      throw new Error("raw token movie household");
    },
    async () => Response.json({ deleted: 2, ids: ["private-id"] }),
  ]) {
    const response = await handlePrivateTransitionRecoveryMaintenance(request(), {
      environment: {
        API_BASE_URL: "https://api.watchsignal.test",
        BACKEND_SERVICE_TOKEN: "backend-secret",
        CRON_SECRET: "cron-secret",
      },
      fetchImpl,
    });
    const serialized = JSON.stringify(await response.json());
    assert.equal(response.status, 502);
    assert.doesNotMatch(serialized, /raw|token|movie|household|private-id/u);
  }
});

test("R2 production schedule and hosted preflight require cleanup configuration", async () => {
  const [route, vercel, example, preflight] = await Promise.all([
    readFile(
      new URL(
        "../app/api/maintenance/private-transition-recovery/route.ts",
        import.meta.url,
      ),
      "utf8",
    ),
    readFile(new URL("../vercel.json", import.meta.url), "utf8"),
    readFile(new URL("../../../.env.example", import.meta.url), "utf8"),
    readFile(
      new URL("../../../scripts/hosted_android_preflight.mjs", import.meta.url),
      "utf8",
    ),
  ]);
  assert.match(route, /handlePrivateTransitionRecoveryMaintenance/);
  assert.deepEqual(JSON.parse(vercel).crons, [
    {
      path: "/api/maintenance/private-transition-recovery",
      schedule: "0 3 * * *",
    },
  ]);
  assert.match(example, /^WATCHSIGNAL_HOUSEHOLD_ID=/mu);
  assert.match(example, /^CRON_SECRET=/mu);
  assert.match(preflight, /WATCHSIGNAL_HOUSEHOLD_ID=/u);
  assert.match(preflight, /CRON_SECRET=/u);
});
