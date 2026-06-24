import assert from "node:assert/strict";
import { chmod, copyFile, mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, describe, it } from "node:test";
import { setTimeout as delay } from "node:timers/promises";

import {
  appendSharedHookContext,
  invokeSharedQualityHook,
  sharedHookBlockOutput,
} from "../specify-quality-adapter.js";

const tempDirs: string[] = [];

async function createTempDir(prefix: string): Promise<string> {
  const dir = await mkdtemp(join(tmpdir(), prefix));
  tempDirs.push(dir);
  return dir;
}

function envWithPath(pathDir: string, extra: NodeJS.ProcessEnv = {}): NodeJS.ProcessEnv {
  return {
    ...process.env,
    PATH: pathDir,
    Path: pathDir,
    SPECIFY_HOOK_EXECUTABLE: undefined,
    ...extra,
  };
}

async function createSpecifyPathShim(stdout: string): Promise<string> {
  const binDir = await createTempDir("specify-quality-shim-");
  if (process.platform === "win32") {
    await copyFile(process.execPath, join(binDir, "specify.exe"));
    await writeFile(join(binDir, "hook"), `console.log(${JSON.stringify(stdout)});\n`, "utf-8");
    return binDir;
  }

  const quoted = stdout.replace(/'/g, "'\\''");
  const shimPath = join(binDir, "specify");
  await writeFile(shimPath, `#!/bin/sh\nprintf '%s\\n' '${quoted}'\n`, "utf-8");
  await chmod(shimPath, 0o755);
  return binDir;
}

afterEach(async () => {
  while (tempDirs.length > 0) {
    const dir = tempDirs.pop();
    if (!dir) continue;
    for (let attempt = 0; attempt < 5; attempt += 1) {
      try {
        await rm(dir, { recursive: true, force: true });
        break;
      } catch (error) {
        const code = (error as NodeJS.ErrnoException).code;
        if (process.platform !== "win32" || (code !== "EBUSY" && code !== "EPERM") || attempt === 4) {
          throw error;
        }
        await delay(50 * (attempt + 1));
      }
    }
  }
});

describe("specify quality adapter", () => {
  it("invokes shared quality hook through SharedHookClient PATH fallback plans", async () => {
    const payload = {
      event: "workflow.prompt_guard.validate",
      status: "ok",
      warnings: ["payload came from shared hook shim"],
    };
    const binDir = await createSpecifyPathShim(JSON.stringify(payload));

    const result = invokeSharedQualityHook(["validate-prompt"], {
      cwd: binDir,
      env: envWithPath(binDir),
    });

    assert.equal(result?.event, payload.event);
    assert.equal(result?.status, "ok");
    assert.deepEqual(result?.warnings, payload.warnings);
  });

  it("fails open when shared quality hook plans are unavailable", async () => {
    const emptyPathDir = await createTempDir("specify-quality-empty-path-");
    const missingExecutable = join(emptyPathDir, "missing-specify-hook");

    const result = invokeSharedQualityHook(["validate-prompt"], {
      cwd: emptyPathDir,
      env: envWithPath(emptyPathDir, { SPECIFY_HOOK_EXECUTABLE: missingExecutable }),
    });

    assert.equal(result, null);
  });

  it("fails open when shared quality hook output is invalid", async () => {
    const binDir = await createSpecifyPathShim("not json");

    const result = invokeSharedQualityHook(["validate-prompt"], {
      cwd: binDir,
      env: envWithPath(binDir),
    });

    assert.equal(result, null);
  });

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

  it("suppresses empty shared compaction resume cues", () => {
    for (const nextAction of ["None", "n/a", "no-op", "noop", ""]) {
      const merged = appendSharedHookContext("Base context.", {
        event: "workflow.compaction.build",
        status: "ok",
        data: {
          artifact: {
            phase_state: {
              next_action: nextAction,
            },
          },
        },
      });

      assert.equal(merged, "Base context.");
    }
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
