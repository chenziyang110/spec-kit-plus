export type CodexHookEventName =
  | "SessionStart"
  | "PreToolUse"
  | "PostToolUse"
  | "UserPromptSubmit"
  | "Stop";

export type NativeHookOutcomeKind =
  | "advisory"
  | "hard-block"
  | "repair-block"
  | "review-block"
  | "continue-block";

export type NativeHookOutcomeSource =
  | "native-local"
  | "shared-hook"
  | "triage"
  | "compaction"
  | "learning";

export interface NativeHookOutcome {
  kind: NativeHookOutcomeKind;
  eventName: CodexHookEventName;
  source: NativeHookOutcomeSource;
  reason?: string;
  additionalContext?: string;
  stopReason?: string;
  systemMessage?: string;
  repeatSignature?: string;
  effectRefs?: string[];
}

export type CodexHookOutput = Record<string, unknown> & {
  decision?: string;
  reason?: string;
  stopReason?: string;
  systemMessage?: string;
  hookSpecificOutput?: {
    hookEventName?: string;
    additionalContext?: string;
  };
};

interface ContinueMetadata {
  stopReason?: string;
  systemMessage?: string;
  repeatSignature?: string;
  effectRefs?: string[];
}

export function advisory(
  eventName: CodexHookEventName,
  source: NativeHookOutcomeSource,
  additionalContext: string,
): NativeHookOutcome {
  return { kind: "advisory", eventName, source, additionalContext };
}

export function hardBlock(
  eventName: CodexHookEventName,
  source: NativeHookOutcomeSource,
  reason: string,
  additionalContext = reason,
): NativeHookOutcome {
  return { kind: "hard-block", eventName, source, reason, additionalContext };
}

export function repairBlock(
  eventName: CodexHookEventName,
  source: NativeHookOutcomeSource,
  reason: string,
  additionalContext = reason,
): NativeHookOutcome {
  return { kind: "repair-block", eventName, source, reason, additionalContext };
}

export function reviewBlock(
  eventName: CodexHookEventName,
  source: NativeHookOutcomeSource,
  reason: string,
  additionalContext = reason,
): NativeHookOutcome {
  return { kind: "review-block", eventName, source, reason, additionalContext };
}

export function continueBlock(
  eventName: CodexHookEventName,
  source: NativeHookOutcomeSource,
  reason: string,
  additionalContext = reason,
  metadata: ContinueMetadata = {},
): NativeHookOutcome {
  return {
    kind: "continue-block",
    eventName,
    source,
    reason,
    additionalContext,
    stopReason: metadata.stopReason,
    systemMessage: metadata.systemMessage,
    repeatSignature: metadata.repeatSignature,
    effectRefs: metadata.effectRefs,
  };
}

function precedence(eventName: CodexHookEventName, kind: NativeHookOutcomeKind): number {
  if (kind === "hard-block") return 50;
  if (kind === "repair-block") return 40;
  if (eventName === "Stop" && kind === "continue-block") return 35;
  if (kind === "review-block") return 30;
  if (kind === "continue-block") return 25;
  return 10;
}

interface ContextMergeItem {
  raw: string;
  rendered: string;
}

function dedupeContexts(values: Array<ContextMergeItem | undefined>): string {
  const seen = new Set<string>();
  const ordered: string[] = [];
  for (const value of values) {
    const raw = String(value?.raw ?? "").trim();
    const rendered = String(value?.rendered ?? "").trim();
    if (!raw || !rendered || seen.has(raw)) continue;
    seen.add(raw);
    ordered.push(rendered);
  }
  return ordered.join(" ");
}

function dedupeEffectRefs(outcomes: NativeHookOutcome[]): string[] {
  return [...new Set(outcomes.flatMap((outcome) => outcome.effectRefs ?? []))];
}

function isBlocking(kind: NativeHookOutcomeKind): boolean {
  return kind !== "advisory";
}

function contextForOutcome(
  outcome: NativeHookOutcome,
  shouldAttribute: boolean,
): ContextMergeItem | undefined {
  const context = String(outcome.additionalContext || outcome.reason || "").trim();
  if (!context) return undefined;
  return {
    raw: context,
    rendered: shouldAttribute ? `[${outcome.source}] ${context}` : context,
  };
}

export function mergeNativeHookOutcomes(
  eventName: CodexHookEventName,
  outcomes: NativeHookOutcome[],
): NativeHookOutcome | null {
  const present = outcomes.filter((outcome) => outcome.eventName === eventName);
  if (present.length === 0) return null;

  const maxPrecedence = Math.max(
    ...present.map((outcome) => precedence(eventName, outcome.kind)),
  );
  const primaryCandidates = present.filter(
    (outcome) => precedence(eventName, outcome.kind) === maxPrecedence,
  );
  const primary =
    primaryCandidates.find((outcome) => outcome.source === "native-local")
    ?? primaryCandidates[0];
  const primaryIndex = present.indexOf(primary);
  const additionalContext = dedupeContexts(
    present.map((outcome, index) => contextForOutcome(
      outcome,
      outcome !== primary
        && index > primaryIndex
        && isBlocking(outcome.kind)
        && precedence(eventName, outcome.kind) === maxPrecedence,
    )),
  );
  const firstStopContinue = eventName === "Stop"
    ? present.find((outcome) => outcome.kind === "continue-block")
    : undefined;

  return {
    ...primary,
    additionalContext,
    stopReason: primary.stopReason ?? firstStopContinue?.stopReason,
    repeatSignature: primary.repeatSignature ?? firstStopContinue?.repeatSignature,
    effectRefs: dedupeEffectRefs(present),
  };
}

export function outcomeToCodexJson(outcome: NativeHookOutcome | null): CodexHookOutput | null {
  if (!outcome) return null;
  const additionalContext = String(outcome.additionalContext ?? "").trim();
  if (outcome.kind === "advisory") {
    if (!additionalContext && !outcome.systemMessage) return null;
    return {
      ...(outcome.systemMessage ? { systemMessage: outcome.systemMessage } : {}),
      hookSpecificOutput: {
        hookEventName: outcome.eventName,
        ...(additionalContext ? { additionalContext } : {}),
      },
    };
  }

  return {
    decision: "block",
    reason: outcome.reason || additionalContext || "native hook blocked the action",
    ...(outcome.stopReason ? { stopReason: outcome.stopReason } : {}),
    ...(outcome.systemMessage ? { systemMessage: outcome.systemMessage } : {}),
    hookSpecificOutput: {
      hookEventName: outcome.eventName,
      ...(additionalContext ? { additionalContext } : {}),
    },
  };
}

function isCodexHookEventName(value: string): value is CodexHookEventName {
  return value === "SessionStart"
    || value === "PreToolUse"
    || value === "PostToolUse"
    || value === "UserPromptSubmit"
    || value === "Stop";
}

function readHookSpecificOutput(output: CodexHookOutput): Record<string, unknown> | null {
  const value = output.hookSpecificOutput;
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function readString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function outputToOutcome(
  output: CodexHookOutput | null,
  fallbackEventName: CodexHookEventName,
): NativeHookOutcome | null {
  if (!output) return null;

  const hookSpecificOutput = readHookSpecificOutput(output);
  const rawEventName = readString(hookSpecificOutput?.hookEventName).trim();
  const eventName = isCodexHookEventName(rawEventName) ? rawEventName : fallbackEventName;
  const additionalContext = readString(hookSpecificOutput?.additionalContext).trim();
  const reason = readString(output.reason).trim();
  const systemMessage = readString(output.systemMessage).trim();
  const stopReason = readString(output.stopReason).trim();

  if (output.decision === "block") {
    return {
      kind: "hard-block",
      eventName,
      source: "native-local",
      reason,
      additionalContext,
      ...(systemMessage ? { systemMessage } : {}),
      ...(stopReason ? { stopReason } : {}),
    };
  }

  if (!additionalContext && !systemMessage) return null;
  return {
    kind: "advisory",
    eventName,
    source: "native-local",
    additionalContext,
    ...(systemMessage ? { systemMessage } : {}),
  };
}
