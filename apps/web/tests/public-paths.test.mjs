import assert from "node:assert/strict";
import test from "node:test";

import { isPublicAppPath } from "../app/auth/public-paths.ts";

test("public product pages stay available without a household session", () => {
  assert.equal(isPublicAppPath("/showcase"), true);
  assert.equal(isPublicAppPath("/showcase/flow"), true);
  assert.equal(isPublicAppPath("/credits"), true);
});

test("household and private research pages remain protected", () => {
  assert.equal(isPublicAppPath("/"), false);
  assert.equal(isPublicAppPath("/setup"), false);
  assert.equal(isPublicAppPath("/taste-lab"), false);
  assert.equal(isPublicAppPath("/api/session"), false);
});
