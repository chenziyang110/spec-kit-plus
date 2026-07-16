import { SharedHookClient, type SharedQualityHookPayload } from "./shared-hook-client.js";

export type { SharedQualityHookPayload } from "./shared-hook-client.js";

export function invokeSharedQualityHook(
  hookArgs: string[],
  options: {
    cwd: string;
    env?: NodeJS.ProcessEnv;
  },
): SharedQualityHookPayload | null {
  const client = new SharedHookClient({
    cwd: options.cwd,
    env: options.env ?? process.env,
  });
  const result = client.invoke(hookArgs, {
    eventName: "UserPromptSubmit",
    timeoutMs: Number.MAX_SAFE_INTEGER,
  });
  return result.status === "ok" || result.status === "blocked" ? result.payload : null;
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
    if (nextAction && !isEmptyResumeCue(nextAction)) {
      lines.push(`Resume cue: ${nextAction}.`);
    }
  }
  if (recoverySummary) {
    lines.push(...recoverySummaryLines(recoverySummary));
  }
  if (lines.length === 0) return existing;
  return dedupeOrdered([existing ?? "", ...lines]).filter(Boolean).join(" ");
}

function isEmptyResumeCue(value: string): boolean {
  const normalized = value.trim().toLowerCase().replace(/\.$/, "");
  return (
    normalized === ""
    || normalized === "none"
    || normalized === "n/a"
    || normalized === "no-op"
    || normalized === "noop"
  );
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
