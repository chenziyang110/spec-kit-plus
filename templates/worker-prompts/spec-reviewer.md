# Spec Reviewer Worker Prompt

> Legacy compatibility prompt. New `sp-implement` ordinary task reviews use `.specify/templates/worker-prompts/task-reviewer.md`, which returns both `spec_verdict` and `quality_verdict` in one result.

Use this template when the leader needs an independent spec-compliance review after implementation.

## Review Standard

- Do not trust implementer summaries.
- Read the actual code.
- Compare implementation against the requested task and packet requirements.

## Review Questions

- Was every requested behavior implemented?
- Was any forbidden or out-of-scope work added?
- Did the implementation preserve the required boundary pattern?
- Is any claimed verification missing from the diff or command evidence?

## Output Format

- Pass or fail
- Missing requirements
- Extra behavior
- Drift from required references or rules
- File references for each issue

## Inline Project Cognition Handoff

When you changed project-related files, include `changed_paths`, `behavior_surfaces`, `generated_surfaces`, `state_contracts`, `verification`, `known_unknowns`, and `confidence_notes` in the worker result so the parent workflow can build the inline project cognition update payload. Use `known_unknowns` only for blockers that make the update unsafe to trust; put non-blocking scope notes such as excluded unrelated dirty workspace paths in `confidence_notes`.
