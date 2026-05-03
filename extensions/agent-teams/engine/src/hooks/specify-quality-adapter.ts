import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve, join } from "node:path";
import { packageRoot } from "../utils/paths.js";

type HookStatus = "ok" | "warn" | "blocked" | "repaired" | "repairable-block";

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

interface HookInvocationPlan {
  executable: string;
  args: string[];
  env: NodeJS.ProcessEnv;
  shell?: boolean;
}

function repoRootFromPackage(): string {
  return resolve(packageRoot(), "..", "..", "..");
}

function hasRepoSourceCheckout(): boolean {
  return existsSync(join(repoRootFromPackage(), "src", "specify_cli", "__init__.py"));
}

function buildInvocationPlans(
  hookArgs: string[],
  cwd: string,
  env: NodeJS.ProcessEnv = process.env,
): HookInvocationPlan[] {
  const plans: HookInvocationPlan[] = [];
  const seen = new Set<string>();
  const add = (executable: string, args: string[], extraEnv: NodeJS.ProcessEnv = env, shell = false) => {
    const key = `${executable}\u0000${args.join("\u0000")}`;
    if (seen.has(key)) return;
    seen.add(key);
    plans.push({ executable, args, env: extraEnv, shell });
  };

  const explicit = String(env.SPECIFY_HOOK_EXECUTABLE ?? "").trim();
  if (explicit) {
    const needsShell = /\.cmd$/i.test(explicit) || /\.bat$/i.test(explicit);
    add(explicit, ["hook", ...hookArgs], env, needsShell);
  }

  add("specify", ["hook", ...hookArgs]);

  if (hasRepoSourceCheckout()) {
    const repoRoot = repoRootFromPackage();
    const pythonEnv = {
      ...env,
      PYTHONPATH: env.PYTHONPATH
        ? `${join(repoRoot, "src")}${process.platform === "win32" ? ";" : ":"}${env.PYTHONPATH}`
        : join(repoRoot, "src"),
    };
    add("python", ["-m", "specify_cli", "hook", ...hookArgs], pythonEnv);
    if (process.platform === "win32") {
      add("py", ["-m", "specify_cli", "hook", ...hookArgs], pythonEnv);
    } else {
      add("python3", ["-m", "specify_cli", "hook", ...hookArgs], pythonEnv);
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

export function invokeSharedQualityHook(
  hookArgs: string[],
  options: {
    cwd: string;
    env?: NodeJS.ProcessEnv;
  },
): SharedQualityHookPayload | null {
  const plans = buildInvocationPlans(hookArgs, options.cwd, options.env ?? process.env);
  for (const plan of plans) {
    const result = spawnSync(plan.executable, plan.args, {
        cwd: options.cwd,
        encoding: "utf-8",
        env: plan.env,
        shell: plan.shell === true,
      });
    if (result.error || result.status !== 0) {
      continue;
    }
    const stdout = String(result.stdout ?? "").trim();
    if (!stdout) continue;
    try {
      const parsed = JSON.parse(stdout) as SharedQualityHookPayload;
      if (parsed && typeof parsed === "object" && typeof parsed.event === "string" && typeof parsed.status === "string") {
        return parsed;
      }
    } catch {
      continue;
    }
  }
  return null;
}

export function sharedHookBlockOutput(
  hookEventName: string,
  payload: SharedQualityHookPayload,
): Record<string, unknown> | null {
  if (payload.status !== "blocked" && payload.status !== "repairable-block") return null;
  const reason = payload.errors?.[0] || payload.warnings?.[0] || "shared quality hook blocked the action";
  const contextParts = dedupeOrdered([reason, ...(payload.errors ?? []), ...(payload.warnings ?? [])]);
  return {
    decision: "block",
    reason,
    hookSpecificOutput: {
      hookEventName,
      additionalContext: contextParts.join(" "),
    },
  };
}

export function appendSharedHookContext(
  existing: string | null,
  payload: SharedQualityHookPayload | null,
): string | null {
  if (!payload) return existing;
  const lines: string[] = [];
  if (payload.warnings?.length) lines.push(...payload.warnings);
  if (payload.actions?.length) lines.push(...payload.actions);
  const checkpoint = payload.data?.checkpoint as Record<string, unknown> | undefined;
  if (checkpoint && typeof checkpoint === "object") {
    const stateKind = typeof checkpoint["state_kind"] === "string" ? String(checkpoint["state_kind"]) : "";
    const nextAction = typeof checkpoint["next_action"] === "string" ? String(checkpoint["next_action"]) : "";
    if (stateKind || nextAction) {
      lines.push(
        `Shared quality hook checkpoint prepared${stateKind ? ` from ${stateKind}` : ""}${nextAction ? `; next action: ${nextAction}` : ""}.`,
      );
    }
  }
  const artifact = payload.data?.artifact as Record<string, unknown> | undefined;
  const recoverySummary = sharedRecoverySummary(payload.data);
  if (artifact && typeof artifact === "object") {
    const phaseState = artifact["phase_state"] as Record<string, unknown> | undefined;
    const nextAction = phaseState && typeof phaseState["next_action"] === "string"
      ? String(phaseState["next_action"])
      : "";
    if (nextAction) {
      lines.push(`Resume cue: ${nextAction}.`);
    }
  }
  if (recoverySummary) {
    lines.push(...recoverySummaryLines(recoverySummary));
  }
  if (lines.length === 0) return existing;
  return dedupeOrdered([existing ?? "", ...lines]).filter(Boolean).join(" ");
}

function sharedRecoverySummary(data: Record<string, unknown> | undefined): Record<string, unknown> | null {
  const artifact = data?.["artifact"];
  if (artifact && typeof artifact === "object") {
    const recoverySummary = (artifact as Record<string, unknown>)["recovery_summary"];
    if (recoverySummary && typeof recoverySummary === "object") {
      return recoverySummary as Record<string, unknown>;
    }
  }
  const policy = data?.["policy"];
  if (policy && typeof policy === "object") {
    const recoverySummary = (policy as Record<string, unknown>)["recovery_summary"];
    if (recoverySummary && typeof recoverySummary === "object") {
      return recoverySummary as Record<string, unknown>;
    }
  }
  return null;
}

function recoverySummaryLines(recoverySummary: Record<string, unknown>): string[] {
  const lines: string[] = [];
  const recoveryTextFields: Array<[string, string]> = [
    ["phase_mode", "Phase"],
    ["next_action", "Next action"],
    ["next_command", "Next command"],
    ["route_reason", "Reason"],
  ];
  for (const [fieldName, label] of recoveryTextFields) {
    const value = recoverySummary[fieldName];
    if (typeof value === "string" && value.trim()) {
      lines.push(`${label}: ${value.trim()}.`);
    }
  }
  return lines;
}

function dedupeOrdered(values: string[]): string[] {
  const seen = new Set<string>();
  const ordered: string[] = [];
  for (const value of values) {
    const trimmed = value.trim();
    if (!trimmed || seen.has(trimmed)) continue;
    seen.add(trimmed);
    ordered.push(trimmed);
  }
  return ordered;
}
