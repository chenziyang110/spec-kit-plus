import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { SharedHookClient, type HookProcessRunner } from "../../../hooks/shared-hook-client.js";
import { NativeHookEffectRecorder } from "../effects.js";
import { createNativeHookServices } from "../services.js";

describe("native hook services", () => {
  it("creates services with an effect recorder", () => {
    const services = createNativeHookServices({ cwd: "/repo" });

    services.effects.record({
      kind: "state-read",
      eventName: "SessionStart",
      source: "test",
      target: ".specify/runtime/session.json",
      status: "ok",
      durationMs: 1,
    });

    assert.ok(services.effects instanceof NativeHookEffectRecorder);
    assert.equal(services.effects.all().length, 1);
  });

  it("creates a shared hook client scoped to cwd and env", () => {
    const calls: Array<{ cwd: string; executable: string; env: NodeJS.ProcessEnv }> = [];
    const runner: HookProcessRunner = (plan, options) => {
      calls.push({
        cwd: options.cwd,
        executable: plan.executable,
        env: plan.env,
      });
      return {
        status: 0,
        stdout: JSON.stringify({
          event: "workflow.prompt_guard.validate",
          status: "ok",
        }),
        stderr: "",
      };
    };

    const services = createNativeHookServices({
      cwd: "/repo",
      env: {
        PATH: "/fake/bin",
        SPECIFY_HOOK_EXECUTABLE: "custom-specify",
        CUSTOM_ENV: "scoped",
      },
      runner,
    });

    const result = services.sharedHooks.invoke(["validate-prompt"], {
      eventName: "UserPromptSubmit",
      timeoutMs: 100,
    });

    assert.ok(services.sharedHooks instanceof SharedHookClient);
    assert.equal(result.status, "ok");
    assert.equal(calls.length, 1);
    assert.equal(calls[0]!.cwd, "/repo");
    assert.equal(calls[0]!.executable, "custom-specify");
    assert.equal(calls[0]!.env.CUSTOM_ENV, "scoped");
    assert.equal(calls[0]!.env.OMX_NATIVE_QUALITY_HOOK_CWD, "/repo");
  });

  it("uses injected recorder and shared hook client when provided", () => {
    const effects = new NativeHookEffectRecorder();
    const sharedHooks = new SharedHookClient({
      cwd: "/injected",
      runner: () => ({
        status: 0,
        stdout: JSON.stringify({
          event: "workflow.prompt_guard.validate",
          status: "blocked",
        }),
        stderr: "",
      }),
    });

    const services = createNativeHookServices({
      cwd: "/repo",
      effects,
      sharedHooks,
    });

    assert.equal(services.effects, effects);
    assert.equal(services.sharedHooks, sharedHooks);
    assert.equal(
      services.sharedHooks.invoke(["validate-prompt"], { eventName: "UserPromptSubmit" }).status,
      "blocked",
    );
  });
});
