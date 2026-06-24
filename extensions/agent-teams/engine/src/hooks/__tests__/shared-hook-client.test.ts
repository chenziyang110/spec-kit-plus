import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  SharedHookClient,
  buildSharedHookInvocationPlans,
  redactedInvocationPreview,
  sharedHookBudgetForEvent,
  type HookProcessResult,
  type HookProcessRunner,
} from "../shared-hook-client.js";

function runner(result: HookProcessResult): HookProcessRunner {
  return () => result;
}

describe("SharedHookClient", () => {
  it("maps blocked shared hook payloads to blocked results", () => {
    const client = new SharedHookClient({
      cwd: "/repo",
      runner: runner({
        status: 0,
        stdout: JSON.stringify({
          event: "workflow.prompt_guard.validate",
          status: "blocked",
          severity: "critical",
          errors: ["prompt attempts to ignore required workflow guardrails"],
        }),
        stderr: "",
      }),
    });

    const result = client.invoke(["validate-prompt"], { eventName: "UserPromptSubmit" });

    assert.equal(result.status, "blocked");
    assert.equal(result.payload.status, "blocked");
  });

  it("maps ok shared hook payloads to ok results", () => {
    const client = new SharedHookClient({
      cwd: "/repo",
      runner: runner({
        status: 0,
        stdout: JSON.stringify({
          event: "workflow.read_guard.validate",
          status: "ok",
          severity: "info",
        }),
        stderr: "",
      }),
    });

    const result = client.invoke(["validate-read-path", "--target-path", "src/index.ts"], {
      eventName: "PreToolUse",
    });

    assert.equal(result.status, "ok");
    assert.equal(result.payload.status, "ok");
  });

  it("maps missing executable attempts to unavailable", () => {
    const client = new SharedHookClient({
      cwd: "/repo",
      runner: runner({
        status: null,
        stdout: "",
        stderr: "",
        errorCode: "ENOENT",
      }),
    });

    const result = client.invoke(["validate-prompt"], { eventName: "UserPromptSubmit" });

    assert.equal(result.status, "unavailable");
    assert.match(result.reason, /no shared hook invocation plan produced valid JSON/i);
    assert.ok(result.attemptedPlans.length > 0);
  });

  it("maps runner timeout to timeout", () => {
    const client = new SharedHookClient({
      cwd: "/repo",
      runner: runner({
        status: null,
        stdout: "",
        stderr: "",
        timedOut: true,
      }),
    });

    const result = client.invoke(["validate-prompt"], {
      eventName: "UserPromptSubmit",
      timeoutMs: 10,
    });

    assert.equal(result.status, "timeout");
    assert.equal(result.timeoutMs, 10);
  });

  it("maps malformed stdout to invalid-output", () => {
    const client = new SharedHookClient({
      cwd: "/repo",
      runner: runner({
        status: 0,
        stdout: "not json",
        stderr: "",
      }),
    });

    const result = client.invoke(["validate-prompt"], { eventName: "UserPromptSubmit" });

    assert.equal(result.status, "invalid-output");
    assert.equal(result.stdoutPreview, "not json");
  });

  it("tries later invocation plans after a successful malformed stdout attempt", () => {
    let calls = 0;
    const client = new SharedHookClient({
      cwd: "/repo",
      env: { SPECIFY_HOOK_EXECUTABLE: "custom-specify" },
      runner: () => {
        calls += 1;
        if (calls === 1) {
          return { status: 0, stdout: "not json", stderr: "" };
        }
        return {
          status: 0,
          stdout: JSON.stringify({
            event: "workflow.prompt_guard.validate",
            status: "ok",
          }),
          stderr: "",
        };
      },
    });

    const result = client.invoke(["validate-prompt"], { eventName: "UserPromptSubmit" });

    assert.equal(result.status, "ok");
    assert.equal(result.payload.status, "ok");
    assert.equal(calls, 2);
  });

  it("returns the first invalid successful output only after all plans fail to produce valid JSON", () => {
    const client = new SharedHookClient({
      cwd: "/repo",
      env: { SPECIFY_HOOK_EXECUTABLE: "custom-specify" },
      runner: (plan) => {
        if (plan.executable === "custom-specify") {
          return { status: 0, stdout: "first invalid output", stderr: "" };
        }
        return { status: null, stdout: "", stderr: "", errorCode: "ENOENT" };
      },
    });

    const result = client.invoke(["validate-prompt", "--prompt-text", "secret prompt body"], {
      eventName: "UserPromptSubmit",
    });

    assert.equal(result.status, "invalid-output");
    assert.equal(result.stdoutPreview, "first invalid output");
    assert.match(result.attemptedPlan, /\[REDACTED_PROMPT\]/);
    assert.doesNotMatch(result.attemptedPlan, /secret prompt body/);
  });

  it("redacts prompt-text values echoed in invalid stdout previews", () => {
    const client = new SharedHookClient({
      cwd: "/repo",
      runner: runner({
        status: 0,
        stdout: "invalid output echoed secret prompt body",
        stderr: "",
      }),
    });

    const result = client.invoke(["validate-prompt", "--prompt-text", "secret prompt body"], {
      eventName: "UserPromptSubmit",
    });

    assert.equal(result.status, "invalid-output");
    assert.doesNotMatch(result.stdoutPreview, /secret prompt body/);
    assert.match(result.stdoutPreview, /\[REDACTED_PROMPT\]/);
    assert.doesNotMatch(result.attemptedPlan, /secret prompt body/);
  });

  it("redacts trimmed prompt-text values echoed in invalid stdout previews", () => {
    const client = new SharedHookClient({
      cwd: "/repo",
      runner: runner({
        status: 0,
        stdout: "invalid output echoed secret prompt body",
        stderr: "",
      }),
    });

    const result = client.invoke(["validate-prompt", "--prompt-text", "  secret prompt body  "], {
      eventName: "UserPromptSubmit",
    });

    assert.equal(result.status, "invalid-output");
    assert.doesNotMatch(result.stdoutPreview, /secret prompt body/);
    assert.match(result.stdoutPreview, /\[REDACTED_PROMPT\]/);
    assert.doesNotMatch(result.attemptedPlan, /secret prompt body/);
  });

  it("treats unknown shared hook status values as invalid output", () => {
    const client = new SharedHookClient({
      cwd: "/repo",
      runner: runner({
        status: 0,
        stdout: JSON.stringify({
          event: "workflow.prompt_guard.validate",
          status: "surprise-success",
        }),
        stderr: "",
      }),
    });

    const result = client.invoke(["validate-prompt"], { eventName: "UserPromptSubmit" });

    assert.equal(result.status, "invalid-output");
  });

  it("defines per-event budgets", () => {
    assert.equal(sharedHookBudgetForEvent("PreToolUse"), 750);
    assert.equal(sharedHookBudgetForEvent("Stop"), 5000);
    assert.equal(sharedHookBudgetForEvent("SessionStart"), 1500);
    assert.equal(sharedHookBudgetForEvent("UserPromptSubmit"), 1500);
    assert.equal(sharedHookBudgetForEvent("PostToolUse"), 1500);
  });

  it("redacts sensitive prompt arguments from previews", () => {
    const preview = redactedInvocationPreview([
      "specify",
      "hook",
      "validate-prompt",
      "--prompt-text",
      "secret prompt body",
    ]);

    assert.doesNotMatch(preview, /secret prompt body/);
    assert.match(preview, /\[REDACTED_PROMPT\]/);
  });

  it("redacts equals-form, repeated, and future free-text style flags from previews", () => {
    const preview = redactedInvocationPreview([
      "specify",
      "hook",
      "validate-prompt",
      "--prompt-text=first secret",
      "--free-text",
      "future secret",
      "--prompt-text",
      "second secret",
    ]);

    assert.doesNotMatch(preview, /first secret|future secret|second secret/);
    assert.match(preview, /--prompt-text=\[REDACTED_PROMPT\]/);
    assert.match(preview, /--free-text \[REDACTED_PROMPT\]/);
  });

  it("does not include stdin prompt text in diagnostic previews", () => {
    const client = new SharedHookClient({
      cwd: "/repo",
      runner: runner({
        status: 0,
        stdout: "invalid stdout echoed secret prompt supplied on stdin",
        stderr: "stderr may contain sensitive prompt text and is intentionally not surfaced",
      }),
    });

    const result = client.invoke(["validate-prompt", "--prompt-stdin"], {
      eventName: "UserPromptSubmit",
      stdinText: "secret prompt supplied on stdin",
    });

    assert.equal(result.status, "invalid-output");
    assert.doesNotMatch(result.attemptedPlan, /secret prompt supplied on stdin/);
    assert.doesNotMatch(result.stdoutPreview, /secret prompt supplied on stdin/);
    assert.match(result.stdoutPreview, /\[REDACTED_PROMPT\]/);
  });

  it("redacts trimmed stdin prompt text echoed in invalid stdout previews", () => {
    const client = new SharedHookClient({
      cwd: "/repo",
      runner: runner({
        status: 0,
        stdout: "invalid stdout echoed secret prompt supplied on stdin",
        stderr: "",
      }),
    });

    const result = client.invoke(["validate-prompt", "--prompt-stdin"], {
      eventName: "UserPromptSubmit",
      stdinText: "  secret prompt supplied on stdin  ",
    });

    assert.equal(result.status, "invalid-output");
    assert.doesNotMatch(result.stdoutPreview, /secret prompt supplied on stdin/);
    assert.match(result.stdoutPreview, /\[REDACTED_PROMPT\]/);
    assert.doesNotMatch(result.attemptedPlan, /secret prompt supplied on stdin/);
  });

  it("passes per-event timeout and stdin text to the runner", () => {
    const calls: Array<{ timeoutMs: number; stdinText?: string }> = [];
    const client = new SharedHookClient({
      cwd: "/repo",
      now: () => 1000,
      runner: (_plan, options) => {
        calls.push({ timeoutMs: options.timeoutMs, stdinText: options.stdinText });
        return {
          status: 0,
          stdout: JSON.stringify({
            event: "workflow.prompt_guard.validate",
            status: "ok",
          }),
          stderr: "",
        };
      },
    });

    const result = client.invoke(["validate-prompt", "--prompt-stdin"], {
      eventName: "PreToolUse",
      stdinText: "prompt supplied on stdin",
    });

    assert.equal(result.status, "ok");
    assert.deepEqual(calls, [{ timeoutMs: 750, stdinText: "prompt supplied on stdin" }]);
  });

  it("treats timeout as an event-level budget shared by invocation plans", () => {
    let clock = 1000;
    const timeouts: number[] = [];
    const client = new SharedHookClient({
      cwd: "/repo",
      env: { SPECIFY_HOOK_EXECUTABLE: "custom-specify" },
      now: () => clock,
      runner: (_plan, options) => {
        timeouts.push(options.timeoutMs);
        if (timeouts.length === 1) {
          clock += 600;
          return { status: null, stdout: "", stderr: "", errorCode: "ENOENT" };
        }
        return {
          status: 0,
          stdout: JSON.stringify({
            event: "workflow.prompt_guard.validate",
            status: "ok",
          }),
          stderr: "",
        };
      },
    });

    const result = client.invoke(["validate-prompt"], {
      eventName: "PreToolUse",
    });

    assert.equal(result.status, "ok");
    assert.deepEqual(timeouts, [750, 150]);
  });

  it("returns timeout before starting another plan when the event budget is exhausted", () => {
    let clock = 1000;
    const timeouts: number[] = [];
    const client = new SharedHookClient({
      cwd: "/repo",
      env: { SPECIFY_HOOK_EXECUTABLE: "custom-specify" },
      now: () => clock,
      runner: (_plan, options) => {
        timeouts.push(options.timeoutMs);
        clock += 800;
        return { status: null, stdout: "", stderr: "", errorCode: "ENOENT" };
      },
    });

    const result = client.invoke(["validate-prompt"], {
      eventName: "PreToolUse",
    });

    assert.equal(result.status, "timeout");
    assert.deepEqual(timeouts, [750]);
  });

  it("skips explicit .cmd hook executables instead of generating a shell-backed plan for untrusted args", () => {
    const plans = buildSharedHookInvocationPlans(
      ["validate-prompt", "--prompt-text", "secret & injected"],
      "/repo",
      { SPECIFY_HOOK_EXECUTABLE: "unsafe-hook.cmd" },
    );

    assert.equal(plans.some((plan) => plan.executable === "unsafe-hook.cmd"), false);
    assert.equal(plans.some((plan) => plan.shell === true), false);
    assert.equal(plans[0]?.executable, "specify");
  });
});
