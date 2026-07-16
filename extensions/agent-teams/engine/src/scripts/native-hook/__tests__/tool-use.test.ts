import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { buildNativeHookContext } from "../context.js";
import { outcomeToCodexJson } from "../outcome.js";
import { handlePostToolUse, handlePreToolUse } from "../tool-use.js";

describe("native hook tool-use wrappers", () => {
  it("returns null for non-Bash PreToolUse", () => {
    const context = buildNativeHookContext({
      hook_event_name: "PreToolUse",
      cwd: "/repo",
      tool_name: "Read",
      tool_input: { file_path: "package.json" },
    });

    assert.equal(handlePreToolUse(context), null);
  });

  it("blocks Bash hard failures after PostToolUse", () => {
    const context = buildNativeHookContext({
      hook_event_name: "PostToolUse",
      cwd: "/repo",
      tool_name: "Bash",
      tool_input: { command: "missing-tool" },
      tool_response: { exit_code: 127, stderr: "missing-tool: command not found" },
    });

    const output = outcomeToCodexJson(handlePostToolUse(context));

    assert.equal(output?.decision, "block");
    assert.equal(output?.hookSpecificOutput?.hookEventName, "PostToolUse");
    assert.match(String(output?.reason), /command\/setup failure/);
  });

  it("preserves destructive PreToolUse advisory systemMessage through Codex JSON rendering", () => {
    const context = buildNativeHookContext({
      hook_event_name: "PreToolUse",
      cwd: "/repo",
      tool_name: "Bash",
      tool_input: { command: "rm -rf dist" },
    });

    const output = outcomeToCodexJson(handlePreToolUse(context));

    assert.deepEqual(output?.hookSpecificOutput, {
      hookEventName: "PreToolUse",
    });
    assert.equal(output?.decision, undefined);
    assert.match(String(output?.systemMessage), /Destructive Bash command detected/);
  });

  it("preserves git commit block systemMessage through Codex JSON rendering", () => {
    const context = buildNativeHookContext({
      hook_event_name: "PreToolUse",
      cwd: "/repo",
      tool_name: "Bash",
      tool_input: { command: 'git commit -m "Update files"' },
    });

    const output = outcomeToCodexJson(handlePreToolUse(context));

    assert.equal(output?.decision, "block");
    assert.equal(output?.hookSpecificOutput?.hookEventName, "PreToolUse");
    assert.match(String(output?.systemMessage), /Lore protocol/);
  });

  it("preserves omx question block systemMessage through Codex JSON rendering", () => {
    const context = buildNativeHookContext({
      hook_event_name: "PreToolUse",
      cwd: "/repo",
      tool_name: "Bash",
      tool_input: { command: "omx question ask" },
    });

    const output = outcomeToCodexJson(handlePreToolUse(context));

    assert.equal(output?.decision, "block");
    assert.equal(output?.hookSpecificOutput?.hookEventName, "PreToolUse");
    assert.match(String(output?.systemMessage), /OMX_QUESTION_RETURN_PANE=\$TMUX_PANE/);
  });
});
