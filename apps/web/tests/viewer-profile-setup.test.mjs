import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

import {
  hasDistinctViewerProfiles,
  profileNameIssue,
  viewerModeOptions,
  viewerSetupMessage,
} from "../app/pass-the-phone/viewer-profile-contract.ts";
import { participantIdForActor } from "../app/pass-the-phone/session-lifecycle.ts";

const profiles = [
  { id: "husband", label: "Cezary", order: 1, avatarKey: "spark", colorKey: "cyan" },
  { id: "wife", label: "Partner", order: 2, avatarKey: "moon", colorKey: "rose" },
];

test("S08 exposes the three exact viewer modes without changing PeopleMode values", () => {
  assert.deepEqual(viewerModeOptions("Cezary", "Partner"), [
    { value: "couple", label: "Couple", detail: "Cezary + Partner" },
    { value: "founder", label: "Husband solo", detail: "Cezary" },
    { value: "wife", label: "Wife solo", detail: "Partner" },
  ]);
});

test("S08 preserves actor-to-profile mapping across couple and solo modes", () => {
  assert.equal(participantIdForActor("couple", ["husband", "wife"], "founder"), "husband");
  assert.equal(participantIdForActor("couple", ["husband", "wife"], "wife"), "wife");
  assert.equal(participantIdForActor("founder", ["husband"], "founder"), "husband");
  assert.equal(participantIdForActor("wife", ["wife"], "wife"), "wife");
});

test("S08 blocks ambiguous identities and normalized duplicate names", () => {
  assert.equal(hasDistinctViewerProfiles("couple", "husband", "husband"), false);
  assert.equal(hasDistinctViewerProfiles("couple", "husband", "wife"), true);
  assert.equal(hasDistinctViewerProfiles("founder", "husband", "husband"), true);
  assert.equal(profileNameIssue("  cezary ", profiles), "That profile already exists.");
  assert.equal(profileNameIssue("", profiles), "Enter a name.");
  assert.equal(profileNameIssue("A third person", profiles), null);
});

test("S08 presents public recovery copy rather than internal service language", () => {
  const failure = viewerSetupMessage("Setup API is not reachable at 127.0.0.1", "create");
  assert.equal(failure, "New profiles need a connection. The name is still here.");
  assert.doesNotMatch(failure, /api|backend|127\.0\.0\.1/i);
});

test("S08 source retains unresolved input and uses a single dominant Continue", async () => {
  const source = await readFile(
    new URL("../app/pass-the-phone/viewer-profile-setup.tsx", import.meta.url),
    "utf8",
  );
  assert.match(source, /maxLength=\{28\}/);
  assert.match(source, /profiles\.some/);
  assert.match(source, /setNewProfileName\(""\)/);
  assert.doesNotMatch(source, /await onCreateProfile[^]*setNewProfileName\(""\)/);
  assert.equal((source.match(/"Continue"/g) ?? []).length, 1);
  assert.match(source, /AccessibleModal/);
});

test("S08 CSS meets compact phone and resilience floors", async () => {
  const css = await readFile(
    new URL("../app/pass-the-phone/viewer-profile-setup.module.css", import.meta.url),
    "utf8",
  );
  const pixelFonts = [...css.matchAll(/font-size:\s*(\d+)px/g)].map((match) => Number(match[1]));
  assert.ok(pixelFonts.every((size) => size >= 12));
  assert.match(css, /width:\s*44px/);
  assert.match(css, /min-height:\s*48px/);
  assert.match(css, /min-height:\s*54px/);
  assert.match(css, /max-height:\s*568px/);
  assert.match(css, /prefers-reduced-motion: reduce/);
  assert.match(css, /prefers-reduced-transparency: reduce/);
  assert.match(css, /forced-colors: active/);
});
