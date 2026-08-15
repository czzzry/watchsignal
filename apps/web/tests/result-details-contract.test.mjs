import assert from "node:assert/strict";
import test from "node:test";

import {
  personInitials,
  resultDetailsCast,
  resultEvidence,
  resultProviderPresentation,
  verifiedProviderLaunchUrl,
} from "../app/pass-the-phone/results/result-details-contract.ts";
import { demoCandidates } from "../app/session-fixtures.ts";

test("Arrival fixture uses the verified golden cast manifest without inventing roles", () => {
  const arrival = demoCandidates.find((candidate) => candidate.id === "arrival");
  assert.ok(arrival);

  assert.deepEqual(resultDetailsCast(arrival), [
    {
      name: "Amy Adams",
      character: "Louise Banks",
      profileUrl: "https://image.tmdb.org/t/p/w185/1h2r2VTpoFb5QefAaBYYQgQzL9z.jpg",
    },
    {
      name: "Jeremy Renner",
      character: "Ian Donnelly",
      profileUrl: "https://image.tmdb.org/t/p/w185/yB84D1neTYXfWBaV0QOE9RF2VCu.jpg",
    },
    {
      name: "Forest Whitaker",
      character: "Colonel Weber",
      profileUrl: "https://image.tmdb.org/t/p/w185/4w7l5JUwnwFNBy7J93ZwYN1nihm.jpg",
    },
  ]);
});

test("name-only compatibility renders deliberate initials without fabricated character data", () => {
  assert.deepEqual(
    resultDetailsCast({
      topCast: ["Daniel Craig", "Ana de Armas", "Chris Evans"],
    }),
    [
      { name: "Daniel Craig", character: null, profileUrl: null },
      { name: "Ana de Armas", character: null, profileUrl: null },
      { name: "Chris Evans", character: null, profileUrl: null },
    ],
  );
  assert.equal(personInitials("Daniel Craig"), "DC");
  assert.equal(personInitials("Cher"), "C");
});

test("structured cast safely completes a partial name-only cast without changing its order", () => {
  assert.deepEqual(
    resultDetailsCast({
      topCast: ["Amy Adams"],
      castDetails: [
        { name: "Amy Adams", character: "Louise Banks" },
        { name: "Jeremy Renner", character: "Ian Donnelly" },
        { name: "Forest Whitaker", character: "Colonel Weber" },
      ],
    }).map((member) => member.name),
    ["Amy Adams", "Jeremy Renner", "Forest Whitaker"],
  );
});

test("details evidence is exactly three factual items from reaction, tone, and runtime", () => {
  assert.deepEqual(
    resultEvidence({
      reactions: "Both interested.",
      tone: "Smart, tense, emotional",
      runtime: "1h 56m",
    }),
    ["Both interested", "Smart, tense, emotional", "Under two hours"],
  );
});

test("DE provider presentation exposes access type and retains an honest missing state", () => {
  assert.deepEqual(
    resultProviderPresentation({
      providerAvailability: [
        { providerName: "Amazon Video", accessType: "rent", region: "DE" },
        { providerName: "Amazon Video", accessType: "buy", region: "DE" },
      ],
      fallbackAvailability: "",
    }),
    {
      providerLabel: "Amazon Video",
      accessLabel: "Rent or buy",
      regionLabel: "Region DE",
    },
  );
  assert.deepEqual(
    resultProviderPresentation({
      providerAvailability: [],
      fallbackAvailability: "Provider check needed",
    }),
    {
      providerLabel: "Provider check needed",
      accessLabel: "Confirm access in your provider app",
      regionLabel: "Region DE",
    },
  );
});

test("provider launch accepts only explicit web URLs", () => {
  assert.equal(
    verifiedProviderLaunchUrl("https://www.amazon.de/gp/video/detail/example"),
    "https://www.amazon.de/gp/video/detail/example",
  );
  assert.equal(verifiedProviderLaunchUrl("javascript:alert(1)"), null);
  assert.equal(verifiedProviderLaunchUrl("Amazon Video"), null);
  assert.equal(verifiedProviderLaunchUrl(), null);
});
