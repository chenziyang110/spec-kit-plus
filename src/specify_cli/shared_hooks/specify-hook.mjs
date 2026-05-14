#!/usr/bin/env node
import { accessSync, constants } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

function exists(path) {
  try {
    accessSync(path, constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

function projectRoot() {
  for (const key of ["CLAUDE_PROJECT_DIR", "GEMINI_PROJECT_DIR", "SPECIFY_PROJECT_DIR"]) {
    const value = (process.env[key] || "").trim();
    if (value) {
      return resolve(value);
    }
  }

  const scriptDir = dirname(fileURLToPath(import.meta.url));
  return resolve(scriptDir, "..", "..");
}

function pythonCandidates(root) {
  if (process.platform === "win32") {
    return [
      [resolve(root, ".venv", "Scripts", "python.exe")],
      ["py"],
      ["python"],
    ];
  }

  return [
    [resolve(root, ".venv", "bin", "python")],
    ["python3"],
    ["python"],
  ];
}

function runtimeArgvFromJson() {
  const raw = (process.env.SPECIFY_HOOK_RUNTIME_ARGV || "").trim();
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length > 0 && parsed.every((item) => typeof item === "string" && item.length > 0)) {
      return parsed;
    }
  } catch {
    return null;
  }

  return null;
}

function splitRuntimeCommand(command) {
  const args = [];
  let current = "";
  let quote = null;

  for (let index = 0; index < command.length; index += 1) {
    const char = command[index];
    if (quote) {
      if (char === quote) {
        quote = null;
      } else {
        current += char;
      }
      continue;
    }

    if (char === "'" || char === '"') {
      quote = char;
      continue;
    }

    if (/\s/.test(char)) {
      if (current) {
        args.push(current);
        current = "";
      }
      continue;
    }

    current += char;
  }

  if (quote) {
    return null;
  }

  if (current) {
    args.push(current);
  }

  return args.length > 0 ? args : null;
}

function runtimeArgvFromCommand() {
  const raw = (process.env.SPECIFY_HOOK_RUNTIME_COMMAND || "").trim();
  if (!raw) {
    return null;
  }

  return splitRuntimeCommand(raw);
}

function runnable(command) {
  if (command.includes("/") || command.includes("\\")) {
    return exists(command);
  }

  const probe = process.platform === "win32"
    ? spawnSync("where", [command], { stdio: "ignore", shell: false })
    : spawnSync("command", ["-v", command], { stdio: "ignore", shell: true });

  return probe.status === 0;
}

function resolvePython(root) {
  const runtimeArgv = runtimeArgvFromJson() || runtimeArgvFromCommand();
  if (runtimeArgv) {
    return runtimeArgv;
  }

  for (const candidate of pythonCandidates(root)) {
    if (runnable(candidate[0])) {
      return candidate;
    }
  }
  return null;
}

function main() {
  const args = process.argv.slice(2);
  if (args.length !== 2) {
    console.error("Usage: specify-hook.mjs <integration> <route>");
    return 2;
  }

  const root = projectRoot();
  const launcher = resolve(root, ".specify", "bin", "specify-hook.py");
  if (!exists(launcher)) {
    console.error("Missing .specify/bin/specify-hook.py. Run 'specify integration repair'.");
    return 2;
  }

  const python = resolvePython(root);
  if (!python) {
    console.error("No usable Python runtime found for native hook launcher. Run 'specify integration repair' or install Python.");
    return 2;
  }

  const child = spawnSync(python[0], [...python.slice(1), launcher, ...args], {
    cwd: root,
    env: process.env,
    stdio: "inherit",
    shell: false,
  });

  if (child.error) {
    console.error(`Failed to start native hook launcher: ${child.error.message}`);
    return 2;
  }

  return child.status ?? 2;
}

process.exitCode = main();
