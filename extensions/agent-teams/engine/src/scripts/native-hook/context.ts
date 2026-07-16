import { specifyRuntimeStateDir } from "../../utils/paths.js";
import type { CodexHookEventName } from "./outcome.js";

export type CodexHookPayload = Record<string, unknown>;

export interface NativeHookContext {
  cwd: string;
  eventName: CodexHookEventName;
  nativeSessionId: string | null;
  canonicalSessionId: string;
  threadId: string | null;
  turnId: string | null;
  promptText: string;
  toolName: string | null;
  toolUseId: string | null;
  toolInput: Record<string, unknown>;
  toolResponse: unknown;
  activeWorkflow: unknown | null;
  runtimeStateDir: string;
}

export interface BuildNativeHookContextOptions {
  defaultCwd?: string;
}

const CODEX_HOOK_EVENTS = new Set<CodexHookEventName>([
  "SessionStart",
  "PreToolUse",
  "PostToolUse",
  "UserPromptSubmit",
  "Stop",
]);

function readString(payload: CodexHookPayload, ...keys: string[]): string | null {
  for (const key of keys) {
    const value = payload[key];
    if (typeof value === "string") return value;
  }
  return null;
}

function readTrimmedString(payload: CodexHookPayload, ...keys: string[]): string | null {
  const value = readString(payload, ...keys)?.trim();
  return value ? value : null;
}

function readTrimmedCwd(payload: CodexHookPayload, defaultCwd: string): string {
  return readTrimmedString(payload, "cwd") ?? defaultCwd;
}

function readValue(payload: CodexHookPayload, ...keys: string[]): unknown {
  for (const key of keys) {
    if (Object.prototype.hasOwnProperty.call(payload, key)) return payload[key];
  }
  return undefined;
}

function readPlainObjectValue(payload: CodexHookPayload, ...keys: string[]): Record<string, unknown> {
  for (const key of keys) {
    if (!Object.prototype.hasOwnProperty.call(payload, key)) continue;
    const value = payload[key];
    if (isPlainObject(value)) return value;
  }
  return {};
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) return false;
  const prototype = Object.getPrototypeOf(value);
  return prototype === Object.prototype || prototype === null;
}

export function readNativeHookEventName(payload: CodexHookPayload): CodexHookEventName | null {
  const eventName = readTrimmedString(payload, "hook_event_name", "hookEventName", "event", "name");
  if (!eventName) return null;
  return CODEX_HOOK_EVENTS.has(eventName as CodexHookEventName)
    ? eventName as CodexHookEventName
    : null;
}

export function readPromptText(payload: CodexHookPayload): string {
  return readString(payload, "prompt", "user_prompt", "userPrompt") ?? "";
}

export function buildNativeHookContext(
  payload: CodexHookPayload,
  options: BuildNativeHookContextOptions = {},
): NativeHookContext | null {
  const eventName = readNativeHookEventName(payload);
  if (!eventName) return null;

  const cwd = readTrimmedCwd(payload, options.defaultCwd ?? process.cwd());

  return {
    cwd,
    eventName,
    nativeSessionId: readTrimmedString(payload, "session_id", "sessionId"),
    canonicalSessionId: "",
    threadId: readTrimmedString(payload, "thread_id", "threadId"),
    turnId: readTrimmedString(payload, "turn_id", "turnId"),
    promptText: readPromptText(payload),
    toolName: readTrimmedString(payload, "tool_name", "toolName"),
    toolUseId: readTrimmedString(payload, "tool_use_id", "toolUseId"),
    toolInput: readPlainObjectValue(payload, "tool_input", "toolInput"),
    toolResponse: readValue(payload, "tool_response", "toolResponse"),
    activeWorkflow: null,
    runtimeStateDir: specifyRuntimeStateDir(cwd),
  };
}
