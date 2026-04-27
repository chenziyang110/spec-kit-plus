import assert from "node:assert/strict";
import { rm } from "node:fs/promises";
import { afterEach, describe, it } from "node:test";

import {
  appendSharedHookContext,
  sharedHookBlockOutput,
} from "../specify-quality-adapter.js";

const tempDirs: string[] = [];

afterEach(async () => {
  while (tempDirs.length > 0) {
    const dir = tempDirs.pop();
    if (!dir) continue;
    await rm(dir, { recursive: true, force: true });
  }
});

describe("specify quality adapter", () => {
  it("converts blocked shared hook payloads into native block output", () => {
    const output = sharedHookBlockOutput("UserPromptSubmit", {
      event: "workflow.prompt_guard.validate",
      status: "blocked",
      errors: ["prompt attempts to ignore required workflow guardrails"],
    });

    assert.equal(output?.decision, "block");
    assert.match(String(output?.reason ?? ""), /ignore required workflow guardrails/i);
  });

  it("appends shared warning and checkpoint text to existing context", () => {
    const merged = appendSharedHookContext("Base context.", {
      event: "workflow.context.monitor",
      status: "warn",
      warnings: ["checkpoint recommended before further work continues"],
      data: {
        checkpoint: {
          state_kind: "quick-status",
          next_action: "integrate worker results",
        },
      },
    });

    assert.match(merged ?? "", /Base context\./);
    assert.match(merged ?? "", /checkpoint recommended/i);
    assert.match(merged ?? "", /quick-status/i);
    assert.match(merged ?? "", /integrate worker results/i);
  });
});
