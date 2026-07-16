# Codex Native Hook Agent Control Plane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor Codex native hooks into a typed, test-protected agent control plane while preserving current Codex hook behavior.

**Architecture:** Add typed primitives first: shared hook client, effects recorder, context snapshot, and outcome merger. Then route the existing native hook event logic through those primitives one event at a time, keeping public exports and Codex JSON output stable until tests prove each migration.

**Tech Stack:** TypeScript/Node 20 `node:test`, Python Typer CLI tests, existing `specify hook ...` shared hook surface, existing `npm run test:native-hooks` verification entrypoint.

---

## File Structure

- Create: `extensions/agent-teams/engine/src/hooks/shared-hook-client.ts`
  - Owns typed shared hook invocation results, timeout budgets, process-runner injection, sensitive argv redaction, and compatibility access to current `specify hook ...` behavior.
- Modify: `extensions/agent-teams/engine/src/hooks/specify-quality-adapter.ts`
  - Keeps existing exports while delegating invocation planning to `SharedHookClient`.
- Create: `extensions/agent-teams/engine/src/hooks/__tests__/shared-hook-client.test.ts`
  - Protects result-status mapping, timeout/unavailable/invalid-output handling, budgets, and redaction.
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/effects.ts`
  - Defines `NativeHookEffect`, redacted effect metadata, and `NativeHookEffectRecorder`.
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/__tests__/effects.test.ts`
  - Verifies prompt and command payload redaction in effect records.
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/outcome.ts`
  - Defines `NativeHookOutcome`, outcome helpers, deterministic merge precedence, and Codex JSON conversion.
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/__tests__/outcome.test.ts`
  - Protects hard/repair/review/continue/advisory precedence and Stop metadata preservation.
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/context.ts`
  - Builds `NativeHookContext` from raw Codex payload once per event.
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/__tests__/context.test.ts`
  - Verifies event/session/tool/prompt normalization.
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/services.ts`
  - Defines `NativeHookServices` and default service constructors used by event handlers.
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/dispatcher.ts`
  - Provides the final event routing surface after handlers are extracted.
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/session-start.ts`
  - Owns `SessionStart` handling after extraction.
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/user-prompt.ts`
  - Owns `UserPromptSubmit` handling after extraction.
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/tool-use.ts`
  - Owns `PreToolUse` and `PostToolUse` handling after extraction.
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/stop.ts`
  - Owns `Stop` handling after extraction.
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`
  - Shrinks to CLI stdin parsing, malformed JSON handling, public re-exports, and dispatcher invocation.
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-pre-post.ts`
  - Remains as a compatibility import target in this plan; do not fold it into `native-hook/tool-use.ts` until all existing imports have moved in a separate cleanup.
- Modify: `src/specify_cli/__init__.py`
  - Adds stdin-compatible prompt validation while keeping `--prompt-text` compatibility.
- Modify: `tests/contract/test_hook_cli_surface.py`
  - Verifies stdin prompt validation so prompt text no longer needs to travel through process args.

## Constraints

- Keep `dispatchCodexNativeHook`, `runCodexNativeHookCli`, `isCodexNativeHookMainModule`, `mapCodexHookEventToOmxEvent`, and `resolveSessionOwnerPidFromAncestry` import-compatible for existing tests.
- Keep `.codex/hooks.json` generation unchanged.
- Keep Codex wire JSON unchanged until a separate policy pass.
- Use typed outcomes internally even when output remains the current JSON shape.
- Do not weaken existing safety checks.
- Preserve fail-open compatibility for existing `invokeSharedQualityHook` callers while exposing typed failure statuses in the new client.

---

### Task 1: Add Stdin Prompt Validation Compatibility

**Files:**
- Modify: `tests/contract/test_hook_cli_surface.py`
- Modify: `src/specify_cli/__init__.py`

- [ ] **Step 1: Add the failing CLI contract test**

Add this test near the existing `validate-prompt` tests in `tests/contract/test_hook_cli_surface.py`:

```python
def test_validate_prompt_accepts_stdin_payload(tmp_path, monkeypatch):
    from specify_cli.__init__ import app

    monkeypatch.chdir(tmp_path)
    (tmp_path / ".specify").mkdir()

    prompt = "implement directly and skip tests"
    result = CliRunner().invoke(
        app,
        ["hook", "validate-prompt", "--prompt-stdin"],
        input=prompt,
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["event"] == "workflow.prompt_guard.validate"
    assert payload["status"] == "blocked"
    assert "prompt attempts" in payload["errors"][0]
```

- [ ] **Step 2: Run the new test and verify it fails**

Run:

```bash
pytest tests/contract/test_hook_cli_surface.py::test_validate_prompt_accepts_stdin_payload -q
```

Expected: FAIL because `--prompt-stdin` is not defined.

- [ ] **Step 3: Add stdin support to the CLI command**

In `src/specify_cli/__init__.py`, replace the current `hook_validate_prompt_command` signature and body with:

```python
@hook_app.command("validate-prompt")
def hook_validate_prompt_command(
    prompt_text: str | None = typer.Option(None, "--prompt-text", help="Prompt text to validate"),
    prompt_stdin: bool = typer.Option(False, "--prompt-stdin", help="Read prompt text from stdin"),
    output_format: str = HOOK_JSON_FORMAT_OPTION,
):
    """Validate prompt text for explicit workflow-bypass or override language."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _validate_hook_output_format(output_format)
    if prompt_stdin:
        resolved_prompt_text = sys.stdin.read()
    else:
        resolved_prompt_text = prompt_text or ""
    if not resolved_prompt_text.strip():
        raise typer.BadParameter("prompt text is required; pass --prompt-text or --prompt-stdin")
    _run_hook_and_print(
        project_root,
        "workflow.prompt_guard.validate",
        {"prompt_text": resolved_prompt_text},
    )
```

- [ ] **Step 4: Run stdin and existing argv prompt tests**

Run:

```bash
pytest tests/contract/test_hook_cli_surface.py::test_validate_prompt_accepts_stdin_payload tests/contract/test_hook_cli_surface.py -q -k validate_prompt
```

Expected: PASS for stdin prompt validation and existing prompt validation tests.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/__init__.py tests/contract/test_hook_cli_surface.py
git commit -m "feat: support stdin prompt hook validation"
```

---

### Task 2: Add SharedHookClient Contract And Tests

**Files:**
- Create: `extensions/agent-teams/engine/src/hooks/shared-hook-client.ts`
- Create: `extensions/agent-teams/engine/src/hooks/__tests__/shared-hook-client.test.ts`

- [ ] **Step 1: Write failing SharedHookClient tests**

Create `extensions/agent-teams/engine/src/hooks/__tests__/shared-hook-client.test.ts`:

```ts
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  SharedHookClient,
  sharedHookBudgetForEvent,
  redactedInvocationPreview,
  type HookProcessResult,
} from "../shared-hook-client.js";

function runner(result: HookProcessResult) {
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

  it("defines per-event budgets", () => {
    assert.equal(sharedHookBudgetForEvent("PreToolUse"), 750);
    assert.equal(sharedHookBudgetForEvent("Stop"), 5000);
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
});
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/hooks/__tests__/shared-hook-client.test.js
```

Expected: FAIL because `shared-hook-client.ts` does not exist.

- [ ] **Step 3: Implement SharedHookClient**

Create `extensions/agent-teams/engine/src/hooks/shared-hook-client.ts`:

```ts
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { packageRoot } from "../utils/paths.js";

export type CodexHookEventName =
  | "SessionStart"
  | "PreToolUse"
  | "PostToolUse"
  | "UserPromptSubmit"
  | "Stop";

export type HookStatus = "ok" | "warn" | "blocked" | "repaired" | "repairable-block";

export interface SharedQualityHookPayload {
  event: string;
  status: HookStatus;
  severity?: string;
  actions?: string[];
  errors?: string[];
  warnings?: string[];
  writes?: Record<string, unknown>;
  data?: Record<string, unknown>;
}

export interface HookInvocationPlan {
  executable: string;
  args: string[];
  env: NodeJS.ProcessEnv;
  shell?: boolean;
}

export interface HookProcessResult {
  status: number | null;
  stdout: string;
  stderr: string;
  errorCode?: string;
  timedOut?: boolean;
}

export type HookProcessRunner = (
  plan: HookInvocationPlan,
  options: { cwd: string; timeoutMs: number; stdinText?: string },
) => HookProcessResult;

export type SharedHookClientResult =
  | { status: "ok"; payload: SharedQualityHookPayload; durationMs: number }
  | { status: "blocked"; payload: SharedQualityHookPayload; durationMs: number }
  | { status: "unavailable"; reason: string; attemptedPlans: string[]; durationMs: number }
  | { status: "timeout"; timeoutMs: number; attemptedPlan: string; durationMs: number }
  | { status: "invalid-output"; stdoutPreview: string; attemptedPlan: string; durationMs: number };

export interface SharedHookInvokeOptions {
  eventName: CodexHookEventName;
  timeoutMs?: number;
  stdinText?: string;
}

export interface SharedHookClientOptions {
  cwd: string;
  env?: NodeJS.ProcessEnv;
  runner?: HookProcessRunner;
  now?: () => number;
}

function repoRootFromPackage(): string {
  return resolve(packageRoot(), "..", "..", "..");
}

function hasRepoSourceCheckout(): boolean {
  return existsSync(join(repoRootFromPackage(), "src", "specify_cli", "__init__.py"));
}

function defaultRunner(
  plan: HookInvocationPlan,
  options: { cwd: string; timeoutMs: number; stdinText?: string },
): HookProcessResult {
  const result = spawnSync(plan.executable, plan.args, {
    cwd: options.cwd,
    encoding: "utf-8",
    env: plan.env,
    shell: plan.shell === true,
    input: options.stdinText,
    timeout: options.timeoutMs,
  });
  return {
    status: result.status,
    stdout: String(result.stdout ?? ""),
    stderr: String(result.stderr ?? ""),
    errorCode: (result.error as NodeJS.ErrnoException | undefined)?.code,
    timedOut: result.error && (result.error as NodeJS.ErrnoException).code === "ETIMEDOUT",
  };
}

function addInvocationPlan(
  plans: HookInvocationPlan[],
  seen: Set<string>,
  executable: string,
  args: string[],
  env: NodeJS.ProcessEnv,
  shell = false,
): void {
  const key = `${executable}\u0000${args.join("\u0000")}`;
  if (seen.has(key)) return;
  seen.add(key);
  plans.push({ executable, args, env, shell });
}

export function buildSharedHookInvocationPlans(
  hookArgs: string[],
  cwd: string,
  env: NodeJS.ProcessEnv = process.env,
): HookInvocationPlan[] {
  const plans: HookInvocationPlan[] = [];
  const seen = new Set<string>();
  const explicit = String(env.SPECIFY_HOOK_EXECUTABLE ?? "").trim();
  if (explicit) {
    addInvocationPlan(explicit, ["hook", ...hookArgs], env, /\.cmd$/i.test(explicit) || /\.bat$/i.test(explicit));
  }

  addInvocationPlan("specify", ["hook", ...hookArgs], env);

  if (hasRepoSourceCheckout()) {
    const repoRoot = repoRootFromPackage();
    const pythonEnv = {
      ...env,
      PYTHONPATH: env.PYTHONPATH
        ? `${join(repoRoot, "src")}${process.platform === "win32" ? ";" : ":"}${env.PYTHONPATH}`
        : join(repoRoot, "src"),
    };
    addInvocationPlan("python", ["-m", "specify_cli", "hook", ...hookArgs], pythonEnv);
    if (process.platform === "win32") {
      addInvocationPlan("py", ["-m", "specify_cli", "hook", ...hookArgs], pythonEnv);
    } else {
      addInvocationPlan("python3", ["-m", "specify_cli", "hook", ...hookArgs], pythonEnv);
    }
  }

  return plans.map((plan) => ({
    ...plan,
    env: {
      ...plan.env,
      OMX_NATIVE_QUALITY_HOOK_CWD: cwd,
    },
  }));
}

export function sharedHookBudgetForEvent(eventName: CodexHookEventName): number {
  switch (eventName) {
    case "PreToolUse":
      return 750;
    case "Stop":
      return 5000;
    case "SessionStart":
    case "UserPromptSubmit":
    case "PostToolUse":
      return 1500;
  }
}

export function redactedInvocationPreview(argv: string[]): string {
  const redacted: string[] = [];
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index] ?? "";
    redacted.push(token);
    if (token === "--prompt-text") {
      index += 1;
      redacted.push("[REDACTED_PROMPT]");
    }
  }
  return redacted.join(" ");
}

function stdoutPreview(stdout: string): string {
  return stdout.trim().slice(0, 500);
}

function parseSharedPayload(stdout: string): SharedQualityHookPayload | null {
  if (!stdout.trim()) return null;
  try {
    const parsed = JSON.parse(stdout.trim()) as SharedQualityHookPayload;
    if (parsed && typeof parsed === "object" && typeof parsed.event === "string" && typeof parsed.status === "string") {
      return parsed;
    }
  } catch {
    return null;
  }
  return null;
}

export class SharedHookClient {
  private readonly cwd: string;
  private readonly env: NodeJS.ProcessEnv;
  private readonly runner: HookProcessRunner;
  private readonly now: () => number;

  constructor(options: SharedHookClientOptions) {
    this.cwd = options.cwd;
    this.env = options.env ?? process.env;
    this.runner = options.runner ?? defaultRunner;
    this.now = options.now ?? (() => Date.now());
  }

  invoke(hookArgs: string[], options: SharedHookInvokeOptions): SharedHookClientResult {
    const started = this.now();
    const timeoutMs = options.timeoutMs ?? sharedHookBudgetForEvent(options.eventName);
    const attemptedPlans: string[] = [];
    const plans = buildSharedHookInvocationPlans(hookArgs, this.cwd, this.env);

    for (const plan of plans) {
      const preview = redactedInvocationPreview([plan.executable, ...plan.args]);
      attemptedPlans.push(preview);
      const result = this.runner(plan, {
        cwd: this.cwd,
        timeoutMs,
        stdinText: options.stdinText,
      });
      const durationMs = Math.max(0, this.now() - started);
      if (result.timedOut) {
        return { status: "timeout", timeoutMs, attemptedPlan: preview, durationMs };
      }
      if (result.status !== 0) continue;
      const payload = parseSharedPayload(result.stdout);
      if (!payload) {
        return {
          status: "invalid-output",
          stdoutPreview: stdoutPreview(result.stdout),
          attemptedPlan: preview,
          durationMs,
        };
      }
      if (payload.status === "blocked" || payload.status === "repairable-block") {
        return { status: "blocked", payload, durationMs };
      }
      return { status: "ok", payload, durationMs };
    }

    return {
      status: "unavailable",
      reason: "no shared hook invocation plan produced valid JSON",
      attemptedPlans,
      durationMs: Math.max(0, this.now() - started),
    };
  }
}
```

- [ ] **Step 4: Run SharedHookClient tests**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/hooks/__tests__/shared-hook-client.test.js
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add extensions/agent-teams/engine/src/hooks/shared-hook-client.ts extensions/agent-teams/engine/src/hooks/__tests__/shared-hook-client.test.ts
git commit -m "feat: add shared hook client contract"
```

---

### Task 3: Add Outcome Model And Precedence Tests

**Files:**
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/outcome.ts`
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/__tests__/outcome.test.ts`

- [ ] **Step 1: Write failing outcome tests**

Create `extensions/agent-teams/engine/src/scripts/native-hook/__tests__/outcome.test.ts`:

```ts
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
  it("keeps hard-block ahead of every other outcome", () => {
    const merged = mergeNativeHookOutcomes("PreToolUse", [
      advisory("PreToolUse", "triage", "extra context"),
      reviewBlock("PreToolUse", "native-local", "read command output first", "output context"),
      hardBlock("PreToolUse", "shared-hook", "sensitive file read blocked", "secret path"),
    ]);

    assert.equal(merged?.kind, "hard-block");
    assert.equal(merged?.reason, "sensitive file read blocked");
    assert.match(merged?.additionalContext ?? "", /extra context/);
    assert.match(merged?.additionalContext ?? "", /read command output first/);
  });

  it("keeps repair-block ahead of review-block", () => {
    const merged = mergeNativeHookOutcomes("UserPromptSubmit", [
      reviewBlock("UserPromptSubmit", "native-local", "review output", "review context"),
      repairBlock("UserPromptSubmit", "shared-hook", "workflow state missing", "repair state"),
    ]);

    assert.equal(merged?.kind, "repair-block");
    assert.equal(merged?.reason, "workflow state missing");
  });

  it("keeps continue-block ahead of review-block during Stop", () => {
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

  it("renders advisory-only Codex JSON without decision", () => {
    const output = outcomeToCodexJson(advisory("SessionStart", "compaction", "Resume cue: refine scope."));

    assert.deepEqual(output, {
      hookSpecificOutput: {
        hookEventName: "SessionStart",
        additionalContext: "Resume cue: refine scope.",
      },
    });
  });

  it("renders blocking Codex JSON with decision block", () => {
    const output = outcomeToCodexJson(
      hardBlock("UserPromptSubmit", "shared-hook", "prompt attempts to bypass workflow", "workflow guard"),
    );

    assert.equal(output?.decision, "block");
    assert.equal(output?.reason, "prompt attempts to bypass workflow");
    assert.equal(output?.hookSpecificOutput?.hookEventName, "UserPromptSubmit");
  });
});
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/scripts/native-hook/__tests__/outcome.test.js
```

Expected: FAIL because `outcome.ts` does not exist.

- [ ] **Step 3: Implement outcome helpers**

Create `extensions/agent-teams/engine/src/scripts/native-hook/outcome.ts`:

```ts
export type CodexHookEventName =
  | "SessionStart"
  | "PreToolUse"
  | "PostToolUse"
  | "UserPromptSubmit"
  | "Stop";

export type NativeHookOutcomeKind =
  | "advisory"
  | "hard-block"
  | "repair-block"
  | "review-block"
  | "continue-block";

export type NativeHookOutcomeSource =
  | "native-local"
  | "shared-hook"
  | "triage"
  | "compaction"
  | "learning";

export interface NativeHookOutcome {
  kind: NativeHookOutcomeKind;
  eventName: CodexHookEventName;
  source: NativeHookOutcomeSource;
  reason?: string;
  additionalContext?: string;
  stopReason?: string;
  systemMessage?: string;
  repeatSignature?: string;
  effectRefs?: string[];
}

export type CodexHookOutput = Record<string, unknown> & {
  decision?: string;
  reason?: string;
  hookSpecificOutput?: {
    hookEventName?: string;
    additionalContext?: string;
  };
};

interface ContinueMetadata {
  stopReason?: string;
  systemMessage?: string;
  repeatSignature?: string;
  effectRefs?: string[];
}

export function advisory(
  eventName: CodexHookEventName,
  source: NativeHookOutcomeSource,
  additionalContext: string,
): NativeHookOutcome {
  return { kind: "advisory", eventName, source, additionalContext };
}

export function hardBlock(
  eventName: CodexHookEventName,
  source: NativeHookOutcomeSource,
  reason: string,
  additionalContext = reason,
): NativeHookOutcome {
  return { kind: "hard-block", eventName, source, reason, additionalContext };
}

export function repairBlock(
  eventName: CodexHookEventName,
  source: NativeHookOutcomeSource,
  reason: string,
  additionalContext = reason,
): NativeHookOutcome {
  return { kind: "repair-block", eventName, source, reason, additionalContext };
}

export function reviewBlock(
  eventName: CodexHookEventName,
  source: NativeHookOutcomeSource,
  reason: string,
  additionalContext = reason,
): NativeHookOutcome {
  return { kind: "review-block", eventName, source, reason, additionalContext };
}

export function continueBlock(
  eventName: CodexHookEventName,
  source: NativeHookOutcomeSource,
  reason: string,
  additionalContext = reason,
  metadata: ContinueMetadata = {},
): NativeHookOutcome {
  return {
    kind: "continue-block",
    eventName,
    source,
    reason,
    additionalContext,
    stopReason: metadata.stopReason,
    systemMessage: metadata.systemMessage,
    repeatSignature: metadata.repeatSignature,
    effectRefs: metadata.effectRefs,
  };
}

function precedence(eventName: CodexHookEventName, kind: NativeHookOutcomeKind): number {
  if (kind === "hard-block") return 50;
  if (kind === "repair-block") return 40;
  if (eventName === "Stop" && kind === "continue-block") return 35;
  if (kind === "review-block") return 30;
  if (kind === "continue-block") return 25;
  return 10;
}

function dedupeContexts(values: Array<string | undefined>): string {
  const seen = new Set<string>();
  const ordered: string[] = [];
  for (const value of values) {
    const trimmed = String(value ?? "").trim();
    if (!trimmed || seen.has(trimmed)) continue;
    seen.add(trimmed);
    ordered.push(trimmed);
  }
  return ordered.join(" ");
}

export function mergeNativeHookOutcomes(
  eventName: CodexHookEventName,
  outcomes: NativeHookOutcome[],
): NativeHookOutcome | null {
  const present = outcomes.filter((outcome) => outcome.eventName === eventName);
  if (present.length === 0) return null;

  const primary = present.reduce((best, candidate) => {
    return precedence(eventName, candidate.kind) > precedence(eventName, best.kind)
      ? candidate
      : best;
  });
  const additionalContext = dedupeContexts([
    primary.additionalContext,
    ...present
      .filter((outcome) => outcome !== primary)
      .map((outcome) => outcome.additionalContext || outcome.reason),
  ]);

  return {
    ...primary,
    additionalContext,
    effectRefs: [
      ...new Set(present.flatMap((outcome) => outcome.effectRefs ?? [])),
    ],
  };
}

export function outcomeToCodexJson(outcome: NativeHookOutcome | null): CodexHookOutput | null {
  if (!outcome) return null;
  const additionalContext = String(outcome.additionalContext ?? "").trim();
  if (outcome.kind === "advisory") {
    if (!additionalContext) return null;
    return {
      hookSpecificOutput: {
        hookEventName: outcome.eventName,
        additionalContext,
      },
    };
  }

  return {
    decision: "block",
    reason: outcome.reason || additionalContext || "native hook blocked the action",
    ...(outcome.stopReason ? { stopReason: outcome.stopReason } : {}),
    ...(outcome.systemMessage ? { systemMessage: outcome.systemMessage } : {}),
    hookSpecificOutput: {
      hookEventName: outcome.eventName,
      ...(additionalContext ? { additionalContext } : {}),
    },
  };
}
```

- [ ] **Step 4: Run outcome tests**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/scripts/native-hook/__tests__/outcome.test.js
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add extensions/agent-teams/engine/src/scripts/native-hook/outcome.ts extensions/agent-teams/engine/src/scripts/native-hook/__tests__/outcome.test.ts
git commit -m "feat: add native hook outcome model"
```

---

### Task 4: Add Effects Recorder And Redaction Boundary

**Files:**
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/effects.ts`
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/__tests__/effects.test.ts`

- [ ] **Step 1: Write failing effects tests**

Create `extensions/agent-teams/engine/src/scripts/native-hook/__tests__/effects.test.ts`:

```ts
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  NativeHookEffectRecorder,
  redactEffectTarget,
} from "../effects.js";

describe("native hook effects", () => {
  it("redacts prompt text from effect targets", () => {
    const redacted = redactEffectTarget("validate-prompt --prompt-text secret prompt body");

    assert.doesNotMatch(redacted, /secret prompt body/);
    assert.match(redacted, /\[REDACTED_PROMPT\]/);
  });

  it("records effect metadata without leaking sensitive prompt text", () => {
    const recorder = new NativeHookEffectRecorder();
    const effect = recorder.record({
      kind: "shared-hook",
      eventName: "UserPromptSubmit",
      source: "SharedHookClient",
      target: "validate-prompt --prompt-text secret prompt body",
      status: "ok",
      durationMs: 12,
    });

    assert.equal(effect.id, "effect-1");
    assert.doesNotMatch(JSON.stringify(recorder.all()), /secret prompt body/);
    assert.match(JSON.stringify(recorder.all()), /\[REDACTED_PROMPT\]/);
  });

  it("records error class without raw stderr", () => {
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

    assert.equal(recorder.all()[0]?.errorClass, "timeout");
    assert.equal("stderr" in (recorder.all()[0] as Record<string, unknown>), false);
  });
});
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/scripts/native-hook/__tests__/effects.test.js
```

Expected: FAIL because `effects.ts` does not exist.

- [ ] **Step 3: Implement effects recorder**

Create `extensions/agent-teams/engine/src/scripts/native-hook/effects.ts`:

```ts
import type { CodexHookEventName } from "./outcome.js";

export type NativeHookEffectKind =
  | "shared-hook"
  | "state-read"
  | "state-write"
  | "hud-reconcile"
  | "plugin-dispatch"
  | "git-exclude-write"
  | "team-state-write"
  | "compaction-write"
  | "learning-signal"
  | "stop-signature-write";

export type NativeHookEffectStatus = "ok" | "warn" | "error" | "skipped";

export interface NativeHookEffectInput {
  kind: NativeHookEffectKind;
  eventName: CodexHookEventName;
  source: string;
  target?: string;
  status: NativeHookEffectStatus;
  durationMs: number;
  errorClass?: string;
}

export interface NativeHookEffect extends NativeHookEffectInput {
  id: string;
}

export function redactEffectTarget(target: string | undefined): string | undefined {
  if (!target) return undefined;
  return target.replace(/(--prompt-text\s+)(?:"[^"]*"|'[^']*'|\S.*)$/u, "$1[REDACTED_PROMPT]");
}

export class NativeHookEffectRecorder {
  private effects: NativeHookEffect[] = [];

  record(input: NativeHookEffectInput): NativeHookEffect {
    const effect: NativeHookEffect = {
      ...input,
      id: `effect-${this.effects.length + 1}`,
      target: redactEffectTarget(input.target),
    };
    this.effects.push(effect);
    return effect;
  }

  all(): NativeHookEffect[] {
    return this.effects.map((effect) => ({ ...effect }));
  }
}
```

- [ ] **Step 4: Run effects tests**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/scripts/native-hook/__tests__/effects.test.js
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add extensions/agent-teams/engine/src/scripts/native-hook/effects.ts extensions/agent-teams/engine/src/scripts/native-hook/__tests__/effects.test.ts
git commit -m "feat: add native hook effects recorder"
```

---

### Task 5: Add Context Snapshot Builder

**Files:**
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/context.ts`
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/__tests__/context.test.ts`

- [ ] **Step 1: Write failing context tests**

Create `extensions/agent-teams/engine/src/scripts/native-hook/__tests__/context.test.ts`:

```ts
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { buildNativeHookContext } from "../context.js";

describe("native hook context", () => {
  it("normalizes event and session fields", () => {
    const context = buildNativeHookContext({
      cwd: "/repo",
      hook_event_name: "UserPromptSubmit",
      session_id: "native-1",
      thread_id: "thread-1",
      turn_id: "turn-1",
      prompt: "fix this",
    });

    assert.equal(context.cwd, "/repo");
    assert.equal(context.eventName, "UserPromptSubmit");
    assert.equal(context.nativeSessionId, "native-1");
    assert.equal(context.threadId, "thread-1");
    assert.equal(context.turnId, "turn-1");
    assert.equal(context.promptText, "fix this");
  });

  it("normalizes tool payload fields", () => {
    const context = buildNativeHookContext({
      cwd: "/repo",
      hookEventName: "PreToolUse",
      tool_name: "Bash",
      tool_use_id: "tool-1",
      tool_input: { command: "cat README.md" },
    });

    assert.equal(context.eventName, "PreToolUse");
    assert.equal(context.toolName, "Bash");
    assert.equal(context.toolUseId, "tool-1");
    assert.deepEqual(context.toolInput, { command: "cat README.md" });
  });

  it("uses process cwd when payload cwd is absent", () => {
    const context = buildNativeHookContext({
      hook_event_name: "Stop",
    });

    assert.equal(context.cwd, process.cwd());
    assert.equal(context.eventName, "Stop");
  });
});
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/scripts/native-hook/__tests__/context.test.js
```

Expected: FAIL because `context.ts` does not exist.

- [ ] **Step 3: Implement context builder**

Create `extensions/agent-teams/engine/src/scripts/native-hook/context.ts`:

```ts
import { specifyRuntimeStateDir } from "../../utils/paths.js";
import type { CodexHookEventName } from "./outcome.js";

export type CodexHookPayload = Record<string, unknown>;

export interface NativeHookContext {
  cwd: string;
  eventName: CodexHookEventName | null;
  nativeSessionId: string;
  canonicalSessionId: string;
  threadId: string;
  turnId: string;
  promptText: string;
  toolName: string;
  toolUseId: string;
  toolInput: Record<string, unknown>;
  toolResponse: unknown;
  activeWorkflow: null;
  runtimeStateDir: string;
  rawPayload: CodexHookPayload;
}

function safeString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function safeObject(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

export function readNativeHookEventName(payload: CodexHookPayload): CodexHookEventName | null {
  const raw = safeString(
    payload.hook_event_name
      ?? payload.hookEventName
      ?? payload.event
      ?? payload.name,
  );
  if (
    raw === "SessionStart"
    || raw === "PreToolUse"
    || raw === "PostToolUse"
    || raw === "UserPromptSubmit"
    || raw === "Stop"
  ) {
    return raw;
  }
  return null;
}

export function readPromptText(payload: CodexHookPayload): string {
  return safeString(payload.prompt) || safeString(payload.user_prompt) || safeString(payload.userPrompt);
}

export function buildNativeHookContext(payload: CodexHookPayload): NativeHookContext {
  const cwd = safeString(payload.cwd) || process.cwd();
  return {
    cwd,
    eventName: readNativeHookEventName(payload),
    nativeSessionId: safeString(payload.session_id ?? payload.sessionId),
    canonicalSessionId: "",
    threadId: safeString(payload.thread_id ?? payload.threadId),
    turnId: safeString(payload.turn_id ?? payload.turnId),
    promptText: readPromptText(payload),
    toolName: safeString(payload.tool_name ?? payload.toolName),
    toolUseId: safeString(payload.tool_use_id ?? payload.toolUseId),
    toolInput: safeObject(payload.tool_input ?? payload.toolInput),
    toolResponse: payload.tool_response ?? payload.toolResponse,
    activeWorkflow: null,
    runtimeStateDir: specifyRuntimeStateDir(cwd),
    rawPayload: payload,
  };
}
```

- [ ] **Step 4: Run context tests**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/scripts/native-hook/__tests__/context.test.js
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add extensions/agent-teams/engine/src/scripts/native-hook/context.ts extensions/agent-teams/engine/src/scripts/native-hook/__tests__/context.test.ts
git commit -m "feat: add native hook context snapshot"
```

---

### Task 6: Preserve Existing Adapter Exports Through SharedHookClient

**Files:**
- Modify: `extensions/agent-teams/engine/src/hooks/specify-quality-adapter.ts`
- Modify: `extensions/agent-teams/engine/src/hooks/__tests__/specify-quality-adapter.test.ts`

- [ ] **Step 1: Add compatibility test for invokeSharedQualityHook**

Add this test to `extensions/agent-teams/engine/src/hooks/__tests__/specify-quality-adapter.test.ts`:

```ts
import { mkdtemp, writeFile, chmod } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { invokeSharedQualityHook } from "../specify-quality-adapter.js";

it("keeps invokeSharedQualityHook compatibility while using shared hook plans", async () => {
  const cwd = await mkdtemp(join(tmpdir(), "shared-hook-compat-"));
  tempDirs.push(cwd);
  const binDir = join(cwd, "bin");
  await mkdir(binDir, { recursive: true });
  const specifyShim = join(binDir, process.platform === "win32" ? "specify.cmd" : "specify");
  const body = process.platform === "win32"
    ? '@echo off\r\nnode -e "process.stdout.write(JSON.stringify({event:\'workflow.prompt_guard.validate\',status:\'ok\',severity:\'info\'}))"\r\n'
    : "#!/bin/sh\nnode -e 'process.stdout.write(JSON.stringify({event:\"workflow.prompt_guard.validate\",status:\"ok\",severity:\"info\"}))'\n";
  await writeFile(specifyShim, body, "utf-8");
  if (process.platform !== "win32") {
    await chmod(specifyShim, 0o755);
  }

  const previousPath = process.env.PATH;
  const previousExecutable = process.env.SPECIFY_HOOK_EXECUTABLE;
  process.env.PATH = `${binDir}${process.platform === "win32" ? ";" : ":"}${previousPath ?? ""}`;
  process.env.SPECIFY_HOOK_EXECUTABLE = specifyShim;
  try {
    const payload = invokeSharedQualityHook(["validate-prompt", "--prompt-text", "hello"], { cwd });
    assert.equal(payload?.status, "ok");
  } finally {
    if (typeof previousPath === "string") process.env.PATH = previousPath;
    else delete process.env.PATH;
    if (typeof previousExecutable === "string") process.env.SPECIFY_HOOK_EXECUTABLE = previousExecutable;
    else delete process.env.SPECIFY_HOOK_EXECUTABLE;
  }
});
```

- [ ] **Step 2: Run the compatibility test and verify current behavior**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/hooks/__tests__/specify-quality-adapter.test.js
```

Expected: PASS before refactor. This confirms the test is a guard, not a behavior change.

- [ ] **Step 3: Replace invocation planning with SharedHookClient**

In `extensions/agent-teams/engine/src/hooks/specify-quality-adapter.ts`:

1. Remove local `HookInvocationPlan`, `repoRootFromPackage`, `hasRepoSourceCheckout`, and `buildInvocationPlans`.
2. Import the client:

```ts
import {
  SharedHookClient,
  type SharedQualityHookPayload,
} from "./shared-hook-client.js";
```

3. Keep the exported `SharedQualityHookPayload` type by re-exporting it:

```ts
export type { SharedQualityHookPayload } from "./shared-hook-client.js";
```

4. Replace `invokeSharedQualityHook` with:

```ts
export function invokeSharedQualityHook(
  hookArgs: string[],
  options: {
    cwd: string;
    env?: NodeJS.ProcessEnv;
  },
): SharedQualityHookPayload | null {
  const client = new SharedHookClient({
    cwd: options.cwd,
    env: options.env ?? process.env,
  });
  const result = client.invoke(hookArgs, {
    eventName: "UserPromptSubmit",
    timeoutMs: Number.MAX_SAFE_INTEGER,
  });
  if (result.status === "ok" || result.status === "blocked") {
    return result.payload;
  }
  return null;
}
```

This preserves current fail-open compatibility by returning `null` for unavailable, timeout, or invalid output.

- [ ] **Step 4: Run adapter and shared client tests**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/hooks/__tests__/specify-quality-adapter.test.js dist/hooks/__tests__/shared-hook-client.test.js
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add extensions/agent-teams/engine/src/hooks/specify-quality-adapter.ts extensions/agent-teams/engine/src/hooks/__tests__/specify-quality-adapter.test.ts
git commit -m "refactor: route shared hook adapter through client"
```

---

### Task 7: Add Services Interface Without Moving Event Logic

**Files:**
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/services.ts`
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/__tests__/services.test.ts`

- [ ] **Step 1: Write failing services tests**

Create `extensions/agent-teams/engine/src/scripts/native-hook/__tests__/services.test.ts`:

```ts
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  createNativeHookServices,
} from "../services.js";

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

    assert.equal(services.effects.all().length, 1);
  });

  it("creates a shared hook client scoped to cwd", () => {
    const services = createNativeHookServices({ cwd: "/repo" });

    const result = services.sharedHooks.invoke(["validate-prompt"], {
      eventName: "UserPromptSubmit",
      timeoutMs: 1,
    });

    assert.ok(["unavailable", "timeout", "invalid-output", "ok", "blocked"].includes(result.status));
  });
});
```

- [ ] **Step 2: Run the tests and verify they fail**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/scripts/native-hook/__tests__/services.test.js
```

Expected: FAIL because `services.ts` does not exist.

- [ ] **Step 3: Implement services shell**

Create `extensions/agent-teams/engine/src/scripts/native-hook/services.ts`:

```ts
import { SharedHookClient } from "../../hooks/shared-hook-client.js";
import { NativeHookEffectRecorder } from "./effects.js";

export interface NativeHookServicesOptions {
  cwd: string;
  env?: NodeJS.ProcessEnv;
}

export interface NativeHookServices {
  effects: NativeHookEffectRecorder;
  sharedHooks: SharedHookClient;
}

export function createNativeHookServices(options: NativeHookServicesOptions): NativeHookServices {
  const effects = new NativeHookEffectRecorder();
  return {
    effects,
    sharedHooks: new SharedHookClient({
      cwd: options.cwd,
      env: options.env ?? process.env,
    }),
  };
}
```

- [ ] **Step 4: Run services tests**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/scripts/native-hook/__tests__/services.test.js
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add extensions/agent-teams/engine/src/scripts/native-hook/services.ts extensions/agent-teams/engine/src/scripts/native-hook/__tests__/services.test.ts
git commit -m "feat: add native hook services boundary"
```

---

### Task 8: Route PreToolUse And PostToolUse Through Outcome Wrapper

**Files:**
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/tool-use.ts`
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/__tests__/tool-use.test.ts`
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`

- [ ] **Step 1: Add tool-use wrapper tests**

Create `extensions/agent-teams/engine/src/scripts/native-hook/__tests__/tool-use.test.ts`:

```ts
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { buildNativeHookContext } from "../context.js";
import {
  handlePostToolUse,
  handlePreToolUse,
} from "../tool-use.js";
import { outcomeToCodexJson } from "../outcome.js";

describe("tool-use native hook handler", () => {
  it("returns no outcome for non-Bash PreToolUse payloads", () => {
    const context = buildNativeHookContext({
      hook_event_name: "PreToolUse",
      cwd: "/repo",
      tool_name: "Read",
    });

    assert.equal(handlePreToolUse(context), null);
  });

  it("wraps Bash hard failures as review blocks after tool use", () => {
    const context = buildNativeHookContext({
      hook_event_name: "PostToolUse",
      cwd: "/repo",
      tool_name: "Bash",
      tool_input: { command: "missing-command" },
      tool_response: JSON.stringify({
        exit_code: 127,
        stdout: "",
        stderr: "command not found: missing-command",
      }),
    });

    const output = outcomeToCodexJson(handlePostToolUse(context));

    assert.equal(output?.decision, "block");
    assert.match(String(output?.reason ?? ""), /command\/setup failure/i);
  });
});
```

- [ ] **Step 2: Run the test and verify it fails**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/scripts/native-hook/__tests__/tool-use.test.js
```

Expected: FAIL because `tool-use.ts` does not exist.

- [ ] **Step 3: Implement tool-use wrappers with current logic**

Create `extensions/agent-teams/engine/src/scripts/native-hook/tool-use.ts`:

```ts
import {
  buildNativePostToolUseOutput,
  buildNativePreToolUseOutput,
} from "../codex-native-pre-post.js";
import type { NativeHookContext } from "./context.js";
import {
  hardBlock,
  advisory,
  type NativeHookOutcome,
} from "./outcome.js";

function outputToOutcome(
  eventName: "PreToolUse" | "PostToolUse",
  output: Record<string, unknown> | null,
): NativeHookOutcome | null {
  if (!output) return null;
  const reason = typeof output.reason === "string" ? output.reason : "";
  const specific = output.hookSpecificOutput;
  const additionalContext =
    specific && typeof specific === "object" && typeof (specific as Record<string, unknown>).additionalContext === "string"
      ? String((specific as Record<string, unknown>).additionalContext)
      : reason;
  if (output.decision === "block") {
    return hardBlock(eventName, "native-local", reason || "native tool-use hook blocked the action", additionalContext);
  }
  if (additionalContext) {
    return advisory(eventName, "native-local", additionalContext);
  }
  return null;
}

export function handlePreToolUse(context: NativeHookContext): NativeHookOutcome | null {
  return outputToOutcome("PreToolUse", buildNativePreToolUseOutput(context.rawPayload));
}

export function handlePostToolUse(context: NativeHookContext): NativeHookOutcome | null {
  return outputToOutcome("PostToolUse", buildNativePostToolUseOutput(context.rawPayload));
}
```

- [ ] **Step 4: Use wrapper in `codex-native-hook.ts` for PreToolUse only**

In `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`, import:

```ts
import { buildNativeHookContext } from "./native-hook/context.js";
import { handlePreToolUse } from "./native-hook/tool-use.js";
import { outcomeToCodexJson } from "./native-hook/outcome.js";
```

Replace:

```ts
  } else if (hookEventName === "PreToolUse") {
    outputJson = buildNativePreToolUseOutput(payload);
```

with:

```ts
  } else if (hookEventName === "PreToolUse") {
    outputJson = outcomeToCodexJson(handlePreToolUse(buildNativeHookContext(payload)));
```

Keep `PostToolUse` on the current path in this task because it has transport-failure state writes that move after services are wired.

- [ ] **Step 5: Run focused native hook tests**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/scripts/native-hook/__tests__/tool-use.test.js dist/scripts/__tests__/codex-native-hook.test.js
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add extensions/agent-teams/engine/src/scripts/native-hook/tool-use.ts extensions/agent-teams/engine/src/scripts/native-hook/__tests__/tool-use.test.ts extensions/agent-teams/engine/src/scripts/codex-native-hook.ts
git commit -m "refactor: route pre-tool native hook through outcome"
```

---

### Task 9: Route UserPromptSubmit Shared Checks Through SharedHookClient

**Files:**
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`
- Modify: `extensions/agent-teams/engine/src/scripts/__tests__/codex-native-hook.test.ts`

- [ ] **Step 1: Add prompt argv redaction characterization**

Add this test to `extensions/agent-teams/engine/src/scripts/__tests__/codex-native-hook.test.ts` near the shared prompt guard tests:

```ts
  it("validates prompt through stdin-capable shared hook path without prompt argv leakage", async () => {
    const cwd = await mkdtemp(join(tmpdir(), "omx-native-hook-prompt-stdin-"));
    const binDir = join(cwd, "bin");
    await mkdir(binDir, { recursive: true });
    await mkdir(join(cwd, ".specify"), { recursive: true });
    const capturePath = join(cwd, "argv-capture.json");
    const specifyShim = join(binDir, process.platform === "win32" ? "specify.cmd" : "specify");
    const shimBody = process.platform === "win32"
      ? `@echo off\r\nnode -e "require('fs').writeFileSync(${JSON.stringify(capturePath)}, JSON.stringify(process.argv)); process.stdout.write(JSON.stringify({event:'workflow.prompt_guard.validate',status:'ok',severity:'info'}))"\r\n`
      : `#!/bin/sh\nnode -e 'require("fs").writeFileSync(${JSON.stringify(capturePath)}, JSON.stringify(process.argv)); process.stdout.write(JSON.stringify({event:"workflow.prompt_guard.validate",status:"ok",severity:"info"}))'\n`;
    await writeFile(specifyShim, shimBody, "utf-8");
    if (process.platform !== "win32") {
      await chmod(specifyShim, 0o755);
    }
    const previousPath = process.env.PATH;
    const previousHookExecutable = process.env.SPECIFY_HOOK_EXECUTABLE;
    process.env.PATH = `${binDir}${process.platform === "win32" ? ";" : ":"}${previousPath ?? ""}`;
    process.env.SPECIFY_HOOK_EXECUTABLE = specifyShim;
    try {
      await dispatchCodexNativeHook(
        {
          hook_event_name: "UserPromptSubmit",
          cwd,
          session_id: "prompt-stdin-1",
          thread_id: "thread-prompt-stdin-1",
          turn_id: "turn-prompt-stdin-1",
          prompt: "secret prompt body",
        },
        { cwd },
      );

      const argv = JSON.parse(await readFile(capturePath, "utf-8")) as string[];
      assert.doesNotMatch(argv.join(" "), /secret prompt body/);
    } finally {
      if (typeof previousPath === "string") process.env.PATH = previousPath;
      else delete process.env.PATH;
      if (typeof previousHookExecutable === "string") process.env.SPECIFY_HOOK_EXECUTABLE = previousHookExecutable;
      else delete process.env.SPECIFY_HOOK_EXECUTABLE;
      await rm(cwd, { recursive: true, force: true });
    }
  });
```

- [ ] **Step 2: Run the new characterization and verify it fails**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/scripts/__tests__/codex-native-hook.test.js --test-name-pattern "validates prompt through stdin-capable"
```

Expected: FAIL because prompt text is still passed through `--prompt-text`.

- [ ] **Step 3: Add `validatePrompt` helper to SharedHookClient**

In `extensions/agent-teams/engine/src/hooks/shared-hook-client.ts`, add this method inside `SharedHookClient`:

```ts
  validatePrompt(promptText: string, options: Omit<SharedHookInvokeOptions, "stdinText">): SharedHookClientResult {
    return this.invoke(["validate-prompt", "--prompt-stdin"], {
      ...options,
      stdinText: promptText,
    });
  }
```

- [ ] **Step 4: Use `validatePrompt` in `UserPromptSubmit`**

In `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`, replace:

```ts
      sharedPromptGuardPayload = invokeSharedQualityHook(
        ["validate-prompt", "--prompt-text", prompt],
        { cwd },
      );
```

with:

```ts
      const sharedPromptGuardResult = new SharedHookClient({ cwd }).validatePrompt(prompt, {
        eventName: "UserPromptSubmit",
      });
      sharedPromptGuardPayload =
        sharedPromptGuardResult.status === "ok" || sharedPromptGuardResult.status === "blocked"
          ? sharedPromptGuardResult.payload
          : null;
```

Add the import:

```ts
import { SharedHookClient } from "../hooks/shared-hook-client.js";
```

- [ ] **Step 5: Run prompt-focused tests**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/scripts/__tests__/codex-native-hook.test.js --test-name-pattern "shared prompt guard|prompt through stdin"
```

Expected: PASS.

- [ ] **Step 6: Run Python stdin prompt contract**

Run:

```bash
pytest tests/contract/test_hook_cli_surface.py::test_validate_prompt_accepts_stdin_payload -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add extensions/agent-teams/engine/src/hooks/shared-hook-client.ts extensions/agent-teams/engine/src/scripts/codex-native-hook.ts extensions/agent-teams/engine/src/scripts/__tests__/codex-native-hook.test.ts
git commit -m "refactor: validate native prompts through stdin"
```

---

### Task 10: Extract SessionStart Handler

**Files:**
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/session-start.ts`
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`

- [ ] **Step 1: Create the handler module by moving existing functions**

Create `extensions/agent-teams/engine/src/scripts/native-hook/session-start.ts` with:

```ts
import type { CodexHookPayload } from "./context.js";

export interface SessionStartHandlerInput {
  cwd: string;
  payload: CodexHookPayload;
  canonicalSessionId: string;
  nativeSessionId: string;
  buildSessionStartContext: (cwd: string, sessionId: string) => Promise<string | null>;
  buildSharedCompactionArgs: (
    cwd: string,
    payload: CodexHookPayload,
    mode: "read" | "build",
  ) => Promise<string[] | null>;
  invokeSharedQualityHook: (
    args: string[],
    options: { cwd: string },
  ) => { warnings?: string[]; actions?: string[]; data?: Record<string, unknown> } | null;
  appendSharedHookContext: (
    existing: string | null,
    payload: { warnings?: string[]; actions?: string[]; data?: Record<string, unknown> } | null,
  ) => string | null;
}

export async function handleSessionStart(input: SessionStartHandlerInput): Promise<Record<string, unknown> | null> {
  const additionalContextBase = await input.buildSessionStartContext(
    input.cwd,
    input.canonicalSessionId || input.nativeSessionId,
  );
  const sharedCompactionArgs = await input.buildSharedCompactionArgs(input.cwd, input.payload, "build");
  const sharedCompactionPayload = sharedCompactionArgs
    ? input.invokeSharedQualityHook(sharedCompactionArgs, { cwd: input.cwd })
    : null;
  const additionalContext = input.appendSharedHookContext(additionalContextBase, sharedCompactionPayload);
  if (!additionalContext) return null;
  return {
    hookSpecificOutput: {
      hookEventName: "SessionStart",
      additionalContext,
    },
  };
}
```

- [ ] **Step 2: Replace SessionStart output branch with handler call**

In `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`, import:

```ts
import { handleSessionStart } from "./native-hook/session-start.js";
```

In the `if (hookEventName === "SessionStart" || hookEventName === "UserPromptSubmit")` block, replace only the `SessionStart` path with:

```ts
    if (hookEventName === "SessionStart") {
      outputJson = await handleSessionStart({
        cwd,
        payload,
        canonicalSessionId,
        nativeSessionId,
        buildSessionStartContext,
        buildSharedCompactionArgs,
        invokeSharedQualityHook,
        appendSharedHookContext,
      });
    } else {
      const additionalContextBase =
        buildAdditionalContextMessage(readPromptText(payload), skillState, cwd, payload) ?? triageAdditionalContext;
      const additionalContext = appendSharedHookContext(
        appendSharedHookContext(additionalContextBase, sharedPromptGuardPayload),
        sharedWorkflowPolicyPayload,
      );
      if (sharedPromptGuardOutput) {
        outputJson = sharedPromptGuardOutput;
        if (additionalContext) {
          const currentAdditionalContext = readHookSpecificAdditionalContext(outputJson);
          outputJson = {
            ...outputJson,
            hookSpecificOutput: {
              ...(outputJson.hookSpecificOutput as Record<string, unknown> | undefined ?? {}),
              hookEventName,
              additionalContext: [currentAdditionalContext, additionalContext].filter(Boolean).join(" "),
            },
          };
        }
      } else if (additionalContext) {
        outputJson = {
          hookSpecificOutput: {
            hookEventName,
            additionalContext,
          },
        };
      }
    }
```

- [ ] **Step 3: Run SessionStart tests**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/scripts/__tests__/codex-native-hook.test.js --test-name-pattern "SessionStart|session"
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add extensions/agent-teams/engine/src/scripts/native-hook/session-start.ts extensions/agent-teams/engine/src/scripts/codex-native-hook.ts
git commit -m "refactor: extract codex session start handler"
```

---

### Task 11: Extract UserPromptSubmit Handler

**Files:**
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/user-prompt.ts`
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`

- [ ] **Step 1: Create user prompt handler interface**

Create `extensions/agent-teams/engine/src/scripts/native-hook/user-prompt.ts`:

```ts
import type { CodexHookPayload } from "./context.js";

export interface UserPromptHandlerInput {
  cwd: string;
  payload: CodexHookPayload;
  hookEventName: "UserPromptSubmit";
  prompt: string;
  skillState: unknown;
  triageAdditionalContext: string | null;
  sharedPromptGuardOutput: Record<string, unknown> | null;
  sharedPromptGuardPayload: Record<string, unknown> | null;
  sharedWorkflowPolicyPayload: Record<string, unknown> | null;
  buildAdditionalContextMessage: (
    prompt: string,
    skillState: unknown,
    cwd: string,
    payload: CodexHookPayload,
  ) => string | null;
  appendSharedHookContext: (
    existing: string | null,
    payload: Record<string, unknown> | null,
  ) => string | null;
  readHookSpecificAdditionalContext: (outputJson: Record<string, unknown> | null) => string;
}

export function handleUserPromptSubmit(input: UserPromptHandlerInput): Record<string, unknown> | null {
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
```

- [ ] **Step 2: Replace output merge branch with handler call**

In `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`, import:

```ts
import { handleUserPromptSubmit } from "./native-hook/user-prompt.js";
```

Replace the `UserPromptSubmit` output branch from Task 10 with:

```ts
    } else {
      outputJson = handleUserPromptSubmit({
        cwd,
        payload,
        hookEventName,
        prompt: readPromptText(payload),
        skillState,
        triageAdditionalContext,
        sharedPromptGuardOutput,
        sharedPromptGuardPayload,
        sharedWorkflowPolicyPayload,
        buildAdditionalContextMessage,
        appendSharedHookContext,
        readHookSpecificAdditionalContext,
      });
    }
```

- [ ] **Step 3: Run prompt routing tests**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/scripts/__tests__/codex-native-hook.test.js --test-name-pattern "UserPromptSubmit|triage|prompt"
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add extensions/agent-teams/engine/src/scripts/native-hook/user-prompt.ts extensions/agent-teams/engine/src/scripts/codex-native-hook.ts
git commit -m "refactor: extract codex user prompt output handler"
```

---

### Task 12: Extract Stop Output Merge Shell

**Files:**
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/stop.ts`
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`

- [ ] **Step 1: Create Stop merge handler**

Create `extensions/agent-teams/engine/src/scripts/native-hook/stop.ts`:

```ts
import type { CodexHookPayload } from "./context.js";

export interface StopHandlerInput {
  cwd: string;
  payload: CodexHookPayload;
  baseOutput: Record<string, unknown> | null;
  buildSharedStopMonitorArgs: (payload: CodexHookPayload) => string[] | null;
  invokeSharedQualityHook: (args: string[], options: { cwd: string }) => Record<string, unknown> | null;
  mergeSharedStopMonitorOutput: (
    currentOutput: Record<string, unknown> | null,
    sharedMonitorPayload: Record<string, unknown> | null,
  ) => Record<string, unknown> | null;
  buildSharedCompactionArgs: (
    cwd: string,
    payload: CodexHookPayload,
    mode: "read" | "build",
  ) => Promise<string[] | null>;
  appendSharedHookContext: (
    existing: string | null,
    payload: Record<string, unknown> | null,
  ) => string | null;
  readHookSpecificAdditionalContext: (outputJson: Record<string, unknown> | null) => string;
  withHookSpecificAdditionalContext: (
    outputJson: Record<string, unknown> | null,
    hookEventName: string,
    additionalContext: string,
  ) => Record<string, unknown>;
  buildSharedLearningSignalArgs: (cwd: string, payload: CodexHookPayload) => Promise<string[] | null>;
  mergeSharedLearningSignalOutput: (
    currentOutput: Record<string, unknown> | null,
    hookEventName: "PostToolUse" | "Stop",
    sharedLearningPayload: Record<string, unknown> | null,
  ) => Record<string, unknown> | null;
}

export async function mergeStopSharedOutputs(input: StopHandlerInput): Promise<Record<string, unknown> | null> {
  let outputJson = input.baseOutput;

  const sharedStopMonitorArgs = input.buildSharedStopMonitorArgs(input.payload);
  if (sharedStopMonitorArgs) {
    const sharedStopMonitorPayload = input.invokeSharedQualityHook(sharedStopMonitorArgs, { cwd: input.cwd });
    outputJson = input.mergeSharedStopMonitorOutput(outputJson, sharedStopMonitorPayload);
  }

  const sharedCompactionArgs = await input.buildSharedCompactionArgs(input.cwd, input.payload, "build");
  if (sharedCompactionArgs) {
    const sharedCompactionPayload = input.invokeSharedQualityHook(sharedCompactionArgs, { cwd: input.cwd });
    const mergedContext = input.appendSharedHookContext(
      input.readHookSpecificAdditionalContext(outputJson) || null,
      sharedCompactionPayload,
    );
    if (mergedContext) {
      outputJson = input.withHookSpecificAdditionalContext(outputJson, "Stop", mergedContext);
    }
  }

  const sharedLearningSignalArgs = await input.buildSharedLearningSignalArgs(input.cwd, input.payload);
  if (sharedLearningSignalArgs) {
    const sharedLearningSignalPayload = input.invokeSharedQualityHook(sharedLearningSignalArgs, { cwd: input.cwd });
    outputJson = input.mergeSharedLearningSignalOutput(outputJson, "Stop", sharedLearningSignalPayload);
  }

  return outputJson;
}
```

- [ ] **Step 2: Replace Stop shared merge branch**

In `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`, import:

```ts
import { mergeStopSharedOutputs } from "./native-hook/stop.js";
```

Replace the Stop branch after `buildStopHookOutput` with:

```ts
  } else if (hookEventName === "Stop") {
    outputJson = await mergeStopSharedOutputs({
      cwd,
      payload,
      baseOutput: await buildStopHookOutput(payload, cwd, stateDir),
      buildSharedStopMonitorArgs,
      invokeSharedQualityHook,
      mergeSharedStopMonitorOutput,
      buildSharedCompactionArgs,
      appendSharedHookContext,
      readHookSpecificAdditionalContext,
      withHookSpecificAdditionalContext,
      buildSharedLearningSignalArgs,
      mergeSharedLearningSignalOutput,
    });
  }
```

- [ ] **Step 3: Run Stop tests**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/scripts/__tests__/codex-native-hook.test.js --test-name-pattern "Stop|stop"
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add extensions/agent-teams/engine/src/scripts/native-hook/stop.ts extensions/agent-teams/engine/src/scripts/codex-native-hook.ts
git commit -m "refactor: extract codex stop shared output merge"
```

---

### Task 13: Move Dispatcher Out Of The CLI Entrypoint

**Files:**
- Create: `extensions/agent-teams/engine/src/scripts/native-hook/dispatcher.ts`
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`

- [ ] **Step 1: Record current public exports**

Run:

```bash
rg -n "export (async function|function)" extensions/agent-teams/engine/src/scripts/codex-native-hook.ts
```

Expected output includes:

```text
export function mapCodexHookEventToOmxEvent
export async function dispatchCodexNativeHook
export function isCodexNativeHookMainModule
export async function runCodexNativeHookCli
```

- [ ] **Step 2: Create dispatcher module with moved runtime logic**

Create `extensions/agent-teams/engine/src/scripts/native-hook/dispatcher.ts` by moving these declarations out of `codex-native-hook.ts`:

```text
CodexHookEventName
CodexHookPayload
NativeHookDispatchOptions
NativeHookDispatchResult
readHookEventName
mapCodexHookEventToOmxEvent
dispatchCodexNativeHook
```

Also move the private helper declarations that `dispatchCodexNativeHook` references. Keep CLI-only declarations in `codex-native-hook.ts`:

```text
NativeHookCliReadResult
isCodexNativeHookMainModule
readStdinJson
runCodexNativeHookCli
main-module guard
```

The top of `dispatcher.ts` must import the modules currently used by the moved helpers. Keep relative paths equivalent to the new `native-hook/` directory. For example:

```ts
import { mkdir, readFile, readdir, writeFile } from "fs/promises";
import { existsSync, readFileSync, statSync } from "fs";
import { join, resolve } from "path";
import { createHash } from "node:crypto";
import { readModeState, readModeStateForSession, updateModeState } from "../../modes/base.js";
import {
  buildNativePostToolUseOutput,
  buildNativePreToolUseOutput,
  detectMcpTransportFailure,
} from "../codex-native-pre-post.js";
```

Use TypeScript compiler errors after the first move to identify any missed private helper imports. Do not change helper bodies while moving them.

- [ ] **Step 3: Re-export dispatcher functions from the CLI file**

At the top of `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`, add:

```ts
export {
  dispatchCodexNativeHook,
  mapCodexHookEventToOmxEvent,
  type NativeHookDispatchOptions,
  type NativeHookDispatchResult,
} from "./native-hook/dispatcher.js";

import { dispatchCodexNativeHook } from "./native-hook/dispatcher.js";
```

After the move, `codex-native-hook.ts` should keep only:

```ts
import { pathToFileURL } from "url";

export {
  dispatchCodexNativeHook,
  mapCodexHookEventToOmxEvent,
  type NativeHookDispatchOptions,
  type NativeHookDispatchResult,
} from "./native-hook/dispatcher.js";

import { dispatchCodexNativeHook } from "./native-hook/dispatcher.js";

interface NativeHookCliReadResult {
  payload: Record<string, unknown>;
  parseError: Error | null;
}

export function isCodexNativeHookMainModule(
  moduleUrl: string,
  argv1: string | undefined,
): boolean {
  if (!argv1) return false;
  return moduleUrl === pathToFileURL(argv1).href;
}

async function readStdinJson(): Promise<NativeHookCliReadResult> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(String(chunk)));
  }
  const raw = Buffer.concat(chunks).toString("utf-8").trim();
  if (!raw) {
    return { payload: {}, parseError: null };
  }

  try {
    return {
      payload: JSON.parse(raw) as Record<string, unknown>,
      parseError: null,
    };
  } catch (error) {
    return {
      payload: {},
      parseError: error instanceof Error ? error : new Error(String(error)),
    };
  }
}

export async function runCodexNativeHookCli(): Promise<void> {
  const { payload, parseError } = await readStdinJson();
  if (parseError) {
    process.stdout.write(`${JSON.stringify({
      decision: "block",
      reason: "OMX native hook received malformed JSON input. Preserve runtime state, inspect the emitting hook payload yourself, and retry with valid JSON.",
      hookSpecificOutput: {
        hookEventName: "Unknown",
        additionalContext:
          `stdin JSON parsing failed inside codex-native-hook: ${parseError.message}. Emit valid JSON from the native hook caller before retrying.`,
      },
    })}\n`);
    return;
  }

  const result = await dispatchCodexNativeHook(payload);
  if (result.outputJson) {
    process.stdout.write(`${JSON.stringify(result.outputJson)}\n`);
  }
}

if (isCodexNativeHookMainModule(import.meta.url, process.argv[1])) {
  runCodexNativeHookCli().catch((error) => {
    process.stderr.write(
      `[omx] codex-native-hook failed: ${
        error instanceof Error ? error.message : String(error)
      }\n`,
    );
    process.exitCode = 1;
  });
}
```

- [ ] **Step 4: Run compiler and public import tests**

Run:

```bash
cd extensions/agent-teams/engine
npm run build
node --test dist/scripts/__tests__/codex-native-hook.test.js --test-name-pattern "main module|maps Codex events|malformed"
```

Expected: PASS.

- [ ] **Step 5: Run full native hook tests**

Run:

```bash
cd extensions/agent-teams/engine
npm run test:native-hooks
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add extensions/agent-teams/engine/src/scripts/native-hook/dispatcher.ts extensions/agent-teams/engine/src/scripts/codex-native-hook.ts
git commit -m "refactor: move codex native dispatch out of cli"
```

---

### Task 14: Run Full Native Hook Verification And Fix Import Drift

**Files:**
- Modify only files touched by previous tasks if verification exposes import or type drift.

- [ ] **Step 1: Run full native hook test entrypoint**

Run:

```bash
cd extensions/agent-teams/engine
npm run test:native-hooks
```

Expected: PASS.

- [ ] **Step 2: Run Python hook compatibility tests**

Run from repo root:

```bash
pytest tests/contract/test_hook_cli_surface.py tests/codex_team/test_sync_ecc_to_codex_scripts.py -q
```

Expected: PASS.

- [ ] **Step 3: Run Codex integration tests if Codex integration files changed**

Run this command only if the implementation changed `src/specify_cli/integrations/codex/**`, `.codex` generation behavior, or `src/specify_cli/launcher.py`:

```bash
pytest tests/integrations/test_integration_codex.py tests/integrations/test_integration_subcommand.py -q
```

Expected: PASS or SKIP for environment-specific tool checks.

- [ ] **Step 4: Inspect final diff**

Run:

```bash
git diff --stat
git diff -- extensions/agent-teams/engine/src src/specify_cli/__init__.py tests/contract/test_hook_cli_surface.py
```

Expected: diff shows structural extraction, new tests, stdin prompt support, and no `.codex/hooks.json` generation change.

- [ ] **Step 5: Commit final verification fixes**

If Step 1 or Step 2 required small import/type fixes, commit them:

```bash
git add extensions/agent-teams/engine/src src/specify_cli/__init__.py tests/contract/test_hook_cli_surface.py
git commit -m "test: verify codex native hook control plane"
```

If there were no fixes, skip this commit.

---

## Self-Review

Spec coverage:

- SharedHookClient typed result contract: Task 2.
- Timeout/unavailable/invalid-output behavior: Task 2.
- Prompt text migration away from argv: Tasks 1 and 9.
- Effects/services boundary: Tasks 4 and 7.
- Outcome precedence and Stop metadata: Task 3.
- Event extraction: Tasks 8, 10, 11, 12, and 13.
- Verification command alignment: Task 14.

Placeholder scan:

- This plan contains concrete file paths, commands, expected outcomes, and code snippets for each implementation task.
- No implementation task depends on an undefined function without introducing it in the same or an earlier task.

Type consistency:

- `CodexHookEventName` is introduced in `outcome.ts` and reused by context/effects/client code.
- `SharedQualityHookPayload` is owned by `shared-hook-client.ts` and re-exported from `specify-quality-adapter.ts`.
- `NativeHookEffectRecorder` is introduced before `NativeHookServices` consumes it.
