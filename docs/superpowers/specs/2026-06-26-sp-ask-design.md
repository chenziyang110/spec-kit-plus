# sp-ask Design

**Date:** 2026-06-26
**Status:** Proposed
**Owner:** Codex

## Summary

Add `sp-ask` as an independent project question-answering workflow.

`sp-ask` is the entrypoint users invoke when they want to ask anything about the
project and get a clear, evidence-backed answer. It is not a lightweight
`sp-discussion`, not a debug workflow, and not a source-editing shortcut.

The core rule is:

> Project cognition finds the right area; live project evidence decides the answer.

The workflow should accept natural, colloquial user questions and return answers
that make the user feel oriented: what the answer is, why it is true, what remains
uncertain, and what to do next if action is needed.

## Problem Statement

Users often need to understand a project before they know which workflow to run.
Today the available workflows are strong, but each implies a heavier intent:

- `sp-discussion` shapes uncertain ideas into requirements and handoffs.
- `sp-specify` creates formal specifications.
- `sp-quick` executes bounded implementation work.
- `sp-debug` investigates defects.
- `sp-explain` explains existing workflow artifacts.
- `sp-auto` resumes from durable state.

There is no explicit project-wide "ask anything" entrypoint.

As a result, users either ask inside a workflow that is too heavy for the question
or rely on ordinary chat, where the agent may answer from memory or vague search
instead of grounding the answer in the project.

`sp-ask` should close that gap.

## Goals

- Let users ask any project question in natural language.
- Recognize what kind of answer the user needs before answering.
- Use project cognition as advisory navigation to find likely concepts, files,
  commands, templates, learnings, and workflows.
- Treat live project evidence as the authority for facts.
- Give concise answers by default and expand only when the question requires it.
- Make the answer satisfying to a human: direct, grounded, honest about uncertainty,
  and useful for deciding the next step.
- Route action-oriented follow-ups to the right workflow instead of silently doing
  implementation work.
- Work across generated integrations as an independent `sp-*` command or skill.

## Non-Goals

- Do not edit source code, tests, templates, docs, or configuration.
- Do not create feature branches or feature directories.
- Do not write `spec.md`, `plan.md`, `tasks.md`, quick-task state, debug sessions,
  discussion handoffs, or implementation artifacts.
- Do not create `.specify/ask/` sessions in v1.
- Do not maintain long-running ask state in v1.
- Do not replace `sp-discussion` for requirement shaping.
- Do not replace `sp-debug` for root-cause investigation.
- Do not replace `sp-deep-research` for external feasibility research.
- Do not treat project cognition output as proof of current behavior.

## User Experience

The user should be able to ask questions such as:

- "Where is this workflow defined?"
- "Why does H5 behave differently from the client?"
- "Is this state normal?"
- "What does this field mean?"
- "If we change this template, what else is affected?"
- "Which workflow should I use for this?"
- "How do I use project cognition here?"
- "What is the difference between `sp-quick` and `sp-fast`?"
- "Does this generated project already support that?"

The answer should usually start with the conclusion. It should not begin with
workflow bookkeeping, raw project-cognition output, or a long evidence dump.

For simple questions, one paragraph may be enough. For complex questions, the answer
should naturally expand into a small structure:

- answer
- evidence
- uncertainty
- next step

These labels are guidance, not mandatory visible headings.

## Question Classification

Before answering, `sp-ask` classifies the user's question into one or more question
types:

- `fact`: what is true in the project now?
- `how-to`: how should the user do something?
- `why`: why does the project behave or route this way?
- `difference`: how are two things different?
- `impact`: what could be affected by a change?
- `location`: where is the relevant logic, template, file, command, or rule?
- `status`: is the current state normal, stale, blocked, complete, or expected?
- `recommendation`: which option should the user choose?
- `concept`: what does a project concept, field, workflow, or artifact mean?
- `history`: why was something designed this way, based on durable notes or docs?
- `boundary`: which project, workflow, target root, or evidence source owns the
  answer?

Classification is internal. The visible answer should name the classification only
when it helps the user understand the answer.

## Evidence Model

`sp-ask` uses a two-level evidence model.

Project cognition is advisory navigation. It can suggest:

- relevant modules and files
- workflow or template surfaces
- project-map concepts and aliases
- likely owners or dependency paths
- project memory and learnings worth reading
- places where live evidence should be checked

Live project evidence is authoritative. It includes:

- source files
- templates
- tests
- scripts
- configuration
- generated workflow assets
- documentation
- state files
- memory and learning documents

The workflow must not present project cognition output as final truth. If cognition
and live files disagree, live files win and the conflict should be called out.

## Answer Contract

Every `sp-ask` answer should satisfy three user-facing questions:

1. What is the answer?
2. Why should I believe it?
3. What should I do next, if anything?

The default answer shape is:

```text
Answer: ...
Evidence: ...
Uncertainty: ...
Next step: ...
```

The visible reply may omit labels when the answer is short. The important contract is
the order and substance, not the headings.

## Routing From sp-ask

`sp-ask` answers the question first. If the answer implies an action, it recommends
the right next workflow without invoking it automatically:

- requirement shaping -> `sp-discussion`
- formal specification -> `sp-specify`
- bounded small implementation -> `sp-quick`
- trivial local fix -> `sp-fast`
- defect/root-cause investigation -> `sp-debug`
- external feasibility or evidence research -> `sp-deep-research`
- current state resume -> `sp-auto`
- artifact explanation -> `sp-explain`
- map maintenance -> `sp-map-update`, or `sp-map-scan -> sp-map-build` only for
  documented baseline rebuild cases

The recommendation should include a short reason so the user understands why that
workflow is the right next step.

## Boundary Rules

If the question depends on another repository or downstream project, `sp-ask` must
lock the target root before making project-specific claims.

If the question asks about current behavior, the workflow must read live evidence
before answering.

If the question is about a concept that can be answered from docs or templates, the
workflow may answer from those sources without reading source code.

If evidence is missing, stale, ambiguous, or contradictory, the answer should say so
directly and name the smallest next evidence action.

## State And Persistence

`sp-ask` v1 is stateless.

It does not create an ask session, durable ask log, or handoff artifact. This keeps it
fast and prevents overlap with `sp-discussion`.

If a question discovers a reusable project lesson, the normal Learning Reflex may
recommend capturing it under project memory, but `sp-ask` should not make routine
questions durable by default.

## Integration Surface

`sp-ask` should be generated like other `sp-*` workflows:

- command template under `templates/commands/ask.md`
- shell partial under `templates/command-partials/ask/shell.md` if the command
  needs a compact generated form
- registration in CLI integration surfaces and supported-agent docs
- workflow routing guidance in passive skills and handbook docs
- tests for Markdown, TOML, skills-based, and Codex generation

The public invocation should follow each integration's existing command style:

- Codex skills: `$sp-ask`
- Claude-style slash command: `/sp-ask`
- slash-dot integrations: `/sp.ask`
- skills-based integrations: their normal `sp-ask` skill invocation

## Success Criteria

- A user can ask a project question without choosing a heavier workflow first.
- The answer starts with the practical conclusion.
- The answer names the evidence used.
- The answer distinguishes evidence-backed facts from assumptions.
- The answer recommends a next workflow only when action is actually needed.
- The workflow does not edit files or create durable state.
- Generated integrations include `sp-ask`.
- Tests verify the command's boundaries, evidence model, question classification,
  and generated integration output.

## Open Questions

- Should `sp-ask` support an explicit `--save` or "record this answer" path later,
  or should durable capture always route through project learning memory?
- Should `sp-ask` be allowed to run bounded commands for evidence, such as tests or
  CLI help, or should v1 limit itself to file reads and existing state?
- Should answer citations be strict file references by default, or only when the
  answer depends on implementation details?

These are v2 questions. The v1 recommendation is to keep `sp-ask` stateless and
read-only.
