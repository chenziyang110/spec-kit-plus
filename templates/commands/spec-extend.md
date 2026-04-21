---
description: Re-open the current specification, deepen weak analysis, and update spec artifacts through targeted enhancement.
handoffs:
  - label: Build Technical Plan
    agent: sp.plan
    prompt: Build the plan using the strengthened specification package.
    send: true
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

Goal: Strengthen an existing spec package after `/sp.specify` by closing planning-critical gaps, correcting misunderstandings, absorbing reference material better, and writing the improved results back into `spec.md`, `alignment.md`, and `references.md`.

1. Run `{SCRIPT}` from repo root once (`--json --paths-only` / `-Json -PathsOnly`). Parse:
   - `FEATURE_DIR`
   - `FEATURE_SPEC`
   - optional downstream paths if returned
   - If JSON parsing fails, abort and instruct the user to verify the feature branch environment.

2. Load the current spec package:
   - `FEATURE_SPEC`
   - `FEATURE_DIR/alignment.md` if present
   - `FEATURE_DIR/context.md` if present
   - `FEATURE_DIR/references.md` if present
   - relevant repository documentation and design artifacts when they materially affect the requested change

3. Identify what needs enhancement:
   - shallow or surface-level capability analysis
   - missing scenarios or usage paths
   - unresolved contradictions
   - underused reference material
   - newly provided requirements or constraints
   - unresolved gray areas that still change plan structure
   - missing locked decisions, canonical references, or deferred-scope notes
   - gaps that would make `/sp.plan` less reliable

4. Classify findings by severity:
   - high-impact gaps that require user confirmation
   - lower-risk gaps that can be improved directly from current context

5. When justified, use multi-agent research or analysis to deepen the spec:
   - parallelize only when the work naturally separates into independent research tracks
   - examples: external references, local codebase context, risk analysis, comparison of alternatives
   - keep the final output synthesized back into the main spec package instead of returning raw research noise

6. Apply enhancements directly to the artifact set:
   - update `spec.md`
   - update `alignment.md`
   - update `context.md`
   - update `references.md`
   - strengthen `Locked Decisions`, `Claude Discretion`, `Canonical References`, and `Deferred / Future Ideas` in `spec.md` when relevant
   - strengthen `Locked Decisions For Planning`, `Outstanding Questions`, and `Planning Gate Recommendation` in `alignment.md`
   - strengthen `Locked Decisions`, `Claude Discretion`, `Canonical References`, `Existing Code Insights`, `Specific User Signals`, and `Outstanding Questions` in `context.md`

7. Maintain a clean output contract:
   - preserve confirmed facts
   - expand low-risk inferences only when they are useful for planning
   - clearly identify what remains unresolved
   - do not imply the spec package is planning-ready if planning-critical gaps still remain

8. Report completion with:
   - sections touched
   - whether multi-agent research was used
   - updated paths
   - remaining planning risks
   - recommended next command
   - whether the spec package is now ready for `/sp.plan` or still needs more clarification
   - whether another `/sp.specify` or `/sp.spec-extend` pass is still justified before planning

## Output Contract

When communicating findings and completion, use a structured terminal presentation built from open blocks with:

- a stage header that identifies `SPEC-EXTEND` and the current enhancement state
- a status block that summarizes whether the spec package was strengthened, partially strengthened, or is waiting on user confirmation
- an explanation block that explains what changed, which planning-critical gaps were reduced, and why it matters for planning
- a risk block that lists unresolved planning risks, remaining contradictions, or evidence gaps
- a next-step block that gives the recommended next command and whether more enhancement work is still needed before `/sp.plan`
- when the package is still not planning-ready, the next-step block must avoid implying an automatic handoff to `/sp.plan`

## Rules

- Use the user's current language for user-visible output unless literal command names, file paths, or fixed status values must remain unchanged.
- Do not re-run the entire `specify` flow from scratch unless the current spec is unusably wrong.
- Prefer targeted enhancement over full restatement.
- If new information materially changes scope or alignment, update `alignment.md` in the same pass.
- Treat `/sp.spec-extend` as the default rescue lane when planning-critical ambiguity remains after `/sp.specify`.
- If high-impact ambiguity remains after enhancement, recommend another clarification pass instead of implying that `/sp.plan` is now safe.
