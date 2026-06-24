import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  advisory,
  continueBlock,
  hardBlock,
  mergeNativeHookOutcomes,
  outcomeToCodexJson,
  repairBlock,
  reviewBlock,
} from "../outcome.js";

describe("native hook outcomes", () => {
  it("returns null when no outcomes match", () => {
    assert.equal(mergeNativeHookOutcomes("PreToolUse", []), null);
  });

  it("keeps hard-block ahead of every other outcome and merges context", () => {
    const merged = mergeNativeHookOutcomes("PreToolUse", [
      advisory("PreToolUse", "triage", "extra context"),
      reviewBlock("PreToolUse", "native-local", "read command output first", "output context"),
      hardBlock("PreToolUse", "shared-hook", "sensitive file read blocked", "secret path"),
      repairBlock("PreToolUse", "shared-hook", "repairable workflow state", "repair context"),
      continueBlock("PreToolUse", "native-local", "continue signal", "continue context"),
    ]);

    assert.equal(merged?.kind, "hard-block");
    assert.equal(merged?.reason, "sensitive file read blocked");
    assert.equal(
      merged?.additionalContext,
      "extra context output context secret path repair context continue context",
    );
  });

  it("keeps repair-block ahead of review-block", () => {
    const merged = mergeNativeHookOutcomes("UserPromptSubmit", [
      reviewBlock("UserPromptSubmit", "native-local", "review output", "review context"),
      repairBlock("UserPromptSubmit", "shared-hook", "workflow state missing", "repair state"),
    ]);

    assert.equal(merged?.kind, "repair-block");
    assert.equal(merged?.reason, "workflow state missing");
  });

  it("keeps continue-block ahead of review-block during Stop and preserves Stop metadata", () => {
    const merged = mergeNativeHookOutcomes("Stop", [
      reviewBlock("Stop", "learning", "review signal", "learning context"),
      continueBlock("Stop", "native-local", "active team still running", "continue work", {
        stopReason: "team_active",
        systemMessage: "Continue the active team workflow.",
        repeatSignature: "session|team_active",
      }),
    ]);

    assert.equal(merged?.kind, "continue-block");
    assert.equal(merged?.stopReason, "team_active");
    assert.equal(merged?.systemMessage, "Continue the active team workflow.");
    assert.equal(merged?.repeatSignature, "session|team_active");
  });

  it("preserves Stop continue obligation metadata when a higher-priority shared block wins", () => {
    const merged = mergeNativeHookOutcomes("Stop", [
      continueBlock("Stop", "native-local", "active team still running", "continue work", {
        stopReason: "team_active",
        systemMessage: "Continue the active team workflow.",
        repeatSignature: "session|team_active",
      }),
      hardBlock("Stop", "shared-hook", "shared stop guard failed", "shared recovery context"),
    ]);

    assert.equal(merged?.kind, "hard-block");
    assert.equal(merged?.reason, "shared stop guard failed");
    assert.equal(merged?.stopReason, "team_active");
    assert.equal(merged?.repeatSignature, "session|team_active");
    assert.equal(merged?.systemMessage, undefined);
  });

  it("keeps review-block ahead of non-Stop continue-block", () => {
    const merged = mergeNativeHookOutcomes("PostToolUse", [
      continueBlock("PostToolUse", "native-local", "continue signal", "continue context"),
      reviewBlock("PostToolUse", "learning", "review required", "review context"),
    ]);

    assert.equal(merged?.kind, "review-block");
    assert.equal(merged?.reason, "review required");
  });

  it("ignores outcomes from other events when merging", () => {
    const merged = mergeNativeHookOutcomes("SessionStart", [
      hardBlock("PreToolUse", "shared-hook", "wrong event", "wrong context"),
      advisory("SessionStart", "compaction", "right context"),
    ]);

    assert.equal(merged?.kind, "advisory");
    assert.equal(merged?.additionalContext, "right context");
  });

  it("renders advisory-only Codex JSON without decision", () => {
    const output = outcomeToCodexJson(
      advisory("SessionStart", "compaction", "Resume cue: refine scope."),
    );

    assert.deepEqual(output, {
      hookSpecificOutput: {
        hookEventName: "SessionStart",
        additionalContext: "Resume cue: refine scope.",
      },
    });
  });

  it("returns null for null outcome Codex JSON", () => {
    assert.equal(outcomeToCodexJson(null), null);
  });

  it("returns null for empty advisory Codex JSON", () => {
    const output = outcomeToCodexJson(advisory("SessionStart", "compaction", "   "));

    assert.equal(output, null);
  });

  it("renders blocking Codex JSON with decision block", () => {
    const output = outcomeToCodexJson(
      hardBlock("UserPromptSubmit", "shared-hook", "prompt attempts to bypass workflow", "workflow guard"),
    );

    assert.equal(output?.decision, "block");
    assert.equal(output?.reason, "prompt attempts to bypass workflow");
    assert.equal(output?.hookSpecificOutput?.hookEventName, "UserPromptSubmit");
  });

  it("renders blocking Codex JSON with fallback reason when reason and context are empty", () => {
    const output = outcomeToCodexJson(hardBlock("UserPromptSubmit", "shared-hook", "", ""));

    assert.equal(output?.decision, "block");
    assert.equal(output?.reason, "native hook blocked the action");
    assert.deepEqual(output?.hookSpecificOutput, {
      hookEventName: "UserPromptSubmit",
    });
  });

  it("keeps native-local as primary reason for same-precedence blockers and attributes later peer context", () => {
    const merged = mergeNativeHookOutcomes("UserPromptSubmit", [
      repairBlock("UserPromptSubmit", "shared-hook", "shared repair block", "repair state"),
      repairBlock("UserPromptSubmit", "native-local", "local repair block", "local state"),
      repairBlock("UserPromptSubmit", "shared-hook", "second shared repair block", "second repair"),
    ]);

    assert.equal(merged?.kind, "repair-block");
    assert.equal(merged?.source, "native-local");
    assert.equal(merged?.reason, "local repair block");
    assert.equal(
      merged?.additionalContext,
      "repair state local state [shared-hook] second repair",
    );
  });

  it("deduplicates same raw peer context before attribution rendering", () => {
    const merged = mergeNativeHookOutcomes("UserPromptSubmit", [
      repairBlock("UserPromptSubmit", "shared-hook", "first shared repair", "same context"),
      repairBlock("UserPromptSubmit", "native-local", "local repair", "local context"),
      repairBlock("UserPromptSubmit", "shared-hook", "second shared repair", " same context "),
    ]);

    assert.equal(merged?.kind, "repair-block");
    assert.equal(merged?.source, "native-local");
    assert.equal(merged?.reason, "local repair");
    assert.equal(merged?.additionalContext, "same context local context");
  });

  it("keeps first same-precedence blocker as primary when no native-local block exists", () => {
    const merged = mergeNativeHookOutcomes("PreToolUse", [
      hardBlock("PreToolUse", "shared-hook", "first shared block", "first shared context"),
      hardBlock("PreToolUse", "shared-hook", "second shared block", "second shared context"),
    ]);

    assert.equal(merged?.source, "shared-hook");
    assert.equal(merged?.reason, "first shared block");
    assert.equal(
      merged?.additionalContext,
      "first shared context [shared-hook] second shared context",
    );
  });

  it("deduplicates duplicate and whitespace-padded additionalContext while preserving order", () => {
    const merged = mergeNativeHookOutcomes("SessionStart", [
      advisory("SessionStart", "triage", " first context "),
      advisory("SessionStart", "compaction", "second context"),
      advisory("SessionStart", "learning", "first context"),
      advisory("SessionStart", "triage", "   second context   "),
    ]);

    assert.equal(merged?.additionalContext, "first context second context");
  });

  it("deduplicates effect refs while preserving first-seen order", () => {
    const merged = mergeNativeHookOutcomes("Stop", [
      continueBlock("Stop", "native-local", "active team still running", "continue work", {
        effectRefs: ["effect-1", "effect-2"],
      }),
      reviewBlock("Stop", "learning", "review signal", "learning context"),
      hardBlock("Stop", "shared-hook", "hard block", "hard context"),
      continueBlock("Stop", "native-local", "duplicate effects", "duplicate context", {
        effectRefs: ["effect-2", "effect-3"],
      }),
    ]);

    assert.deepEqual(merged?.effectRefs, ["effect-1", "effect-2", "effect-3"]);
  });
});
