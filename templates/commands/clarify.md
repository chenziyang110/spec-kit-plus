---
description: Compatibility bridge for users who still run clarify; route requirement-extension work to spec-extend while preserving alignment updates.
handoffs:
  - label: Extend Spec Package
    agent: sp.spec-extend
    prompt: Deepen and realign the current requirement package
    send: true
  - label: Build Technical Plan
    agent: sp.plan
    prompt: Create a plan for the spec. I am building with...
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --paths-only
  ps: scripts/powershell/check-prerequisites.ps1 -Json -PathsOnly
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

Goal: Preserve existing `/sp.clarify` users during migration by acting as a compatibility bridge. Route to `/sp.spec-extend` for deeper requirement extension, misalignment repair, or evidence refresh, while still preserving alignment updates for users who invoked `/sp.clarify`.

Note: This is not the main path anymore. `/sp.specify` should already have completed deep requirement analysis. Use `/sp.clarify` mainly for backward compatibility, small follow-up corrections, or users who explicitly invoke it. When requirements materially change, recommend `/sp.spec-extend` before `/sp.plan`.

Execution steps:

1. Run `{SCRIPT}` from repo root once (`--json --paths-only` / `-Json -PathsOnly`). Parse:
   - `FEATURE_DIR`
   - `FEATURE_SPEC`
   - If JSON parsing fails, abort and instruct the user to re-run `/sp.specify` or verify the feature branch environment.

2. Load the current requirement package:
   - Read `FEATURE_SPEC`
   - Read `FEATURE_DIR/alignment.md` if present
   - Read `FEATURE_DIR/references.md` if present
   - If the spec file is missing, instruct the user to run `/sp.specify` first.

3. Decide whether this should become `/sp.spec-extend`.
   - Recommend `/sp.spec-extend` when the user is really asking for deeper analysis, requirement extension, misalignment repair, new evidence capture, or broader planning-readiness review.
   - If the environment supports agent handoff, route to `sp.spec-extend`.
   - If the user still wants `/sp.clarify` to continue, preserve compatibility and continue with a narrowed clarification pass.

4. Run a compatibility clarification scan against the current artifacts.
   - Check for underspecified scope, user roles, data shape, edge cases, and acceptance-test shaping detail.
   - Check for contradictions between `spec.md`, `alignment.md`, and newly provided requirements or constraints.
   - Prefer only high-impact clarification that materially affects planning.

5. Generate an internal prioritized queue of candidate clarification questions.
   - Ask at least 5 questions only when a full clarification pass is still justified.
   - Skip questions that `/sp.specify` already resolved clearly.
   - Focus on ambiguity that changes architecture, capability boundaries, test design, compliance posture, or release readiness.

6. Sequential questioning loop:
   - Present exactly one question at a time.
   - Prefer concise multiple-choice answers when useful.
   - Allow the user to provide new requirements, new constraints, corrections, or scope changes.
   - Use the user's current language for all user-visible clarification content.
   - Keep turns concise and avoid restating the full understanding after every answer.

7. Integration after each accepted answer:
   - Update the spec in memory and on disk.
   - Update `alignment.md` in parallel. If it does not exist, create it using the current best understanding.
   - Apply each answer to the most appropriate section without reordering unrelated content.
   - Record adding newly provided requirements or constraints in both artifacts.

8. Validation after each write plus final pass:
   - Clarification summary is updated without duplication.
   - No contradictory earlier statement remains.
   - Markdown structure stays valid.
   - Terminology stays consistent.

9. Update the alignment decision before reporting:
   - Use `Aligned: ready for plan` only when no unresolved high-impact ambiguity remains.
   - Use `Force proceed with known risks` if unresolved high-impact ambiguity remains and the user explicitly wants to continue.
   - Record new requirements, constraints, or corrections in both the spec and `alignment.md`.

10. Write the updated spec back to `FEATURE_SPEC` and write the updated alignment report to `FEATURE_DIR/alignment.md`.

11. Report completion:
   - Number of questions asked and answered
   - Path to updated spec
   - Path to updated alignment report
   - Sections touched
   - Coverage summary table with Status: Resolved / Deferred / Clear / Outstanding
   - Alignment decision: `Aligned: ready for plan` or `Force proceed with known risks`
   - recommended next command: `/sp.spec-extend` when deeper requirement work is still needed, otherwise `/sp.plan`

## Behavior rules

- This is a compatibility bridge, not the main path.
- If the user has already terminated clarification explicitly, stop and report the current state.
- If the spec file is missing, instruct the user to run `/sp.specify` first.
- Recommend or redirect to `/sp.spec-extend` whenever the request is broader than a narrow compatibility clarification.
- Clarification retries for a single question do not count as new questions.
- Respect user early termination signals such as "stop", "done", or "proceed".
- Use this command to add newly provided requirements or constraints, not just to answer old questions.
- Match the user's current language for all user-visible output unless a literal command name, file path, or fixed status value must remain unchanged.

Context for prioritization: {ARGS}
