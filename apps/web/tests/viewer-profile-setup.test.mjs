import assert from "node:assert/strict";
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
