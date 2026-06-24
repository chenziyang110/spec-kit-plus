import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { specifyRuntimeStateDir } from "../../../utils/paths.js";
import {
  buildNativeHookContext,
  readNativeHookEventName,
  readPromptText,
} from "../context.js";

describe("native hook context", () => {
  it("normalizes supported event name fields and rejects invalid events", () => {
    assert.equal(readNativeHookEventName({ hook_event_name: " PreToolUse " }), "PreToolUse");
    assert.equal(readNativeHookEventName({ hookEventName: "PostToolUse" }), "PostToolUse");
    assert.equal(readNativeHookEventName({ event: "UserPromptSubmit" }), "UserPromptSubmit");
    assert.equal(readNativeHookEventName({ name: "Stop" }), "Stop");
    assert.equal(readNativeHookEventName({ hook_event_name: "SessionStart" }), "SessionStart");
    assert.equal(readNativeHookEventName({ hook_event_name: "pre_tool_use" }), null);
    assert.equal(readNativeHookEventName({ hook_event_name: "Unknown" }), null);
    assert.equal(readNativeHookEventName({ hook_event_name: 42 }), null);
  });

  it("normalizes session, thread, and turn fields from snake_case and camelCase payloads", () => {
    const snake = buildNativeHookContext({
      hook_event_name: "SessionStart",
      cwd: "/repo",
      session_id: " session-snake ",
      thread_id: " thread-snake ",
      turn_id: " turn-snake ",
    });
    const camel = buildNativeHookContext({
      hookEventName: "SessionStart",
      cwd: "/repo",
      sessionId: " session-camel ",
      threadId: " thread-camel ",
      turnId: " turn-camel ",
    });

    assert.equal(snake?.nativeSessionId, "session-snake");
    assert.equal(snake?.canonicalSessionId, "");
    assert.equal(snake?.threadId, "thread-snake");
    assert.equal(snake?.turnId, "turn-snake");
    assert.equal(snake?.activeWorkflow, null);
    assert.equal(camel?.nativeSessionId, "session-camel");
    assert.equal(camel?.canonicalSessionId, "");
    assert.equal(camel?.threadId, "thread-camel");
    assert.equal(camel?.turnId, "turn-camel");
    assert.equal(camel?.activeWorkflow, null);
  });

  it("reads prompt text from prompt, user_prompt, and userPrompt fields without trimming user text", () => {
    assert.equal(readPromptText({ prompt: "  plain prompt\n" }), "  plain prompt\n");
    assert.equal(readPromptText({ user_prompt: "snake prompt" }), "snake prompt");
    assert.equal(readPromptText({ userPrompt: "camel prompt" }), "camel prompt");
    assert.equal(readPromptText({ prompt: 42 }), "");
  });

  it("normalizes tool fields from snake_case and camelCase payloads", () => {
    const toolInput = { command: "npm test" };
    const toolResponse = { status: "ok" };
    const snake = buildNativeHookContext({
      hook_event_name: "PreToolUse",
      cwd: "/repo",
      tool_name: " shell ",
      tool_use_id: " tool-snake ",
      tool_input: toolInput,
      tool_response: toolResponse,
    });
    const camel = buildNativeHookContext({
      hookEventName: "PostToolUse",
      cwd: "/repo",
      toolName: " apply_patch ",
      toolUseId: " tool-camel ",
      toolInput,
      toolResponse,
    });

    assert.equal(snake?.toolName, "shell");
    assert.equal(snake?.toolUseId, "tool-snake");
    assert.equal(snake?.toolInput, toolInput);
    assert.equal(snake?.toolResponse, toolResponse);
    assert.equal(camel?.toolName, "apply_patch");
    assert.equal(camel?.toolUseId, "tool-camel");
    assert.equal(camel?.toolInput, toolInput);
    assert.equal(camel?.toolResponse, toolResponse);
  });

  it("uses injected default cwd and derives the runtime state directory", () => {
    const payload = { hook_event_name: "Stop" };
    const first = buildNativeHookContext(payload, { defaultCwd: "/repo-one" });
    const second = buildNativeHookContext(payload, { defaultCwd: "/repo-two" });

    assert.equal(first?.cwd, "/repo-one");
    assert.equal(first?.runtimeStateDir, specifyRuntimeStateDir("/repo-one"));
    assert.equal(second?.cwd, "/repo-two");
    assert.equal(second?.runtimeStateDir, specifyRuntimeStateDir("/repo-two"));
  });

  it("normalizes cwd before deriving the runtime state directory", () => {
    const defaultCwd = "/default-repo";
    const missing = buildNativeHookContext({ hook_event_name: "Stop" }, { defaultCwd });
    const empty = buildNativeHookContext({ hook_event_name: "Stop", cwd: "" }, { defaultCwd });
    const whitespace = buildNativeHookContext({ hook_event_name: "Stop", cwd: "   \t" }, { defaultCwd });
    const trimmed = buildNativeHookContext({
      hook_event_name: "Stop",
      cwd: " /repo ",
    }, { defaultCwd });

    assert.equal(missing?.cwd, defaultCwd);
    assert.equal(empty?.cwd, defaultCwd);
    assert.equal(whitespace?.cwd, defaultCwd);
    assert.equal(trimmed?.cwd, "/repo");
    assert.equal(missing?.runtimeStateDir, specifyRuntimeStateDir(defaultCwd));
    assert.equal(empty?.runtimeStateDir, specifyRuntimeStateDir(defaultCwd));
    assert.equal(whitespace?.runtimeStateDir, specifyRuntimeStateDir(defaultCwd));
    assert.equal(trimmed?.runtimeStateDir, specifyRuntimeStateDir("/repo"));
  });

  it("derives runtimeStateDir from explicit cwd", () => {
    const context = buildNativeHookContext({
      hook_event_name: "Stop",
      cwd: "/repo",
    });

    assert.equal(context?.runtimeStateDir, specifyRuntimeStateDir("/repo"));
  });

  it("accepts only plain object toolInput values", () => {
    const objectInput = { path: "src/index.ts" };

    assert.deepEqual(buildNativeHookContext({
      hook_event_name: "PreToolUse",
      cwd: "/repo",
      toolInput: objectInput,
    })?.toolInput, objectInput);
    assert.deepEqual(buildNativeHookContext({
      hook_event_name: "PreToolUse",
      cwd: "/repo",
      tool_input: null,
      toolInput: { command: "git commit" },
    })?.toolInput, { command: "git commit" });
    assert.deepEqual(buildNativeHookContext({
      hook_event_name: "PreToolUse",
      cwd: "/repo",
      toolInput: [],
    })?.toolInput, {});
    assert.deepEqual(buildNativeHookContext({
      hook_event_name: "PreToolUse",
      cwd: "/repo",
      tool_input: null,
      toolInput: [],
    })?.toolInput, {});
    assert.deepEqual(buildNativeHookContext({
      hook_event_name: "PreToolUse",
      cwd: "/repo",
      toolInput: null,
    })?.toolInput, {});
    assert.deepEqual(buildNativeHookContext({
      hook_event_name: "PreToolUse",
      cwd: "/repo",
      toolInput: "command",
    })?.toolInput, {});
  });

  it("returns null for invalid event payloads", () => {
    assert.equal(buildNativeHookContext({ hook_event_name: "Invalid" }), null);
  });

  it("does not expose raw payload as part of the stable snapshot", () => {
    const payload = { hook_event_name: "UserPromptSubmit", prompt: "hello" };
    const context = buildNativeHookContext(payload);

    assert.ok(context);
    assert.equal("rawPayload" in (context as unknown as Record<string, unknown>), false);
  });
});
