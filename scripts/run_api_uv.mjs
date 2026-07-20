#!/usr/bin/env node

import { accessSync, constants, existsSync, mkdirSync } from "node:fs";
import { basename, delimiter, dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";

const DEFAULT_UV_VERSION = "0.11.24";
const scriptPath = fileURLToPath(import.meta.url);
export const repoRoot = resolve(dirname(scriptPath), "..");

export function uvCandidatePaths({
  root = repoRoot,
  environment = process.env,
  sharedCheckoutRoot = discoverSharedCheckoutRoot(root),
  platform = process.platform,
} = {}) {
  const executableName = platform === "win32" ? "uv.exe" : "uv";
  const binDirectory = platform === "win32" ? "Scripts" : "bin";
  const candidates = [];

  if (environment.MOVIE_NIGHT_UV) {
    candidates.push(resolve(environment.MOVIE_NIGHT_UV));
  }
  candidates.push(join(root, ".tools", "uv", binDirectory, executableName));
  if (sharedCheckoutRoot && resolve(sharedCheckoutRoot) !== resolve(root)) {
    candidates.push(
      join(sharedCheckoutRoot, ".tools", "uv", binDirectory, executableName),
    );
  }
  for (const pathEntry of (environment.PATH ?? "").split(delimiter)) {
    if (pathEntry) {
      candidates.push(join(pathEntry, executableName));
    }
  }

  return Array.from(new Set(candidates));
}

export function resolveUvExecutable(options = {}) {
  return uvCandidatePaths(options).find(isExecutable) ?? null;
}

export function ensureUvExecutable(options = {}) {
  const existing = resolveUvExecutable(options);
  if (existing) {
    return existing;
  }

  const root = options.root ?? repoRoot;
  const environment = options.environment ?? process.env;
  if (environment.MOVIE_NIGHT_UV_BOOTSTRAP === "0") {
    throw new Error(missingUvMessage());
  }

  const python = resolvePythonExecutable(environment);
  if (!python) {
    throw new Error(`${missingUvMessage()} Python 3 is also unavailable for local bootstrap.`);
  }

  const uvHome = join(root, ".tools", "uv");
  const binDirectory = process.platform === "win32" ? "Scripts" : "bin";
  const uvExecutable = join(
    uvHome,
    binDirectory,
    process.platform === "win32" ? "uv.exe" : "uv",
  );
  const venvPython = join(
    uvHome,
    binDirectory,
    process.platform === "win32" ? "python.exe" : "python",
  );
  const version = environment.MOVIE_NIGHT_UV_VERSION ?? DEFAULT_UV_VERSION;

  mkdirSync(join(root, ".tools"), { recursive: true });
  runSetupCommand(python, ["-m", "venv", uvHome], root);
  runSetupCommand(
    venvPython,
    [
      "-m",
      "pip",
      "install",
      "--disable-pip-version-check",
      `uv==${version}`,
    ],
    root,
  );

  if (!isExecutable(uvExecutable)) {
    throw new Error(`uv ${version} bootstrap completed without creating ${uvExecutable}.`);
  }
  return uvExecutable;
}

export function uvEnvironment({ root = repoRoot, environment = process.env } = {}) {
  return {
    ...environment,
    UV_CACHE_DIR: environment.UV_CACHE_DIR ?? join(root, ".tools", "uv-cache"),
  };
}

export function discoverSharedCheckoutRoot(root = repoRoot) {
  const result = spawnSync(
    "git",
    ["rev-parse", "--path-format=absolute", "--git-common-dir"],
    { cwd: root, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] },
  );
  if (result.status !== 0) {
    return null;
  }

  const commonDirectory = result.stdout.trim();
  return basename(commonDirectory) === ".git" ? dirname(commonDirectory) : null;
}

function isExecutable(path) {
  if (!existsSync(path)) {
    return false;
  }
  try {
    accessSync(path, process.platform === "win32" ? constants.F_OK : constants.X_OK);
    return true;
  } catch {
    return false;
  }
}

function resolvePythonExecutable(environment) {
  const names = process.platform === "win32" ? ["python.exe"] : ["python3", "python"];
  for (const name of names) {
    for (const pathEntry of (environment.PATH ?? "").split(delimiter)) {
      const candidate = pathEntry ? join(pathEntry, name) : null;
      if (candidate && isExecutable(candidate)) {
        return candidate;
      }
    }
  }
  return null;
}

function runSetupCommand(command, args, cwd) {
  const result = spawnSync(command, args, { cwd, stdio: "inherit" });
  if (result.error) {
    throw result.error;
  }
  if (result.status !== 0) {
    throw new Error(`${command} exited with status ${result.status}.`);
  }
}

function missingUvMessage() {
  return "uv was not found via MOVIE_NIGHT_UV, repository tools, the shared checkout, or PATH.";
}

function runCli() {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.error("Usage: node scripts/run_api_uv.mjs <uv arguments>");
    return 2;
  }

  const uvExecutable = ensureUvExecutable();
  const result = spawnSync(uvExecutable, args, {
    cwd: join(repoRoot, "apps", "api"),
    env: uvEnvironment(),
    stdio: "inherit",
  });
  if (result.error) {
    throw result.error;
  }
  return result.status ?? 1;
}

if (process.argv[1] && pathToFileURL(resolve(process.argv[1])).href === import.meta.url) {
  try {
    process.exitCode = runCli();
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  }
}
