import assert from "node:assert/strict";
import test from "node:test";

import {
  createPrivateTransitionCommandId,
  createPrivateTransitionToken,
  founderSealCommandFingerprint,
  privateTransitionCommandFingerprint,
  recoveryMovieDisplayFromCandidate,
  stableRecoveryCommandJson,
  stableCanonicalJson,
} from "../app/pass-the-phone/private-transition-command.ts";

const command = {
  kind: "seal_founder_ballot",
  workflowVersion: 1,
  payloadVersion: 1,
  canonicalSessionId: "session-1",
  commandId: "0".repeat(64),
  ballot: [
    { sourceMovieId: "tmdb:1", reaction: "interested" },
    { sourceMovieId: "tmdb:2", reaction: "maybe" },
    { sourceMovieId: "tmdb:3", reaction: "no" },
    { sourceMovieId: "tmdb:4", reaction: "seen" },
    { sourceMovieId: "tmdb:5", reaction: "interested" },
  ],
  displaySnapshot: Array.from({ length: 5 }, (_, index) => ({
    sourceMovieId: `tmdb:${index + 1}`,
    title: `Movie ${index + 1}`,
    year: 2021 + index,
    runtimeLabel: "Runtime check needed",
    posterUrl: `https://image.tmdb.org/t/p/w500/${index + 1}.jpg`,
    backdropUrl: null,
    providerUrl: null,
    synopsis: "",
    genres: [],
    cast: [],
    providers: [],
    matchedPersonNames: [],
    safePickStatus: "Safe Pick",
    availability: "Availability check needed",
    languageAccess: "Audio and subtitle details need a quick check",
    tone: "Balanced pick",
    positiveEvidence: [],
    penalties: [],
  })),
};

test("TypeScript and Python share one founder-seal canonical fingerprint", async () => {
  const canonical = stableRecoveryCommandJson(command);

  assert.equal(new TextEncoder().encode(canonical).byteLength, 2878);
  assert.equal(
    await founderSealCommandFingerprint(command),
    "4f4b072608b83094dd905a6bfb12375f059aef39bb884a454e03e738b7ea34f6",
  );
});

test("canonical JSON recursively sorts object keys but preserves array order", () => {
  assert.equal(
    stableCanonicalJson({ z: 1, nested: { b: 2, a: 1 }, list: [3, 2, 1] }),
    '{"list":[3,2,1],"nested":{"a":1,"b":2},"z":1}',
  );
});

test("later-stage command fingerprints also match Python golden vectors", async () => {
  const openSecondPass = {
    kind: "open_second_pass",
    workflowVersion: 1,
    payloadVersion: 1,
    canonicalSessionId: "session-1",
    commandId: "8".repeat(64),
  };
  const finalSeal = {
    ...command,
    kind: "seal_final_ballot",
    commandId: "7".repeat(64),
    ballot: [
      { sourceMovieId: "tmdb:1", reaction: "maybe" },
      { sourceMovieId: "tmdb:2", reaction: "interested" },
      { sourceMovieId: "tmdb:3", reaction: "seen" },
      { sourceMovieId: "tmdb:4", reaction: "no" },
      { sourceMovieId: "tmdb:5", reaction: "interested" },
    ],
  };

  assert.equal(
    await privateTransitionCommandFingerprint(openSecondPass),
    "7ef75e3ce6ef751f0bc0cd5c27646c104f0d021cb645b6da3975c9fb918d9cd7",
  );
  assert.equal(
    await privateTransitionCommandFingerprint(finalSeal),
    "3b71edaf54d1ae19ede536eb32471640dd762a08e32685152965a9f4ac3ed778",
  );
});

test("recovery tokens contain exactly 32 random bytes with no padding", () => {
  const token = createPrivateTransitionToken();
  const decoded = Buffer.from(token, "base64url");

  assert.match(token, /^[A-Za-z0-9_-]{43}$/);
  assert.equal(decoded.byteLength, 32);
  assert.equal(token.includes("="), false);
});

test("recovery command ids contain exactly 32 random bytes as lowercase hex", () => {
  assert.match(createPrivateTransitionCommandId(), /^[0-9a-f]{64}$/);
});

test("candidate recovery keeps display fields but excludes raw scorer and profile data", () => {
  const display = recoveryMovieDisplayFromCandidate({
    id: "tmdb:1",
    title: "Arrival",
    year: 2016,
    runtime: "1h 56m",
    posterUrl: "https://image.tmdb.org/t/p/w500/poster.jpg",
    backdropUrl: "https://image.tmdb.org/t/p/original/backdrop.jpg",
    providerUrl: "https://www.amazon.de/gp/video/detail/example",
    topCast: ["Amy Adams"],
    castDetails: [
      {
        name: "Amy Adams",
        character: "Louise Banks",
        profileUrl: "https://image.tmdb.org/t/p/w185/amy.jpg",
      },
    ],
    providerAvailability: [
      { providerName: "Amazon Video", accessType: "rent", region: "DE" },
    ],
    matchedPersonNames: ["Amy Adams"],
    genres: ["Drama", "Mystery"],
    safePickStatus: "Safe Pick",
    availability: "Amazon Video - rent in Germany",
    languageAccess: "English audio available",
    tone: "Thoughtful and tense",
    reason: "raw scorer explanation must not be stored",
    overview: "A verified synopsis.",
    whyNow: "raw private narrative",
    groupScore: 0.84,
    dominantPositiveEvidence: [
      "nudge_person:Amy Adams",
      "nudge_person:husband-profile",
      "title_similarity:Private saved title",
      "learned_taste:profile-123",
      "debug:profile-id:husband-profile",
    ],
    dominantPenalties: [
      "nudge_signal:avoid:superhero",
      "scorer_internal:raw-weight",
    ],
    baseRank: 1,
    taste: { founder: 90, wife: 70 },
    provenance: {
      poster: "api-payload",
      criticScore: "not-provided",
      descriptiveCopy: "api-payload",
    },
  });
  const serialized = JSON.stringify(display);

  assert.equal(display.synopsis, "A verified synopsis.");
  assert.equal(display.cast[0].name, "Amy Adams");
  assert.deepEqual(display.positiveEvidence, [
    "nudge_person:Amy Adams",
    "title_similarity:present",
    "learned_taste:present",
  ]);
  assert.deepEqual(display.penalties, ["nudge_signal:avoid:superhero"]);
  assert.doesNotMatch(
    serialized,
    /raw scorer|raw private|groupScore|"taste":|provenance/,
  );
  assert.doesNotMatch(
    serialized,
    /profile-id|husband-profile|profile-123|Private saved title|scorer_internal|raw-weight/,
  );
});

test("candidate recovery bounds live provider text to the durable schema", () => {
  const display = recoveryMovieDisplayFromCandidate({
    id: "tmdb:bounded",
    title: `  ${"T".repeat(240)}  `,
    year: 2026,
    runtime: `  ${"R".repeat(60)}  `,
    posterUrl: `https://example.com/${"p".repeat(2_100)}`,
    backdropUrl: "https://example.com/backdrop.jpg",
    providerUrl: "https://example.com/watch",
    topCast: [],
    castDetails: [{
      name: ` ${"N".repeat(120)} `,
      character: ` ${"C".repeat(140)} `,
      profileUrl: "https://example.com/person.jpg",
    }],
    providerAvailability: [{
      providerName: ` ${"P".repeat(120)} `,
      accessType: ` ${"A".repeat(60)} `,
      region: ` ${"D".repeat(12)} `,
    }],
    matchedPersonNames: [` ${"M".repeat(120)} `],
    genres: [` ${"G".repeat(60)} `],
    safePickStatus: "Safe Pick",
    availability: ` ${"V".repeat(280)} `,
    languageAccess: ` ${"L".repeat(200)} `,
    tone: ` ${"O".repeat(150)} `,
    reason: "internal",
    overview: ` ${"S".repeat(1_700)} `,
    dominantPositiveEvidence: [
      `nudge_signal:include:${"i".repeat(180)}`,
    ],
    dominantPenalties: [
      `nudge_signal:avoid:${"x".repeat(180)}`,
    ],
    baseRank: 1,
    taste: { founder: 80, wife: 80 },
    provenance: {
      poster: "api-payload",
      criticScore: "not-provided",
      descriptiveCopy: "api-payload",
    },
  });

  assert.equal(display.title.length, 200);
  assert.equal(display.runtimeLabel.length, 40);
  assert.equal(display.posterUrl, null);
  assert.equal(display.synopsis.length, 1_500);
  assert.equal(display.genres[0].length, 40);
  assert.equal(display.cast[0].name.length, 100);
  assert.equal(display.cast[0].character.length, 120);
  assert.equal(display.providers[0].providerName.length, 100);
  assert.equal(display.providers[0].accessType.length, 40);
  assert.equal(display.providers[0].region.length, 8);
  assert.equal(display.matchedPersonNames[0].length, 100);
  assert.equal(display.availability.length, 240);
  assert.equal(display.languageAccess.length, 160);
  assert.equal(display.tone.length, 120);
  assert.equal(display.positiveEvidence[0].length, 160);
  assert.equal(display.penalties[0].length, 160);
});

test("candidate recovery truncates Unicode on whole code points", () => {
  const display = recoveryMovieDisplayFromCandidate({
    id: "tmdb:unicode",
    title: `${"T".repeat(199)}🎬Z`,
    year: 2026,
    runtime: "2h",
    topCast: [],
    genres: [],
    safePickStatus: "Safe Pick",
    availability: "Available",
    languageAccess: "English audio",
    tone: "Warm",
    reason: "internal",
    baseRank: 1,
    taste: { founder: 80, wife: 80 },
    provenance: {
      poster: "fallback-placeholder",
      criticScore: "not-provided",
      descriptiveCopy: "generic-fallback",
    },
  });

  assert.equal(Array.from(display.title).length, 200);
  assert.equal(display.title.endsWith("🎬"), true);
  assert.doesNotMatch(display.title, /[\uD800-\uDFFF]$/u);
});

test("non-HTTPS or local artwork becomes an explicit missing-data fallback", () => {
  const display = recoveryMovieDisplayFromCandidate({
    id: "tmdb:2",
    title: "Missing art",
    year: 2026,
    runtime: "Runtime check needed",
    posterUrl: "/fallback-poster.svg",
    backdropUrl: "http://unsafe.example/backdrop.jpg",
    providerUrl: "javascript:bad",
    topCast: [],
    genres: [],
    safePickStatus: "Needs Quick Check",
    availability: "Availability check needed",
    languageAccess: "Audio and subtitle details need a quick check",
    tone: "Balanced pick",
    reason: "internal",
    baseRank: 2,
    taste: { founder: 50, wife: 50 },
    provenance: {
      poster: "fallback-placeholder",
      criticScore: "not-provided",
      descriptiveCopy: "generic-fallback",
    },
  });

  assert.equal(display.posterUrl, null);
  assert.equal(display.backdropUrl, null);
  assert.equal(display.providerUrl, null);
});
