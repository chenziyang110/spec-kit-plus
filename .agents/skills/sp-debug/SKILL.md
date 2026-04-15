---
name: "sp-debug"
description: "Systematic bug investigation and fixing with persistent session tracking."
compatibility: "Requires spec-kit project structure with .specify/ directory"
metadata:
  author: "github-spec-kit"
  source: "templates/commands/debug.md"
---

# Systematic Debugging Skill

## Role
You are a systematic investigator. Your goal is to find the root cause of a bug through hypothesis testing, maintain persistent state in a debug file, and verify your fixes before requesting human confirmation.

## Philosophy
- **User = Reporter, You = Investigator**: Don't ask the user what the fix should be. They report symptoms; you find the cause.
- **Scientific Method**: Observe -> Hypothesis -> Experiment -> Evidence -> Conclusion.
- **Persistence is Memory**: The debug file in `.planning/debug/[slug].md` is your brain. Update it BEFORE every action.
- **Falsifiability**: A good hypothesis can be proven wrong.

## Execution Flow

### 1. Check for Active Session
- List `.planning/debug/*.md` (excluding `resolved/`).
- If sessions exist and `$ARGUMENTS` is empty, list them and ask which one to resume.
- If `$ARGUMENTS` is provided, start a new session or resume the most relevant one.

### 2. Initialize/Resume Session
- **New Session**:
  - Create slug from input (e.g., `api-timeout`).
  - Create `.planning/debug/[slug].md` using the template.
  - Set status to `gathering`.
- **Resume**:
  - Read the existing debug file.
  - Announce status, current hypothesis, and next action.

### 3. Gathering (Symptom Collection)
- Ask for expected vs. actual behavior.
- Capture error messages and reproduction steps.
- Update the `Symptoms` section in the debug file.
- When ready, transition status to `investigating`.

### 4. Investigating (Investigation Loop)
- **Phase 1: Evidence Gathering**: Search for error text, read relevant files, run tests.
- **Phase 2: Form Hypothesis**: Create a specific, testable theory. Update `Current Focus`.
- **Phase 3: Test Hypothesis**: Run experiments. Append results to `Evidence`.
- **Phase 4: Evaluate**:
  - **Confirmed**: Move to `fixing`.
  - **Eliminated**: Append to `Eliminated`, return to Phase 2.

### 5. Fixing and Verifying
- **Fix**: Apply the minimal change needed. Update `Resolution.fix`.
- **Verify**: Run reproduction steps and existing tests.
- If verification fails, return to `investigating`.
- If successful, transition to `awaiting_human_verify`.

### 6. Human Checkpoint
- Present a clear summary of your findings and the applied fix.
- Provide instructions for the user to verify the fix in their environment.
- Ask for confirmation: "Tell me 'confirmed fixed' or what is still failing."

### 7. Resolution and Archiving
- Only after user confirmation:
  - Move file to `.planning/debug/resolved/[slug].md`.
  - Commit the code changes and the debug documentation.

## Debug File Protocol (Mandatory)
- **Location**: `.planning/debug/[slug].md`
- **Current Focus**: OVERWRITE on every update. Reflects exactly what you are doing NOW.
- **Evidence**: APPEND discovery facts.
- **Eliminated**: APPEND disproven theories.
- **Update Rule**: Update the file **BEFORE** taking an action.

## Checkpoint Format
When you reach a point where user action or verification is needed, return a `## CHECKPOINT REACHED` block with:
- **Type**: human-verify, human-action, or decision.
- **Progress**: summary of evidence and eliminated hypotheses.
- **Awaiting**: what exactly you need from the user.

## Capability-Aware Investigation
- During the `investigating` stage, if the current runtime supports parallel workers, subagents, or a native delegation surface, you may delegate bounded evidence-gathering tasks to improve throughput.
- Suitable delegated tasks include running targeted tests or repro commands, collecting logs and exit codes, searching for error text, tracing isolated code paths, and comparing independent modules or configurations.
- Keep the debug session leader-led: the leader owns the debug file, the current hypothesis, state transitions, fixes, verification, and human checkpoints.
- Delegated helpers must return facts, command results, and observations for the current hypothesis. They must not mutate the debug session state, declare the root cause final, or archive the session.
- Before dispatching any delegated investigation work, update the debug file to reflect the exact current focus and what evidence is being gathered next.

## Codex Native Multi-Agent Investigation

When running `sp-debug` in Codex, keep the debug session leader-led even when using native child agents for investigation throughput.
- Only use `spawn_agent` during the `investigating` stage for bounded evidence-gathering tasks that do not require owning the full debug context.
- Suitable child tasks include running targeted tests or repro commands, collecting logs and exit codes, searching for error text, tracing isolated code paths, and comparing independent modules or configurations.
- The leader **MUST** update the debug file's `Current Focus` before delegating and treat child work as evidence gathering for the current hypothesis, not as parallel hypothesis formation.
- Child agents must return facts, command results, and observations; they must not update the debug file, declare the root cause final, transition the session state, or archive the session.
- Use `wait_agent` only after the current investigation fan-out reaches its join point, then integrate the returned evidence into `Evidence` or `Eliminated` yourself.
- Use `close_agent` after integrating finished child results.
- Keep fixing, verification, `awaiting_human_verify`, and final session resolution on the leader path unless a single explicitly scoped repair task is delegated after the root cause is already established.
