{{spec-kit-include: ../common/user-input.md}}

## Objective

Translate the approved specification package into explicit implementation design artifacts, research findings, and execution guidance that can safely feed task generation.

## Context

- Primary input: canonical `spec-contract.json` queried through targeted `specify-runtime artifact show` calls, including its context capsule, evidence refs, protected decisions, acceptance criteria, and `semantic_delta`. Query project-facing spec views through the same owner; open passive memory through its CLI and live repository files only when a required reference or stale condition calls for them.
- Working truth lives in agent-only `plan-contract.json`; `plan.md` is the project-facing view. `research.md`, `data-model.md`, `contracts/`, and `quickstart.md` are conditional evidence or design artifacts, while workflow and lane files are resume/dispatch state rather than duplicated handoffs.
- This command is design-only. Planning does not grant permission to start execution.

## Process

- Recover the active feature context and validate that the specification package is ready for planning.
- If `FEATURE_DIR` is not explicit, run `{{specify-subcmd:specify-runtime lane resolve --command plan --ensure-worktree}}`; honor a materialized worktree and stop on `uncertain` instead of guessing from branch state.
- Validate `/status: planning-ready` and the source revision from the `artifact show` response. Do not revalidate the original discussion contract unless the revision changed or the spec contract reports a semantic or evidence delta.
- Stop when the spec contract is not planning-ready, its context capsule lacks the required target boundary, hard unknowns remain open, or conflicts remain open.
- For cross-project implementation, plan from the target project context and record that current project cognition cannot prove target-project implementation facts.
- Use target cognition, minimal live reads in the target, user confirmation, or explicit assumptions for target evidence; do not ask the user to rebuild current-project cognition for target files.
- Refresh or inspect repository navigation artifacts until task-relevant coverage is sufficient.
- Research only unresolved implementation-shaping questions; reuse verified choices and evidence already carried by the context capsule.
- Design every carried `CA-###` consequence obligation into operational behavior, dependency impact, recovery/validation proof, and stop-and-reopen conditions before task handoff.
- Validate the resulting plan package before handing off to task generation.

## Output Contract

- Write the minimum sufficient implementation plan artifact set needed by `/sp-tasks`.
- If `plan-contract.json` is absent, create its fixed shape with `artifact scaffold --kind plan-contract`; otherwise query it with `artifact show`. Mutate only targeted fields through fresh leased JSON-pointer `artifact patch` calls; never submit or reconstruct the whole contract.
- For UI-bearing work, preserve the exact approved visual reference,
  preview/manifest/handoff SHA-256 values, immutable handoff reference, design
  decision IDs, handoff contract IDs, component contracts, color modes,
  responsive and motion contracts, viewport/state acceptance matrix,
  comparison tolerance, and accepted deviations from `spec-contract.json` into
  `ui_design_contract`. Planning may select the task-relevant `DS-*` and `DH-*`
  subsets and assign them to implementation owners, but may not summarize,
  rename, restate, or weaken their structured values.
- When delegated planning lanes are used, scaffold the compact planning lane manifest, replace its bounded `/lanes` array through fresh leased JSON-pointer patches at material joins, and submit each required result inline through `specify-runtime result submit`; the runtime owns all result paths. Do not submit the manifest wholesale or create evidence indexes/checkpoint logs for leader-inline work.
- Query every accepted planning handoff through `specify-runtime artifact show` before final synthesis; integrate it into `plan.md`, `research.md`, `quickstart.md`, `data-model.md`, `contracts/`, or `plan-contract.json` only through the registered artifact CLI, or patch a complete user-confirmed deferral contract or blocker with its reason.
- Surface risks, unresolved decisions, and planning-time constitution/guardrail requirements explicitly.
- Keep the resulting artifact set consistent enough that task generation does not need to rediscover obvious design decisions.

## Guardrails

- Do not implement code, edit tests, or start execution from `sp-plan`.
- Do not leave locked planning decisions implicit or scattered only in prose.
- Do not trust stale navigation coverage as evidence; use the carried context capsule or the single optional compass intake as advisory navigation and prove claims from live project facts.
- Use anchorable section headings (`## Section Name`) in all output artifacts so that downstream task generation can produce precise `file#section` context pointers.
