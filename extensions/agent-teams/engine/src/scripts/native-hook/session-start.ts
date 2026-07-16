import type { SharedQualityHookPayload } from "../../hooks/specify-quality-adapter.js";
import type { CodexHookPayload } from "./context.js";

export interface SessionStartHandlerInput {
  cwd: string;
  payload: CodexHookPayload;
  canonicalSessionId: string;
  nativeSessionId: string;
  buildSessionStartContext: (cwd: string, sessionId: string) => Promise<string | null>;
  buildSharedCompactionArgs: (
    cwd: string,
    payload: CodexHookPayload,
    mode: "read" | "build",
  ) => Promise<string[] | null>;
  invokeSharedQualityHook: (
    args: string[],
    options: { cwd: string },
  ) => SharedQualityHookPayload | null;
  appendSharedHookContext: (
    existing: string | null,
    payload: SharedQualityHookPayload | null,
  ) => string | null;
}

export async function handleSessionStart(
  input: SessionStartHandlerInput,
): Promise<Record<string, unknown> | null> {
  const additionalContextBase = await input.buildSessionStartContext(
    input.cwd,
    input.canonicalSessionId || input.nativeSessionId,
  );
  const sharedCompactionArgs = await input.buildSharedCompactionArgs(input.cwd, input.payload, "build");
  const sharedCompactionPayload = sharedCompactionArgs
    ? input.invokeSharedQualityHook(sharedCompactionArgs, { cwd: input.cwd })
    : null;
  const additionalContext = input.appendSharedHookContext(additionalContextBase, sharedCompactionPayload);
  if (!additionalContext) return null;
  return {
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext,
    },
  };
}
