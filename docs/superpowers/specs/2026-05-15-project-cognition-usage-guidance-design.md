# Project Cognition Usage Guidance Design

**Date:** 2026-05-15  
**Status:** Draft for review  
**Scope:** Generated constitution guidance, generated agent context files, `sp-*`
workflow templates, and regression tests for project-cognition consumption
guidance.

## Summary

Project cognition is already present as a brownfield hard gate, but downstream
agents can still treat it as a one-time preflight instead of a working context
source. The next improvement should teach agents when project cognition is
mandatory and what it means to use it well.

The guidance should not make project cognition a universal ritual. It should
make it non-optional when work depends on existing-system truth: ownership,
architecture boundaries, existing behavior, state surfaces, integration points,
verification routes, task decomposition, or subagent dispatch.

The design uses three layers:

1. Constitution records the principle.
2. Generated agent context files record day-to-day usage scenarios and the
   required query consumption loop.
3. Workflow templates require project-cognition facts to be carried into the
   next artifact or execution state.

## Problem

The current system strongly says "query project cognition first" in generated
workflow templates and context files. That is necessary but not sufficient.

Agents may still fail in two ways:

- They skip project cognition during tasks that clearly depend on existing
  project structure.
- They run the query, then continue with broad source reads, unstated
  assumptions, or task packets that do not preserve the returned facts.

The missing instruction is not another refresh rule. The missing instruction is
an operational model:

- when project cognition is mandatory
- what the query result should control
- where the result must be carried forward
- when the runtime must be refreshed or marked dirty after changes

## Goals

- Make project-cognition usage mandatory for existing-system judgment.
- Teach agents concrete usage scenarios instead of only naming the command.
- Prevent "query as ceremony" by requiring returned facts to drive routing,
  first reads, artifacts, and execution state.
- Respect each integration's actual context file, such as `CLAUDE.md`,
  `GEMINI.md`, `AGENTS.md`, `.github/copilot-instructions.md`,
  `.cursor/rules/specify-rules.mdc`, and other generated agent guidance files,
  while deriving the complete target set from integration metadata and context
  update scripts instead of trusting a manually maintained list.
- Keep constitution guidance principle-level rather than CLI-procedural.
- Avoid encouraging agents to search for excuses to bypass project cognition.

## Non-Goals

- Do not redesign `project-cognition query` scoring, alias generation, or graph
  schema in this change.
- Do not make project cognition replace live code reads.
- Do not require project cognition for every possible textual or mechanical
  task.
- Do not collapse all generated agent context files into `AGENTS.md`; each
  integration keeps its own context surface.

## Proposed Design

### Constitution Principle

Generated constitution profiles should add a principle-level engineering rule:

```text
Project Cognition Before Existing-System Judgment: When work depends on
existing project truth, agents MUST query project cognition before broad source
inspection, planning, debugging, implementation, task decomposition, or
subagent dispatch. The query result MUST guide routing, minimal live reads,
boundary constraints, and verification strategy.
```

This belongs in the engineering standards layer, not in workflow mechanics.
It should establish the governance expectation without spelling out every CLI
state or command.

### Agent Context Files

Generated agent context files should include a `Project Cognition Usage`
section in the managed Spec Kit block. The implementation must first reconcile
the actual target files from:

- each integration's `Integration.context_file`
- the shared Bash and PowerShell `update-agent-context` target mappings
- integration-specific `scripts/update-context.*` wrappers
- tests that assert generated context-file locations

Do not manually trust a hard-coded list of files in this design document as the
source of truth. The list below is illustrative only:

- `CLAUDE.md`
- `GEMINI.md`
- `AGENTS.md`
- `.github/copilot-instructions.md`
- `.cursor/rules/specify-rules.mdc`
- `QWEN.md`
- `.windsurf/rules/specify-rules.md`
- `.roo/rules/specify-rules.md`
- `CODEBUDDY.md`
- `QODER.md`
- `KIMI.md`

Known current drift, such as Vibe and Trae context-file locations differing
between integration metadata and shared update scripts, must be resolved or
explicitly documented before implementation changes the managed context block.

The section should use the generic term "agent context files" in shared
documentation, not "AGENTS.md", because several supported CLIs use different
filenames.

The managed block should state that project cognition is mandatory when the
task depends on existing-system truth, including:

- changing existing functionality or behavior such as login, payment, routing,
  permissions, import/export, notifications, or background jobs
- judging module ownership, truth owners, architecture boundaries, reuse
  points, integration points, state surfaces, or consumer impact
- writing or updating `specify`, `plan`, or `tasks` outputs that must land in
  the current project structure
- running `implement` or `quick` work that touches existing code, tests,
  configuration, routes, protocols, data models, or workflows
- debugging symptoms that must map to existing capabilities, entrypoints, state
  surfaces, or test surfaces
- decomposing tasks, compiling task packets, or dispatching subagents that need
  read scope, write scope, required references, or validation commands
- choosing testing strategy, verification entry points, regression scope, or
  coverage-gap handling
- changing architecture boundaries, workflow contracts, integration contracts,
  ownership, or verification entry points
- closing out work that changed project-cognition truth and therefore requires
  a project-cognition refresh or dirty marker

For all other work, agents may decide based on risk, context cost, and the user
goal. The guidance should avoid listing bypass cases. The important rule is:
if the agent needs to know how this project is organized, implemented, or
verified, project cognition is mandatory.

### Query Consumption Loop

The managed agent context block should describe the required loop:

1. Query project cognition through the project launcher or generated command
   renderer before broad code inspection, planning, research, testing,
   debugging, or implementation:

   ```text
   project-cognition query --intent <workflow-intent> --query "<task summary>" --format json
   ```

   In generated workflow templates, use the launcher-backed renderer form, for
   example:

   ```text
   {{specify-subcmd:project-cognition query --intent <workflow-intent> --query "$ARGUMENTS" --format json}}
   ```

   Valid workflow intents include at least `plan`, `implement`, `debug`,
   `test`, and `research`. Future workflow-specific intents may be added without
   changing the usage model.

   When relevant paths are known from the user request or upstream artifacts,
   include them through `--paths`.

2. Use `readiness` for routing:

   - `ready`: continue with the task-local bundle.
   - `review`: inspect only the returned `minimal_live_reads` before trusting
     the runtime for task decisions.
   - `ambiguous`: ask the user or upstream artifact to select the intended
     candidate instead of silently choosing.
   - `needs_update`: route through the integration-neutral `sp-map-update`
     workflow entrypoint, rendered for the active agent.
   - `needs_rebuild`: route through the integration-neutral `sp-map-scan`, then
     `sp-map-build` workflow entrypoints, rendered for the active agent.
   - `blocked`: stop and report the runtime issue.

3. Extract working facts from the result:

   - matched capability or symptom
   - affected nodes and subgraph
   - `minimal_live_reads`
   - missing coverage
   - evidence traces
   - verification routes when present
   - ambiguity, conflicts, or weak coverage

4. Constrain the first live reads to `minimal_live_reads` plus directly relevant
   durable workflow artifacts. Only expand search when those reads do not answer
   the task.

5. Carry project-cognition facts into the next artifact or execution state.

6. Refresh or mark dirty when the change updates project-cognition truth.

The core rule should be explicit:

```text
A project-cognition query is not complete when it returns JSON. It is complete
only when readiness drives routing, minimal_live_reads constrains inspection,
and relevant facts are carried into the next workflow artifact or execution
state.
```

### Workflow Template Carry-Forward

Workflow templates should keep their existing hard gate language, but they
should also name the expected carry-forward target:

- `sp-specify`: write project-cognition ownership, affected surfaces, reusable
  assets, verification routes, and known unknowns into `context.md` and the
  brainstorming handoff where relevant.
- `sp-clarify`: use project-cognition facts to decide whether an apparent
  requirement gap is already answered by repository truth, and carry selected
  ownership, boundary, ambiguity, or verification facts into the clarified spec
  package.
- `sp-deep-research`: use project-cognition results as repository-grounded
  starting context, preserve cited capabilities, constraints, affected
  surfaces, and verification routes in `deep-research.md`, and distinguish
  repository facts from external research findings.
- `sp-plan`: promote project-cognition facts into planning constraints,
  `Implementation Constitution`, boundary rules, verification strategy, and
  `plan-contract.json` when applicable.
- `sp-tasks`: carry cognition-derived required references, write scopes,
  validation commands, forbidden drift, and known unknowns into `tasks.md`,
  `task-index.json`, and task packets.
- `sp-analyze`: preserve cognition-backed blocker evidence when classifying
  whether issues belong to `plan`, `clarify`, `deep-research`, or task-layer
  remediation.
- `sp-implement`: write the selected capability, minimal live reads, boundary
  constraints, required references, validation route, and evidence gaps into
  `implement-tracker.md` or the current `WorkerTaskPacket` before dispatch or
  code edits.
- `sp-debug`: write the selected capability or symptom, evidence routes,
  minimal reads, competing truths, and unresolved coverage gaps into debug
  session state before root-cause claims.
- `sp-fast`: use project-cognition signals to decide whether fast-path execution
  is still safe, and carry the selected capability, minimal reads, and
  verification route into the fast-task state or report.
- `sp-quick`: write the selected capability, minimal reads, validation route,
  and known risk into quick-task `STATUS.md` before implementation proceeds.
- `sp-test-scan` and `sp-test-build`: carry project-cognition testing-surface
  ownership, covered modules, verification nodes, coverage gaps, and required
  live reads into testing inventory and build-plan artifacts.

This change makes the workflow behavior "query and use" rather than only
"query first".

## Example

For a downstream request such as:

```text
After login succeeds, redirect users to the dashboard, but preserve returnUrl
when a protected route sent them to login.
```

The agent should query:

```text
{{specify-subcmd:project-cognition query --intent implement --query "login success redirect dashboard preserve return url" --format json}}
```

The agent then uses the result to identify the login capability, route guard or
redirect helper that owns post-login navigation, session or return-url state,
minimal files to read, and relevant login redirect tests. If the result is
ambiguous between normal login, admin SSO, or magic-link login, the agent asks
for candidate selection rather than editing a guessed component. If the result
is ready, the first source reads should be the returned `minimal_live_reads`,
not a broad repository search.

The resulting plan or task packet should say which redirect surface is the
truth owner, which existing helper must be preserved, which files are required
references, which validation command proves the behavior, and which drift is
forbidden, such as adding a second parallel redirect path inside a form
component when routing owns the behavior.

## Tests

Regression coverage should include:

- generated constitution profile guidance contains the project-cognition
  principle for existing-system judgment
- Bash and PowerShell managed context block renderers include the
  `Project Cognition Usage` scenario guidance
- implementation tests reconcile generated context-file targets from
  integration metadata and shared update-context scripts, including any Vibe or
  Trae location drift fixed by this work
- generated context guidance uses "agent context files" or equivalent neutral
  wording rather than implying every integration uses `AGENTS.md`
- generated context guidance names mandatory scenarios for existing-system
  truth, task decomposition, debugging, testing strategy, and closeout refresh
- generated context guidance states that query completion requires readiness
  routing, `minimal_live_reads` constrained inspection, and carry-forward into
  artifacts or execution state
- key workflow templates include carry-forward targets for `sp-specify`,
  `sp-clarify`, `sp-deep-research`, `sp-plan`, `sp-tasks`, `sp-analyze`,
  `sp-implement`, `sp-debug`, `sp-fast`, `sp-quick`, `sp-test-scan`, and
  `sp-test-build`
- existing tests that reject raw graph reads or legacy project-map runtime
  reliance continue to pass

## Success Criteria

- Downstream agents have a clear, integration-neutral usage model for project
  cognition.
- Existing-system work has an explicit constitution-backed rule requiring
  project cognition before broad guessing.
- Generated agent context files explain the scenarios that make project
  cognition mandatory.
- Workflow templates require cognition results to shape artifacts and execution
  state, not just preflight routing.
- The change does not make project cognition a universal ritual for unrelated
  mechanical tasks.
