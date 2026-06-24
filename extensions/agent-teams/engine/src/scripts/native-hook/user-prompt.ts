import type { SharedQualityHookPayload } from "../../hooks/specify-quality-adapter.js";
import type { SkillActiveState } from "../../hooks/keyword-detector.js";
import type { CodexHookPayload } from "./context.js";

export interface UserPromptHandlerInput {
  cwd: string;
  payload: CodexHookPayload;
  hookEventName: "UserPromptSubmit";
  prompt: string;
  skillState: SkillActiveState | null;
  triageAdditionalContext: string | null;
  sharedPromptGuardOutput: Record<string, unknown> | null;
  sharedPromptGuardPayload: SharedQualityHookPayload | null;
  sharedWorkflowPolicyPayload: SharedQualityHookPayload | null;
  buildAdditionalContextMessage: (
    prompt: string,
    skillState: SkillActiveState | null | undefined,
    cwd: string,
    payload?: CodexHookPayload,
  ) => string | null;
  appendSharedHookContext: (
    existing: string | null,
    payload: SharedQualityHookPayload | null,
  ) => string | null;
  readHookSpecificAdditionalContext: (outputJson: Record<string, unknown> | null) => string;
}

export function handleUserPromptSubmit(
  input: UserPromptHandlerInput,
): Record<string, unknown> | null {
  const additionalContextBase =
    input.buildAdditionalContextMessage(input.prompt, input.skillState, input.cwd, input.payload)
    ?? input.triageAdditionalContext;
  const additionalContext = input.appendSharedHookContext(
    input.appendSharedHookContext(additionalContextBase, input.sharedPromptGuardPayload),
    input.sharedWorkflowPolicyPayload,
  );

  if (input.sharedPromptGuardOutput) {
    if (!additionalContext) return input.sharedPromptGuardOutput;
    const currentAdditionalContext = input.readHookSpecificAdditionalContext(input.sharedPromptGuardOutput);
    return {
      ...input.sharedPromptGuardOutput,
      hookSpecificOutput: {
        ...(input.sharedPromptGuardOutput.hookSpecificOutput as Record<string, unknown> | undefined ?? {}),
        hookEventName: input.hookEventName,
        additionalContext: [currentAdditionalContext, additionalContext].filter(Boolean).join(" "),
      },
    };
  }

  if (!additionalContext) return null;
  return {
    hookSpecificOutput: {
      hookEventName: input.hookEventName,
      additionalContext,
    },
  };
}
