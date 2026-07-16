import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  NativeHookEffectRecorder,
  redactEffectTarget,
  type NativeHookEffectInput,
} from "../effects.js";

describe("native hook effects", () => {
  it("redacts prompt text from effect targets", () => {
    const redacted = redactEffectTarget("validate-prompt --prompt-text secret prompt body");

    assert.doesNotMatch(redacted ?? "", /secret prompt body/);
    assert.match(redacted ?? "", /\[REDACTED_PROMPT\]/);
  });

  it("redacts equals-form sensitive tails", () => {
    const redacted = redactEffectTarget(
      [
        "specify hook validate-prompt",
        "--prompt-text=first secret",
        "--free-text \"quoted future secret\"",
        "--prompt-text 'second secret'",
        "--safe value",
      ].join(" "),
    );

    assert.doesNotMatch(redacted ?? "", /first secret|quoted future secret|second secret|--safe|value/);
    assert.match(redacted ?? "", /--prompt-text=\[REDACTED_PROMPT\]/);
    assert.doesNotMatch(redacted ?? "", /--free-text/);
  });

  it("redacts prompt-text tails that contain flag-like prompt content", () => {
    const redacted = redactEffectTarget("validate-prompt --prompt-text please use --help now");

    assert.doesNotMatch(redacted ?? "", /please use|--help|now/);
    assert.equal(redacted, "validate-prompt --prompt-text [REDACTED_PROMPT]");
  });

  it("redacts free-text tails including later safe-looking flags", () => {
    const redacted = redactEffectTarget(
      "validate-prompt --free-text \"quoted secret\" --safe value",
    );

    assert.doesNotMatch(redacted ?? "", /quoted secret|--safe|value/);
    assert.equal(redacted, "validate-prompt --free-text [REDACTED_PROMPT]");
  });

  it("leaves safe targets unchanged when no sensitive free-text flag is present", () => {
    const target = "validate-read-path --target-path src/index.ts";

    assert.equal(redactEffectTarget(target), target);
  });

  it("records stable effect metadata with redacted targets", () => {
    const recorder = new NativeHookEffectRecorder();
    const first = recorder.record({
      kind: "shared-hook",
      eventName: "UserPromptSubmit",
      source: "SharedHookClient",
      target: "validate-prompt --prompt-text secret prompt body",
      status: "ok",
      durationMs: 12,
    });
    const second = recorder.record({
      kind: "state-write",
      eventName: "PostToolUse",
      source: "StateStore",
      target: "state/session.json",
      status: "error",
      durationMs: 25,
      errorClass: "timeout",
    });

    assert.equal(first.id, "effect-1");
    assert.equal(second.id, "effect-2");
    assert.deepEqual(recorder.all(), [
      {
        id: "effect-1",
        kind: "shared-hook",
        eventName: "UserPromptSubmit",
        source: "SharedHookClient",
        target: "validate-prompt --prompt-text [REDACTED_PROMPT]",
        status: "ok",
        durationMs: 12,
      },
      {
        id: "effect-2",
        kind: "state-write",
        eventName: "PostToolUse",
        source: "StateStore",
        target: "state/session.json",
        status: "error",
        durationMs: 25,
        errorClass: "timeout",
      },
    ]);
  });

  it("returns copies so external mutation cannot alter recorded effects", () => {
    const recorder = new NativeHookEffectRecorder();
    recorder.record({
      kind: "shared-hook",
      eventName: "PreToolUse",
      source: "SharedHookClient",
      target: "validate-read-path --target-path src/index.ts",
      status: "warn",
      durationMs: 8,
    });

    const effects = recorder.all();
    effects.push({
      id: "effect-999",
      kind: "state-read",
      eventName: "Stop",
      source: "ExternalMutation",
      status: "ok",
      durationMs: 1,
    });
    effects[0]!.target = "mutated target";

    assert.equal(recorder.all().length, 1);
    assert.equal(recorder.all()[0]?.id, "effect-1");
    assert.equal(
      recorder.all()[0]?.target,
      "validate-read-path --target-path src/index.ts",
    );
  });

  it("does not record raw stdout or stderr fields while preserving error class", () => {
    const recorder = new NativeHookEffectRecorder();
    recorder.record({
      kind: "shared-hook",
      eventName: "PostToolUse",
      source: "SharedHookClient",
      target: "build-compaction",
      status: "error",
      durationMs: 25,
      errorClass: "timeout",
    });

    const effect = recorder.all()[0] as unknown as Record<string, unknown>;
    assert.equal(effect.errorClass, "timeout");
    assert.equal("stderr" in effect, false);
    assert.equal("stdout" in effect, false);
  });

  it("drops runtime stdout and stderr fields from widened record inputs", () => {
    const recorder = new NativeHookEffectRecorder();
    recorder.record({
      kind: "shared-hook",
      eventName: "UserPromptSubmit",
      source: "SharedHookClient",
      target: "validate-prompt --prompt-text secret prompt body",
      status: "error",
      durationMs: 31,
      errorClass: "invalid-output",
      stdout: "raw stdout with secret prompt body",
      stderr: "raw stderr with secret prompt body",
    } as unknown as NativeHookEffectInput);

    const effect = recorder.all()[0] as unknown as Record<string, unknown>;
    assert.equal(effect.errorClass, "invalid-output");
    assert.equal("stderr" in effect, false);
    assert.equal("stdout" in effect, false);
    assert.doesNotMatch(JSON.stringify(effect), /secret prompt body/);
  });
});
