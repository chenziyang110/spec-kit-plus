import {
  buildNativePostToolUseOutput,
  buildNativePreToolUseOutput,
} from "../codex-native-pre-post.js";
import type { NativeHookContext } from "./context.js";
import {
  outputToOutcome,
  type NativeHookOutcome,
} from "./outcome.js";

function legacyPayloadFromContext(context: NativeHookContext): Record<string, unknown> {
  return {
    cwd: context.cwd,
    hook_event_name: context.eventName,
    tool_name: context.toolName ?? "",
    tool_use_id: context.toolUseId ?? "",
    tool_input: context.toolInput,
    tool_response: context.toolResponse,
  };
}

export function handlePreToolUse(context: NativeHookContext | null): NativeHookOutcome | null {
  if (!context || context.eventName !== "PreToolUse" || context.toolName !== "Bash") return null;
  return outputToOutcome(
    buildNativePreToolUseOutput(legacyPayloadFromContext(context)),
    "PreToolUse",
  );
}

export function handlePostToolUse(context: NativeHookContext | null): NativeHookOutcome | null {
  if (!context || context.eventName !== "PostToolUse") return null;
  return outputToOutcome(
    buildNativePostToolUseOutput(legacyPayloadFromContext(context)),
    "PostToolUse",
  );
}
