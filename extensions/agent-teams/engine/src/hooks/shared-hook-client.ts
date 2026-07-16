import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { delimiter, join, resolve } from "node:path";

import { packageRoot } from "../utils/paths.js";

export type CodexHookEventName =
  | "SessionStart"
  | "PreToolUse"
  | "PostToolUse"
  | "UserPromptSubmit"
  | "Stop";

export type HookStatus = "ok" | "warn" | "blocked" | "repaired" | "repairable-block";

export interface SharedQualityHookPayload {
  event: string;
  status: HookStatus;
  severity?: string;
  actions?: string[];
  errors?: string[];
  warnings?: string[];
  writes?: Record<string, unknown>;
  data?: Record<string, unknown>;
}

export interface HookInvocationPlan {
  executable: string;
  args: string[];
  env: NodeJS.ProcessEnv;
  shell?: boolean;
}

export interface HookProcessResult {
  status: number | null;
  stdout: string;
  stderr: string;
  errorCode?: string;
  timedOut?: boolean;
}

export type HookProcessRunner = (
  plan: HookInvocationPlan,
  options: { cwd: string; timeoutMs: number; stdinText?: string },
) => HookProcessResult;

export type SharedHookClientResult =
  | { status: "ok"; payload: SharedQualityHookPayload; durationMs: number }
  | { status: "blocked"; payload: SharedQualityHookPayload; durationMs: number }
  | { status: "unavailable"; reason: string; attemptedPlans: string[]; durationMs: number }
  | { status: "timeout"; timeoutMs: number; attemptedPlan: string; durationMs: number }
  | { status: "invalid-output"; stdoutPreview: string; attemptedPlan: string; durationMs: number };

export interface SharedHookInvokeOptions {
  eventName: CodexHookEventName;
  timeoutMs?: number;
  stdinText?: string;
}

export interface SharedHookClientOptions {
  cwd: string;
  env?: NodeJS.ProcessEnv;
  runner?: HookProcessRunner;
  now?: () => number;
}

function repoRootFromPackage(): string {
  return resolve(packageRoot(), "..", "..", "..");
}

function hasRepoSourceCheckout(): boolean {
  return existsSync(join(repoRootFromPackage(), "src", "specify_cli", "__init__.py"));
}

const VALID_HOOK_STATUSES: ReadonlySet<string> = new Set([
  "ok",
  "warn",
  "blocked",
  "repaired",
  "repairable-block",
]);

const SHARED_HOOK_SUCCESS_EXIT_CODE = 0;
const SHARED_HOOK_BLOCKED_EXIT_CODE = 10;

const SENSITIVE_FREE_TEXT_FLAGS: ReadonlySet<string> = new Set([
  "--prompt-text",
  "--free-text",
  "--message-text",
  "--command-text",
]);

function defaultRunner(
  plan: HookInvocationPlan,
  options: { cwd: string; timeoutMs: number; stdinText?: string },
): HookProcessResult {
  const result = spawnSync(plan.executable, plan.args, {
    cwd: options.cwd,
    encoding: "utf-8",
    env: plan.env,
    shell: plan.shell === true,
    input: options.stdinText,
    timeout: options.timeoutMs,
  });
  const error = result.error as NodeJS.ErrnoException | undefined;
  return {
    status: result.status,
    stdout: String(result.stdout ?? ""),
    stderr: String(result.stderr ?? ""),
    errorCode: error?.code,
    timedOut: error?.code === "ETIMEDOUT",
  };
}

function addInvocationPlan(
  plans: HookInvocationPlan[],
  seen: Set<string>,
  executable: string,
  args: string[],
  env: NodeJS.ProcessEnv,
  shell = false,
): void {
  const key = `${executable}\u0000${args.join("\u0000")}`;
  if (seen.has(key)) return;
  seen.add(key);
  plans.push({ executable, args, env, shell });
}

export function buildSharedHookInvocationPlans(
  hookArgs: string[],
  cwd: string,
  env: NodeJS.ProcessEnv = process.env,
): HookInvocationPlan[] {
  const plans: HookInvocationPlan[] = [];
  const seen = new Set<string>();
  const explicit = String(env.SPECIFY_HOOK_EXECUTABLE ?? "").trim();
  if (explicit) {
    const shellBackedOnWindows = /\.cmd$/i.test(explicit) || /\.bat$/i.test(explicit);
    // Do not route untrusted hook args through shell-backed explicit executables.
    // Falling back to direct specify/python plans preserves behavior without shell injection risk.
    if (!shellBackedOnWindows) {
      addInvocationPlan(plans, seen, explicit, ["hook", ...hookArgs], env);
    }
  }

  addInvocationPlan(plans, seen, "specify", ["hook", ...hookArgs], env);

  if (hasRepoSourceCheckout()) {
    const repoRoot = repoRootFromPackage();
    const pythonPath = join(repoRoot, "src");
    const pythonEnv = {
      ...env,
      PYTHONPATH: env.PYTHONPATH ? `${pythonPath}${delimiter}${env.PYTHONPATH}` : pythonPath,
    };
    addInvocationPlan(plans, seen, "python", ["-m", "specify_cli", "hook", ...hookArgs], pythonEnv);
    if (process.platform === "win32") {
      addInvocationPlan(plans, seen, "py", ["-m", "specify_cli", "hook", ...hookArgs], pythonEnv);
    } else {
      addInvocationPlan(plans, seen, "python3", ["-m", "specify_cli", "hook", ...hookArgs], pythonEnv);
    }
  }

  return plans.map((plan) => ({
    ...plan,
    env: {
      ...plan.env,
      OMX_NATIVE_QUALITY_HOOK_CWD: cwd,
    },
  }));
}

export function sharedHookBudgetForEvent(eventName: CodexHookEventName): number {
  switch (eventName) {
    case "PreToolUse":
      return 750;
    case "Stop":
      return 5000;
    case "SessionStart":
    case "UserPromptSubmit":
    case "PostToolUse":
      return 1500;
  }
}

export function redactedInvocationPreview(argv: string[]): string {
  const redacted: string[] = [];
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index] ?? "";
    const equalsIndex = token.indexOf("=");
    const flagName = equalsIndex >= 0 ? token.slice(0, equalsIndex) : token;
    if (SENSITIVE_FREE_TEXT_FLAGS.has(flagName) && equalsIndex >= 0) {
      redacted.push(`${flagName}=[REDACTED_PROMPT]`);
      continue;
    }
    redacted.push(token);
    if (SENSITIVE_FREE_TEXT_FLAGS.has(token)) {
      index += 1;
      redacted.push("[REDACTED_PROMPT]");
    }
  }
  return redacted.join(" ");
}

function collectSensitiveValues(hookArgs: string[], stdinText?: string): string[] {
  const values: string[] = [];
  const addValue = (value: string | undefined) => {
    if (!value) return;
    const trimmedValue = value.trim();
    if (trimmedValue === "") return;
    values.push(value);
    values.push(trimmedValue);
  };

  for (let index = 0; index < hookArgs.length; index += 1) {
    const token = hookArgs[index] ?? "";
    const equalsIndex = token.indexOf("=");
    const flagName = equalsIndex >= 0 ? token.slice(0, equalsIndex) : token;
    if (SENSITIVE_FREE_TEXT_FLAGS.has(flagName) && equalsIndex >= 0) {
      addValue(token.slice(equalsIndex + 1));
      continue;
    }
    if (SENSITIVE_FREE_TEXT_FLAGS.has(token)) {
      index += 1;
      addValue(hookArgs[index]);
    }
  }

  addValue(stdinText);
  return [...new Set(values)];
}

function redactExactValues(value: string, sensitiveValues: string[]): string {
  let redacted = value;
  for (const sensitiveValue of sensitiveValues) {
    redacted = redacted.split(sensitiveValue).join("[REDACTED_PROMPT]");
  }
  return redacted;
}

function stdoutPreview(stdout: string, sensitiveValues: string[]): string {
  return redactExactValues(stdout.trim(), sensitiveValues).slice(0, 500);
}

function parseSharedPayload(stdout: string): SharedQualityHookPayload | null {
  const trimmed = stdout.trim();
  if (!trimmed) return null;
  try {
    const parsed = JSON.parse(trimmed) as SharedQualityHookPayload;
    if (
      parsed
      && typeof parsed === "object"
      && typeof parsed.event === "string"
      && typeof parsed.status === "string"
      && VALID_HOOK_STATUSES.has(parsed.status)
    ) {
      return parsed;
    }
  } catch {
    return null;
  }
  return null;
}

function isBlockedPayload(payload: SharedQualityHookPayload): boolean {
  return payload.status === "blocked" || payload.status === "repairable-block";
}

export class SharedHookClient {
  private readonly cwd: string;
  private readonly env: NodeJS.ProcessEnv;
  private readonly runner: HookProcessRunner;
  private readonly now: () => number;

  constructor(options: SharedHookClientOptions) {
    this.cwd = options.cwd;
    this.env = options.env ?? process.env;
    this.runner = options.runner ?? defaultRunner;
    this.now = options.now ?? (() => Date.now());
  }

  invoke(hookArgs: string[], options: SharedHookInvokeOptions): SharedHookClientResult {
    const started = this.now();
    const timeoutMs = options.timeoutMs ?? sharedHookBudgetForEvent(options.eventName);
    const deadline = started + timeoutMs;
    const attemptedPlans: string[] = [];
    const sensitiveValues = collectSensitiveValues(hookArgs, options.stdinText);
    let firstInvalidAttempt: { attemptedPlan: string; stdoutPreview: string } | null = null;
    const plans = buildSharedHookInvocationPlans(hookArgs, this.cwd, this.env);

    for (const plan of plans) {
      const preview = redactedInvocationPreview([plan.executable, ...plan.args]);
      attemptedPlans.push(preview);
      const remainingMs = Math.max(0, deadline - this.now());
      if (remainingMs <= 0) {
        return {
          status: "timeout",
          timeoutMs,
          attemptedPlan: preview,
          durationMs: Math.max(0, this.now() - started),
        };
      }
      const result = this.runner(plan, {
        cwd: this.cwd,
        timeoutMs: remainingMs,
        stdinText: options.stdinText,
      });
      const durationMs = Math.max(0, this.now() - started);
      if (result.timedOut) {
        return { status: "timeout", timeoutMs, attemptedPlan: preview, durationMs };
      }
      if (
        result.status !== SHARED_HOOK_SUCCESS_EXIT_CODE
        && result.status !== SHARED_HOOK_BLOCKED_EXIT_CODE
      ) {
        continue;
      }
      const payload = parseSharedPayload(result.stdout);
      if (!payload) {
        firstInvalidAttempt ??= {
          attemptedPlan: preview,
          stdoutPreview: stdoutPreview(result.stdout, sensitiveValues),
        };
        continue;
      }
      if (
        result.status === SHARED_HOOK_BLOCKED_EXIT_CODE
        && !isBlockedPayload(payload)
      ) {
        firstInvalidAttempt ??= {
          attemptedPlan: preview,
          stdoutPreview: stdoutPreview(result.stdout, sensitiveValues),
        };
        continue;
      }
      if (isBlockedPayload(payload)) {
        return { status: "blocked", payload, durationMs };
      }
      return { status: "ok", payload, durationMs };
    }

    if (firstInvalidAttempt) {
      return {
        status: "invalid-output",
        stdoutPreview: firstInvalidAttempt.stdoutPreview,
        attemptedPlan: firstInvalidAttempt.attemptedPlan,
        durationMs: Math.max(0, this.now() - started),
      };
    }

    return {
      status: "unavailable",
      reason: "no shared hook invocation plan produced valid JSON",
      attemptedPlans,
      durationMs: Math.max(0, this.now() - started),
    };
  }
}
