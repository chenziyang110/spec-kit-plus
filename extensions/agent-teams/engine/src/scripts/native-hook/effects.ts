import type { CodexHookEventName } from "./outcome.js";

export type NativeHookEffectKind =
  | "shared-hook"
  | "state-read"
  | "state-write"
  | "hud-reconcile"
  | "plugin-dispatch"
  | "git-exclude-write"
  | "team-state-write"
  | "compaction-write"
  | "learning-signal"
  | "stop-signature-write";

export type NativeHookEffectStatus = "ok" | "warn" | "error" | "skipped";

export interface NativeHookEffectInput {
  kind: NativeHookEffectKind;
  eventName: CodexHookEventName;
  source: string;
  target?: string;
  status: NativeHookEffectStatus;
  durationMs: number;
  errorClass?: string;
}

export interface NativeHookEffect extends NativeHookEffectInput {
  id: string;
}

const SENSITIVE_FREE_TEXT_FLAGS: ReadonlySet<string> = new Set([
  "--prompt-text",
  "--free-text",
  "--message-text",
  "--command-text",
]);

function tokenizeTarget(target: string): string[] {
  const tokens: string[] = [];
  let current = "";
  let quote: "'" | "\"" | null = null;

  for (let index = 0; index < target.length; index += 1) {
    const character = target[index]!;
    if (quote) {
      current += character;
      if (character === quote) {
        quote = null;
      }
      continue;
    }
    if (character === "'" || character === "\"") {
      quote = character;
      current += character;
      continue;
    }
    if (/\s/u.test(character)) {
      if (current) {
        tokens.push(current);
        current = "";
      }
      continue;
    }
    current += character;
  }

  if (current) {
    tokens.push(current);
  }
  return tokens;
}

function flagName(token: string): string {
  const equalsIndex = token.indexOf("=");
  return equalsIndex >= 0 ? token.slice(0, equalsIndex) : token;
}

export function redactEffectTarget(target: string | undefined): string | undefined {
  if (!target) return undefined;

  const tokens = tokenizeTarget(target);
  const redacted: string[] = [];
  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index]!;
    const name = flagName(token);
    const equalsIndex = token.indexOf("=");
    if (SENSITIVE_FREE_TEXT_FLAGS.has(name) && equalsIndex >= 0) {
      redacted.push(`${name}=[REDACTED_PROMPT]`);
      break;
    }
    if (SENSITIVE_FREE_TEXT_FLAGS.has(token)) {
      redacted.push(token, "[REDACTED_PROMPT]");
      break;
    }
    redacted.push(token);
  }
  return redacted.join(" ");
}

export class NativeHookEffectRecorder {
  private readonly effects: NativeHookEffect[] = [];

  record(input: NativeHookEffectInput): NativeHookEffect {
    const effect: NativeHookEffect = {
      id: `effect-${this.effects.length + 1}`,
      kind: input.kind,
      eventName: input.eventName,
      source: input.source,
      target: redactEffectTarget(input.target),
      status: input.status,
      durationMs: input.durationMs,
      ...(input.errorClass ? { errorClass: input.errorClass } : {}),
    };
    this.effects.push(effect);
    return { ...effect };
  }

  all(): NativeHookEffect[] {
    return this.effects.map((effect) => ({ ...effect }));
  }
}
