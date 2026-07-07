#!/usr/bin/env node

import { existsSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";

const repoRoot = new URL("..", import.meta.url).pathname;

const checks = [];

function ok(label, detail = "") {
  checks.push({ level: "ok", label, detail });
}

function warn(label, detail = "") {
  checks.push({ level: "warn", label, detail });
}

function fail(label, detail = "") {
  checks.push({ level: "fail", label, detail });
}

function pathExists(relativePath) {
  return existsSync(join(repoRoot, relativePath));
}

function run(command, args) {
  return spawnSync(command, args, {
    cwd: repoRoot,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
}

function checkRequiredPath(relativePath, label = relativePath) {
  if (pathExists(relativePath)) {
    ok(label);
  } else {
    fail(label, `${relativePath} is missing.`);
  }
}

function checkOptionalEnv(name, detail) {
  if (process.env[name]) {
    ok(`${name} is set`);
  } else {
    warn(`${name} is not set`, detail);
  }
}

function checkPackageScripts() {
  const packagePath = join(repoRoot, "package.json");
  const packageJson = JSON.parse(readFileSync(packagePath, "utf8"));
  const scripts = packageJson.scripts ?? {};
  for (const scriptName of [
    "beta:preflight",
    "beta:check",
    "beta:dogfood",
    "check",
    "smoke:ux:mobile",
  ]) {
    if (scripts[scriptName]) {
      ok(`package script ${scriptName}`);
    } else {
      fail(`package script ${scriptName}`, "Expected script is missing.");
    }
  }
}

function checkCommand(command, args, label) {
  const result = run(command, args);
  if (result.status === 0) {
    ok(label, result.stdout.trim().split("\n")[0] ?? "");
  } else {
    fail(label, result.stderr.trim() || result.stdout.trim());
  }
}

function checkGitState() {
  const result = run("git", ["status", "--short", "--branch"]);
  if (result.status !== 0) {
    warn("git status unavailable", result.stderr.trim());
    return;
  }
  const output = result.stdout.trim();
  if (output.split("\n").length === 1) {
    ok("working tree is clean", output);
  } else {
    warn("working tree has local changes", output);
  }
}

checkRequiredPath("README.md");
checkRequiredPath(".env.example");
checkRequiredPath("apps/api/src/movie_night_mediator/api/main.py", "FastAPI app entrypoint");
checkRequiredPath("apps/web/app/page.tsx", "Next.js app entrypoint");
checkRequiredPath("scripts/mobile_pass_the_phone_ux_smoke.mjs", "mobile UX smoke");
checkRequiredPath("docs/setup/mobile-pass-the-phone-ux-smoke.md", "mobile smoke documentation");
checkRequiredPath("docs/beta-readiness/fresh-checkout-runbook.md", "fresh checkout runbook");
checkRequiredPath("docs/beta-readiness/dogfood-checklist.md", "dogfood checklist");
checkRequiredPath("docs/beta-readiness/environment-and-secrets.md", "environment guide");
checkPackageScripts();
checkCommand("node", ["--version"], "Node.js is available");
checkCommand("pnpm", ["--version"], "pnpm is available");

if (pathExists(".tools/uv/bin/uv")) {
  ok("repo-local uv is available", ".tools/uv/bin/uv");
} else if (pathExists("../../.tools/uv/bin/uv")) {
  ok("parent uv is available", "../../.tools/uv/bin/uv");
} else {
  warn("uv helper was not found", "pnpm check may still work if the environment supplies uv another way.");
}

if (pathExists("apps/web/node_modules")) {
  ok("web dependencies appear installed", "apps/web/node_modules");
} else {
  warn("web dependencies are not installed", "Run pnpm install before building or dogfooding.");
}

if (pathExists(".env")) {
  ok(".env exists");
} else {
  warn(".env does not exist", "Copy .env.example only when live TMDb or custom local paths are needed.");
}

if (process.env.MOVIE_NIGHT_MEDIATOR_SQLITE_PATH) {
  ok("MOVIE_NIGHT_MEDIATOR_SQLITE_PATH is set");
} else {
  ok("SQLite path will use local default", "data/movie_night_mediator.sqlite3");
}

checkOptionalEnv(
  "API_BASE_URL",
  "The web app defaults to http://127.0.0.1:8000 when this is unset.",
);

if (process.env.TMDB_READ_ACCESS_TOKEN || process.env.TMDB_API_KEY) {
  ok("TMDb credentials are available");
} else {
  warn(
    "TMDb credentials are not set",
    "Demo-safe fixture mode still works. Live TMDb mode needs TMDB_READ_ACCESS_TOKEN or TMDB_API_KEY.",
  );
}

checkGitState();

for (const check of checks) {
  const prefix = check.level === "ok" ? "OK" : check.level === "warn" ? "WARN" : "FAIL";
  const suffix = check.detail ? ` - ${check.detail}` : "";
  console.log(`${prefix}: ${check.label}${suffix}`);
}

const failures = checks.filter((check) => check.level === "fail");
const warnings = checks.filter((check) => check.level === "warn");

console.log("");
console.log(`Beta readiness preflight: ${failures.length} failure(s), ${warnings.length} warning(s).`);

if (failures.length > 0) {
  process.exit(1);
}
