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

  it("converts repairable-block shared hook payloads into native block output", () => {
    const output = sharedHookBlockOutput("UserPromptSubmit", {
      event: "workflow.policy.evaluate",
      status: "repairable-block",
      errors: ["workflow state missing; repair before continue"],
      actions: ["recreate workflow-state.md"],
    });

    assert.equal(output?.decision, "block");
    assert.match(String(output?.reason ?? ""), /workflow state missing/i);
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

  it("appends shared compaction resume cues to existing context", () => {
    const merged = appendSharedHookContext("Base context.", {
      event: "workflow.compaction.build",
      status: "ok",
      data: {
        artifact: {
          phase_state: {
            next_action: "finish design review",
          },
        },
      },
    });

    assert.match(merged ?? "", /Base context\./);
    assert.match(merged ?? "", /Resume cue: finish design review\./);
  });

  it("appends shared recovery summary text to existing context", () => {
    const merged = appendSharedHookContext("Base context.", {
      event: "workflow.compaction.build",
      status: "ok",
      data: {
        artifact: {
          recovery_summary: {
            phase_mode: "planning-only",
            next_action: "refine scope",
            next_command: "/sp.plan",
            route_reason: "spec not yet approved for implementation",
          },
        },
      },
    });

    assert.match(merged ?? "", /Base context\./);
    assert.match(merged ?? "", /Phase: planning-only\./);
    assert.match(merged ?? "", /Next action: refine scope\./);
    assert.match(merged ?? "", /Next command: \/sp\.plan\./);
    assert.match(merged ?? "", /Reason: spec not yet approved for implementation\./);
  });

  it("appends workflow-policy redirect recovery summary text to existing context", () => {
    const merged = appendSharedHookContext("Base context.", {
      event: "workflow.policy.evaluate",
      status: "warn",
      data: {
        policy: {
          classification: "redirect",
          recovery_summary: {
            phase_mode: "planning-only",
            next_action: "refine scope",
            next_command: "/sp.plan",
            route_reason: "spec not yet approved for implementation",
          },
        },
      },
    });

    assert.match(merged ?? "", /Base context\./);
    assert.match(merged ?? "", /Phase: planning-only\./);
    assert.match(merged ?? "", /Next action: refine scope\./);
    assert.match(merged ?? "", /Next command: \/sp\.plan\./);
    assert.match(merged ?? "", /Reason: spec not yet approved for implementation\./);
  });
});
