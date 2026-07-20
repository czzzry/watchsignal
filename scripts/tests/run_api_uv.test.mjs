import assert from "node:assert/strict";
import { chmodSync, mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { delimiter, join } from "node:path";
import test from "node:test";

import {
  resolveUvExecutable,
  uvCandidatePaths,
  uvEnvironment,
} from "../run_api_uv.mjs";

test("uv candidates prefer explicit, checkout-local, shared, then PATH executables", () => {
  const candidates = uvCandidatePaths({
    root: "/work/feature",
    sharedCheckoutRoot: "/work/main",
    environment: {
      MOVIE_NIGHT_UV: "/opt/uv",
      PATH: ["/usr/local/bin", "/usr/bin"].join(delimiter),
    },
    platform: "linux",
  });

  assert.deepEqual(candidates, [
    "/opt/uv",
    "/work/feature/.tools/uv/bin/uv",
    "/work/main/.tools/uv/bin/uv",
    "/usr/local/bin/uv",
    "/usr/bin/uv",
  ]);
});

test("uv candidates de-duplicate repeated locations", () => {
  const root = "/work/project";
  const localUv = join(root, ".tools", "uv", "bin", "uv");
  const candidates = uvCandidatePaths({
    root,
    sharedCheckoutRoot: root,
    environment: { MOVIE_NIGHT_UV: localUv, PATH: "" },
    platform: "linux",
  });

  assert.deepEqual(candidates, [localUv]);
});

test("uv resolver returns the first executable candidate", () => {
  const root = mkdtempSync(join(tmpdir(), "movie-night-uv-test-"));
  const binDirectory = join(root, "bin");
  const executable = join(binDirectory, "uv");
  mkdirSync(binDirectory);
  writeFileSync(executable, "#!/bin/sh\nexit 0\n");
  chmodSync(executable, 0o755);

  assert.equal(
    resolveUvExecutable({
      root: join(root, "checkout"),
      sharedCheckoutRoot: null,
      environment: { MOVIE_NIGHT_UV: executable, PATH: "" },
      platform: "linux",
    }),
    executable,
  );
});

test("uv environment defaults to a repository-local cache", () => {
  assert.deepEqual(uvEnvironment({ root: "/work/project", environment: { A: "1" } }), {
    A: "1",
    UV_CACHE_DIR: "/work/project/.tools/uv-cache",
  });
});

test("uv environment preserves an explicit cache", () => {
  assert.equal(
    uvEnvironment({
      root: "/work/project",
      environment: { UV_CACHE_DIR: "/cache/uv" },
    }).UV_CACHE_DIR,
    "/cache/uv",
  );
});
