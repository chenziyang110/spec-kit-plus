import type { SharedQualityHookPayload } from "../../hooks/specify-quality-adapter.js";
import type { CodexHookPayload } from "./context.js";

export interface StopHandlerInput {
  cwd: string;
  payload: CodexHookPayload;
  baseOutput: Record<string, unknown> | null;
  buildSharedStopMonitorArgs: (payload: CodexHookPayload) => string[] | null;
  invokeSharedQualityHook: (
    args: string[],
    options: { cwd: string },
  ) => SharedQualityHookPayload | null;
  mergeSharedStopMonitorOutput: (
    currentOutput: Record<string, unknown> | null,
    sharedMonitorPayload: SharedQualityHookPayload | null,
  ) => Record<string, unknown> | null;
  buildSharedCompactionArgs: (
    cwd: string,
    payload: CodexHookPayload,
    mode: "read" | "build",
  ) => Promise<string[] | null>;
  appendSharedHookContext: (
    existing: string | null,
    payload: SharedQualityHookPayload | null,
  ) => string | null;
  readHookSpecificAdditionalContext: (outputJson: Record<string, unknown> | null) => string;
  withHookSpecificAdditionalContext: (
    outputJson: Record<string, unknown> | null,
    hookEventName: string,
    additionalContext: string,
  ) => Record<string, unknown>;
  buildSharedLearningSignalArgs: (
    cwd: string,
    payload: CodexHookPayload,
  ) => Promise<string[] | null>;
  mergeSharedLearningSignalOutput: (
    currentOutput: Record<string, unknown> | null,
    hookEventName: "PostToolUse" | "Stop",
    sharedLearningPayload: SharedQualityHookPayload | null,
  ) => Record<string, unknown> | null;
}

export async function mergeStopSharedOutputs(
  input: StopHandlerInput,
): Promise<Record<string, unknown> | null> {
  let outputJson = input.baseOutput;

  const sharedStopMonitorArgs = input.buildSharedStopMonitorArgs(input.payload);
  if (sharedStopMonitorArgs) {
    const sharedStopMonitorPayload = input.invokeSharedQualityHook(sharedStopMonitorArgs, { cwd: input.cwd });
    outputJson = input.mergeSharedStopMonitorOutput(outputJson, sharedStopMonitorPayload);
  }

  const sharedCompactionArgs = await input.buildSharedCompactionArgs(input.cwd, input.payload, "build");
  if (sharedCompactionArgs) {
    const sharedCompactionPayload = input.invokeSharedQualityHook(sharedCompactionArgs, { cwd: input.cwd });
    const mergedContext = input.appendSharedHookContext(
      input.readHookSpecificAdditionalContext(outputJson) || null,
      sharedCompactionPayload,
    );
    if (mergedContext) {
      outputJson = input.withHookSpecificAdditionalContext(outputJson, "Stop", mergedContext);
    }
  }

  const sharedLearningSignalArgs = await input.buildSharedLearningSignalArgs(input.cwd, input.payload);
  if (sharedLearningSignalArgs) {
    const sharedLearningSignalPayload = input.invokeSharedQualityHook(sharedLearningSignalArgs, { cwd: input.cwd });
    outputJson = input.mergeSharedLearningSignalOutput(outputJson, "Stop", sharedLearningSignalPayload);
  }

  return outputJson;
}
