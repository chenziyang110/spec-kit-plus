{{spec-kit-include: ../common/user-input.md}}

## Objective

Answer project questions with evidence-backed, read-only project Q&A.

## Context

- Primary inputs: the user's project question, project memory, generated state, docs, templates, live files, and project-cognition navigation output.
- Project cognition provides advisory navigation. Live evidence is authoritative.
- This workflow answers questions only; it does not create implementation, discussion, debug, or planning state.

## Process

- Classify the user's question.
- Use project cognition to find the smallest likely evidence set.
- Read only the live evidence needed to prove the answer.
- Answer directly, then recommend another workflow only when the user needs action.

## Output Contract

- Provide a read-only answer with conclusion, evidence, uncertainty, and next step when useful.
- State when the available evidence cannot prove the answer.
- Keep the response natural and concise for simple questions, with short sections only when complexity requires them.

## Guardrails

- Do not mutate project files, workflow state, generated state, docs, templates, or memory.
- Do not create `.specify/ask/` or any ask handoff.
- Do not run tests, builds, package managers, app servers, or project CLI commands.
- Do not invoke another `sp-*` workflow automatically.

## Evidence-Backed Project Q&A

You answer project questions. The user's question may be rough, partial, bilingual, or based on an incorrect assumption.

Use this command when the user wants to know something about the project before choosing an action workflow.

## Read-Only Boundary

This workflow is read-only.

- Do not edit source files, tests, templates, docs, configs, generated state, or memory.
- Do not create `.specify/ask/`.
- Do not write handoff files.
- Do not run tests.
- Do not run builds.
- Do not run package managers.
- Do not launch apps or servers.
- Do not execute project CLI commands.
- Do not invoke another `sp-*` workflow automatically.

Allowed operations are narrow file reads, `rg`, project memory reads, generated-state reads, docs/template reads, and project-cognition navigation.

## Default Navigation

Start with:

```text
{{specify-subcmd:project-cognition compass --intent ask --query="$ARGUMENTS" --format json}}
```

Treat project cognition as advisory navigation. Live evidence is authoritative.

Use `project-cognition query --intent ask` only after you build a semantic intake or query plan from the user's wording and the project vocabulary because the compass output or live evidence is ambiguous or has incomplete coverage. Stale or localization-sensitive results are examples that still require that ambiguity or incomplete-coverage reason.

```text
{{specify-subcmd:project-cognition query --intent ask --query-plan "<query_plan_json>" --format json}}
```

When shell quoting makes inline JSON brittle, write the planned object to a file and call `project-cognition query --intent ask --query-plan-file <path> --format json` instead.

Use `project-cognition lexicon --intent ask --mode catalog --format json` only when you need vocabulary candidates before writing the query plan.

## Question Classifier

Classify the question before answering:

- `fact`: where something is, what exists, what changed, what config is active.
- `how_to`: how a project workflow, tool, script, or integration should be used.
- `why`: why the project behaves or is designed a certain way.
- `difference`: compare two workflows, files, commands, integrations, or states.
- `impact`: what will be affected if a change is made.
- `status`: whether a feature, artifact, release, map, or state is ready.
- `recommendation`: choose the best next step, with evidence.
- `concept`: explain project terminology or architecture.
- `history`: explain prior decisions from project files, templates, docs, generated state, memory, or project cognition.
- `boundary`: decide which workflow should handle the user's actual need.

## Evidence Rules

- Use project cognition to choose likely files; verify claims with live reads.
- Prefer the smallest evidence set that can answer the question.
- Quote or cite file paths when they materially support the answer.
- If the evidence conflicts, say which source wins and why.
- If the answer cannot be proven from available evidence, say that directly.
- If the user's question names a downstream project path, first establish the target project root before making claims about that project.

## Answer Shape

Answer naturally. Use only as much structure as the question needs.

Default shape:

1. Answer first.
2. Evidence.
3. Uncertainty or caveat.
4. Next step only when useful.

For simple questions, one short paragraph is enough. For complex questions, use short sections with human-readable names, not rigid audit labels.

## Routing Guidance

If the answer reveals that the user needs action, recommend one next workflow without invoking it:

- Use `sp-discussion` for product/design/requirement shaping.
- Use `sp-specify` for confirmed feature requirements.
- Use `sp-quick` for small bounded code or docs changes.
- Use `sp-fast` for minimal low-risk execution.
- Use `sp-debug` for root-cause diagnosis.
- Use `sp-deep-research` for feasibility proof or external evidence.
- Use `sp-explain` for explaining a specific generated artifact or stage output.
- Use `sp-map-update`, `sp-map-scan`, or `sp-map-build` only when project-cognition freshness or coverage itself is the subject.

Do not ask the user to say "continue" when the answer and recommended next step can be delivered in one response.
