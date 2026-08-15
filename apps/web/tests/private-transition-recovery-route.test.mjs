import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  handlePrivateTransitionRecoveryRequest,
} from "../app/api/private-transition-recovery/recovery-route.ts";
import {
  forwardPrivateTransitionRecovery,
} from "../app/api/private-transition-recovery/backend.ts";

const configuredEnvironment = {
  HOUSEHOLD_ACCESS_PASSWORD: "access-secret",
  HOUSEHOLD_SESSION_SECRET: "session-secret",
  BACKEND_SERVICE_TOKEN: "backend-secret",
  WATCHSIGNAL_HOUSEHOLD_ID: "configured-household",
};

function request(
  body = { token: "A".repeat(43), command: { kind: "open_second_pass" } },
  headers = {},
) {
  return new Request("https://watchsignal.test/api/private-transition-recovery/seal", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Origin: "https://watchsignal.test",
      "X-WatchSignal-Recovery": "1",
      ...headers,
    },
    body: JSON.stringify(body),
  });
}

function dependencies(overrides = {}) {
  const forwarded = [];
  return {
    forwarded,
    ports: {
      environment: configuredEnvironment,
      readSessionCookie: async () => "signed-cookie",
      verifySession: async (token, secret) =>
        token === "signed-cookie" && secret === "session-secret",
      forward: async (operation, payload) => {
        forwarded.push({ operation, payload });
        return Response.json({ version: 1, expiresAtMs: 7_200_000 });
      },
      ...overrides,
    },
  };
}

function safeMovieDisplay(overrides = {}) {
  return {
    availability: "Available to rent",
    backdropUrl: "https://image.test/backdrop.jpg",
    cast: [
      {
        character: "Louise Banks",
        name: "Amy Adams",
        profileUrl: "https://image.test/amy.jpg",
      },
    ],
    genres: ["Drama", "Science Fiction"],
    languageAccess: "English audio",
    matchedPersonNames: ["Amy"],
    penalties: ["nudge_signal:avoid:horror"],
    positiveEvidence: ["shared:overlap_strength", "nudge_person:Amy"],
    posterUrl: "https://image.test/poster.jpg",
    providerUrl: "https://provider.test/watch",
    providers: [
      {
        accessType: "rent",
        providerName: "Amazon Video",
        region: "DE",
      },
    ],
    runtimeLabel: "1h 56m",
    safePickStatus: "Safe Pick",
    sourceMovieId: "arrival-2016",
    synopsis: "A linguist works to understand visitors from another world.",
    title: "Arrival",
    tone: "Thoughtful",
    year: 2016,
    ...overrides,
  };
}

test("R2 forwards an authenticated same-origin request with server-owned tenancy", async () => {
  const fixture = dependencies();
  const response = await handlePrivateTransitionRecoveryRequest(
    "seal",
    request(),
    fixture.ports,
  );

  assert.equal(response.status, 200);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.deepEqual(fixture.forwarded, [
    {
      operation: "seal",
      payload: {
        deploymentTenant: "configured-household",
        token: "A".repeat(43),
        command: { kind: "open_second_pass" },
      },
    },
  ]);
});

test("R2 fails closed when any required server configuration is absent", async () => {
  for (const key of Object.keys(configuredEnvironment)) {
    const fixture = dependencies({
      environment: { ...configuredEnvironment, [key]: "" },
    });
    const response = await handlePrivateTransitionRecoveryRequest(
      "seal",
      request(),
      fixture.ports,
    );
    assert.equal(response.status, 503, key);
    assert.equal(response.headers.get("cache-control"), "no-store", key);
    assert.equal(fixture.forwarded.length, 0, key);
  }
});

test("R2 rejects unauthenticated, cross-origin, and non-JSON browser requests", async () => {
  const unauthenticated = dependencies({ verifySession: async () => false });
  assert.equal(
    (
      await handlePrivateTransitionRecoveryRequest(
        "seal",
        request(),
        unauthenticated.ports,
      )
    ).status,
    401,
  );

  const crossOrigin = dependencies();
  const crossOriginRequest = request(undefined, {
    Origin: "https://attacker.test",
  });
  crossOriginRequest.headers.delete("X-WatchSignal-Recovery");
  assert.equal(
    (
      await handlePrivateTransitionRecoveryRequest(
        "seal",
        crossOriginRequest,
        crossOrigin.ports,
      )
    ).status,
    403,
  );

  const missingOrigin = dependencies();
  const noOriginRequest = request();
  noOriginRequest.headers.delete("Origin");
  noOriginRequest.headers.delete("X-WatchSignal-Recovery");
  assert.equal(
    (
      await handlePrivateTransitionRecoveryRequest(
        "seal",
        noOriginRequest,
        missingOrigin.ports,
      )
    ).status,
    403,
  );

  const refererFallback = dependencies();
  const refererRequest = request();
  refererRequest.headers.delete("Origin");
  refererRequest.headers.delete("X-WatchSignal-Recovery");
  refererRequest.headers.set("Referer", "https://watchsignal.test/");
  assert.equal(
    (
      await handlePrivateTransitionRecoveryRequest(
        "seal",
        refererRequest,
        refererFallback.ports,
      )
    ).status,
    200,
  );

  const foreignReferer = dependencies();
  const foreignRefererRequest = request();
  foreignRefererRequest.headers.delete("Origin");
  foreignRefererRequest.headers.delete("X-WatchSignal-Recovery");
  foreignRefererRequest.headers.set("Referer", "https://attacker.test/");
  assert.equal(
    (
      await handlePrivateTransitionRecoveryRequest(
        "seal",
        foreignRefererRequest,
        foreignReferer.ports,
      )
    ).status,
    403,
  );

  const fetchMetadata = dependencies();
  const fetchMetadataRequest = request();
  fetchMetadataRequest.headers.delete("Origin");
  fetchMetadataRequest.headers.set("Sec-Fetch-Site", "same-origin");
  assert.equal(
    (
      await handlePrivateTransitionRecoveryRequest(
        "seal",
        fetchMetadataRequest,
        fetchMetadata.ports,
      )
    ).status,
    200,
  );

  const applicationMarker = dependencies();
  const applicationMarkerRequest = request();
  applicationMarkerRequest.headers.delete("Origin");
  assert.equal(
    (
      await handlePrivateTransitionRecoveryRequest(
        "seal",
        applicationMarkerRequest,
        applicationMarker.ports,
      )
    ).status,
    200,
  );

  const nonJson = dependencies();
  assert.equal(
    (
      await handlePrivateTransitionRecoveryRequest(
        "seal",
        request(undefined, { "Content-Type": "application/x-www-form-urlencoded" }),
        nonJson.ports,
      )
    ).status,
    415,
  );
});

test("R2 never accepts browser-selected tenancy or a query-string token", async () => {
  const tenant = dependencies();
  assert.equal(
    (
      await handlePrivateTransitionRecoveryRequest(
        "seal",
        request({
          deploymentTenant: "attacker-household",
          token: "A".repeat(43),
          command: { kind: "open_second_pass" },
        }),
        tenant.ports,
      )
    ).status,
    400,
  );
  assert.equal(tenant.forwarded.length, 0);

  const query = dependencies();
  const queryRequest = new Request(
    "https://watchsignal.test/api/private-transition-recovery/seal?token=private",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Origin: "https://watchsignal.test",
      },
      body: JSON.stringify({ token: "A".repeat(43) }),
    },
  );
  assert.equal(
    (
      await handlePrivateTransitionRecoveryRequest(
        "seal",
        queryRequest,
        query.ports,
      )
    ).status,
    400,
  );
  assert.equal(query.forwarded.length, 0);
});

test("R2 backend forwarding keeps the token in JSON and returns only allowlisted success", async () => {
  const calls = [];
  const response = await forwardPrivateTransitionRecovery(
    "seal",
    {
      deploymentTenant: "configured-household",
      token: "A".repeat(43),
      command: { kind: "open_second_pass" },
    },
    {
      environment: {
        API_BASE_URL: "https://api.watchsignal.test/base/",
        BACKEND_SERVICE_TOKEN: "backend-secret",
      },
      fetchImpl: async (url, init) => {
        calls.push({ url: String(url), init });
        return Response.json({ version: 1, expiresAtMs: 7_200_000 });
      },
    },
  );

  assert.equal(response.status, 200);
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.equal(calls.length, 1);
  assert.equal(
    calls[0].url,
    "https://api.watchsignal.test/private-transition-recovery/seal",
  );
  assert.doesNotMatch(calls[0].url, /A{43}|configured-household/u);
  assert.equal(calls[0].init.method, "POST");
  assert.equal(calls[0].init.headers.Authorization, "Bearer backend-secret");
  assert.deepEqual(JSON.parse(calls[0].init.body), {
    deploymentTenant: "configured-household",
    token: "A".repeat(43),
    command: { kind: "open_second_pass" },
  });
  assert.deepEqual(await response.json(), { version: 1, expiresAtMs: 7_200_000 });
});

test("R2 backend forwarding never reflects upstream detail or private fields", async () => {
  const markers = "raw backend token ballot movie title private-marker";
  for (const fetchImpl of [
    async () => Response.json({ detail: markers }, { status: 500 }),
    async () => {
      throw new Error(markers);
    },
    async () =>
      Response.json({
        kind: "handoff_ready",
        recipientLabel: "Sophie",
        canBegin: true,
        ballot: markers,
      }),
  ]) {
    const response = await forwardPrivateTransitionRecovery(
      "resume",
      { deploymentTenant: "configured-household", token: "A".repeat(43) },
      {
        environment: {
          API_BASE_URL: "https://api.watchsignal.test",
          BACKEND_SERVICE_TOKEN: "backend-secret",
        },
        fetchImpl,
      },
    );
    const serialized = JSON.stringify(await response.json());
    assert.equal(response.status, 502);
    assert.equal(response.headers.get("cache-control"), "no-store");
    assert.doesNotMatch(serialized, /private-marker|backend|ballot|movie title/u);
  }
});

test("R2 backend forwarding validates safe resume projections and consume acknowledgement", async () => {
  const environment = {
    API_BASE_URL: "https://api.watchsignal.test",
    BACKEND_SERVICE_TOKEN: "backend-secret",
  };
  const resume = await forwardPrivateTransitionRecovery(
    "resume",
    { deploymentTenant: "configured-household", token: "A".repeat(43) },
    {
      environment,
      fetchImpl: async () =>
        Response.json({
          kind: "handoff_ready",
          recipientLabel: "Sophie",
          canBegin: true,
        }),
    },
  );
  assert.deepEqual(await resume.json(), {
    kind: "handoff_ready",
    recipientLabel: "Sophie",
    canBegin: true,
  });

  const secondPass = await forwardPrivateTransitionRecovery(
    "resume",
    { deploymentTenant: "configured-household", token: "A".repeat(43) },
    {
      environment,
      fetchImpl: async () =>
        Response.json({
          kind: "second_pass_ready",
          displaySnapshot: Array.from({ length: 5 }, (_, index) =>
            safeMovieDisplay({
              sourceMovieId: `movie-${index + 1}`,
              title: `Movie ${index + 1}`,
            }),
          ),
        }),
    },
  );
  assert.equal(secondPass.status, 200);
  assert.equal(secondPass.headers.get("cache-control"), "no-store");
  assert.equal((await secondPass.json()).displaySnapshot.length, 5);

  const result = await forwardPrivateTransitionRecovery(
    "resume",
    { deploymentTenant: "configured-household", token: "A".repeat(43) },
    {
      environment,
      fetchImpl: async () =>
        Response.json({
          kind: "result_ready",
          canonicalSessionId: "session-1",
          resultSource: "local",
          finalReactions: Array.from({ length: 5 }, (_, index) => ({
            sourceMovieId: `movie-${index + 1}`,
            reaction: index % 2 === 0 ? "interested" : "maybe",
          })),
          displaySnapshot: Array.from({ length: 5 }, (_, index) =>
            safeMovieDisplay({
              sourceMovieId: `movie-${index + 1}`,
              title: `Movie ${index + 1}`,
            }),
          ),
        }),
    },
  );
  assert.equal(result.status, 200);
  assert.equal((await result.json()).resultSource, "local");

  const consume = await forwardPrivateTransitionRecovery(
    "consume",
    { deploymentTenant: "configured-household", token: "A".repeat(43) },
    {
      environment,
      fetchImpl: async () => new Response(null, { status: 204 }),
    },
  );
  assert.equal(consume.status, 204);
  assert.equal(consume.headers.get("cache-control"), "no-store");
});

test("R2 backend rejects hostile movie display fields from a successful upstream", async () => {
  const environment = {
    API_BASE_URL: "https://api.watchsignal.test",
    BACKEND_SERVICE_TOKEN: "backend-secret",
  };
  const hostileDisplays = [
    safeMovieDisplay({ posterUrl: "javascript:alert(1)" }),
    safeMovieDisplay({ backdropUrl: "http://image.test/backdrop.jpg" }),
    safeMovieDisplay({ providerUrl: "data:text/html,private" }),
    safeMovieDisplay({
      cast: [
        {
          character: "Louise Banks",
          name: "Amy Adams",
          profileUrl: "file:///private/profile.jpg",
        },
      ],
    }),
    safeMovieDisplay({ genres: ["G".repeat(41)] }),
    safeMovieDisplay({ positiveEvidence: ["private_scorer:raw-weight"] }),
    safeMovieDisplay({ positiveEvidence: [`tonight_intent:${"x".repeat(146)}`] }),
    safeMovieDisplay({ positiveEvidence: ["nudge_person:Not matched"] }),
    safeMovieDisplay({ penalties: ["internal_penalty:raw-weight"] }),
    safeMovieDisplay({ penalties: [`nudge_signal:avoid:${"x".repeat(142)}`] }),
    safeMovieDisplay({ year: 1887 }),
    safeMovieDisplay({ year: 2201 }),
  ];

  for (const hostileDisplay of hostileDisplays) {
    const response = await forwardPrivateTransitionRecovery(
      "resume",
      { deploymentTenant: "configured-household", token: "A".repeat(43) },
      {
        environment,
        fetchImpl: async () =>
          Response.json({
            kind: "second_pass_ready",
            displaySnapshot: [
              hostileDisplay,
              safeMovieDisplay({ sourceMovieId: "movie-2", title: "Movie 2" }),
              safeMovieDisplay({ sourceMovieId: "movie-3", title: "Movie 3" }),
              safeMovieDisplay({ sourceMovieId: "movie-4", title: "Movie 4" }),
              safeMovieDisplay({ sourceMovieId: "movie-5", title: "Movie 5" }),
            ],
          }),
      },
    );

    assert.equal(response.status, 502, JSON.stringify(hostileDisplay));
    assert.deepEqual(await response.json(), {
      detail: "Private transition recovery is temporarily unavailable.",
    });
  }
});

test("R2 production routes use the authenticated stateless handler and body-only operations", async () => {
  const [handler, seal, resume, consume] = await Promise.all([
    readFile(
      new URL(
        "../app/api/private-transition-recovery/route-handler.ts",
        import.meta.url,
      ),
      "utf8",
    ),
    readFile(
      new URL("../app/api/private-transition-recovery/seal/route.ts", import.meta.url),
      "utf8",
    ),
    readFile(
      new URL("../app/api/private-transition-recovery/resume/route.ts", import.meta.url),
      "utf8",
    ),
    readFile(
      new URL("../app/api/private-transition-recovery/consume/route.ts", import.meta.url),
      "utf8",
    ),
  ]);
  assert.match(handler, /SESSION_COOKIE_NAME/);
  assert.match(handler, /verifySessionToken/);
  assert.match(handler, /forwardPrivateTransitionRecovery/);
  assert.match(seal, /handlePrivateTransitionRecoveryRoute\("seal"/);
  assert.match(resume, /handlePrivateTransitionRecoveryRoute\("resume"/);
  assert.match(consume, /handlePrivateTransitionRecoveryRoute\("consume"/);
  assert.doesNotMatch(`${handler}\n${seal}\n${resume}\n${consume}`, /searchParams|get\("token"\)/);
  await assert.rejects(
    readFile(
      new URL("../app/api/private-transition-vault/route.ts", import.meta.url),
      "utf8",
    ),
    { code: "ENOENT" },
  );
});
