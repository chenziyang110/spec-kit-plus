# Specify Native Question Hard Gate Design

**Date:** 2026-04-26  
**Status:** Implemented  
**Owner:** Codex

## Summary

This design hardens the `sp-specify` clarification output contract so native structured
question tools are treated as a hard gate rather than a soft preference.

Before this change, the shared `sp-specify` template already said that a native
structured question tool should be used when available, but the textual fallback format
was still detailed enough that models could choose it anyway. In practice, this meant
the fallback competed with the preferred path instead of acting as a true backup.

The approved change is:

- if a native structured question tool is available, it must be used
- the textual block must not be rendered when the native tool is available
- fallback is allowed only when the tool is unavailable or the tool call fails
- the shared template stays integration-neutral; concrete tool names remain integration
  specific

## Problem Statement

The old contract had three weaknesses:

1. The native-tool rule and the textual fallback lived side-by-side inside the same
   clarification section.
2. The fallback block was highly concrete and easy to copy verbatim.
3. Nothing explicitly prevented the model from self-authorizing fallback because a
   question felt “simple enough” for plain text.

That made the workflow vulnerable to the exact failure the user reported:

- the model knew a native tool existed
- but still rendered the textual fallback question block

## Goals

- Make the native structured question path the default execution path.
- Prevent the model from emitting both the native tool question and the textual block
  in the same turn.
- Preserve the textual format as a real fallback for runtimes that do not expose the
  structured tool.
- Keep the shared template integration-neutral across Codex, Claude, Markdown, TOML,
  and skills-based renderers.

## Non-Goals

- Do not hard-code `AskUserQuestion` or `request_user_input` into the shared template.
- Do not remove the textual fallback entirely.
- Do not redesign the surrounding clarification workflow.
- Do not move question handling into a separate command.

## Approved Direction

The contract now adds a hard gate at the top of the clarification loop:

1. Before any clarification question, confirmation, or bounded selection is generated,
   the workflow checks whether a native structured question tool is available.
2. If it is available, the model must use it.
3. The textual fallback block must not be rendered while that native tool is available.
4. The model may not self-authorize fallback because the question seems short or easy.
5. Fallback is allowed only when the tool is unavailable or the tool call fails.

## Mapping Rule

The shared template now states how to map the existing question structure into generic
native tool fields:

- stage header + topic label -> native header/title field
- prompt -> native question field
- options -> native option list
- recommendation rationale -> recommended option description or equivalent metadata

This keeps the shared contract cross-CLI while still making the native path specific
enough to execute reliably.

## Integration Boundaries

The shared template remains generic.

Concrete tool names stay in integration metadata:

- Codex injects `request_user_input`
- Claude injects `AskUserQuestion`

This avoids coupling the shared workflow template to one runtime while still allowing
tests to verify concrete injected behavior per integration.

## Testing Strategy

The implementation is locked at three levels:

1. Shared template tests assert the hard gate language exists in `sp-specify`.
2. Shared skill-mirror tests assert generated `sp-specify` skills inherit the same
   hard gate.
3. Integration tests assert the injected Codex and Claude surfaces keep the same
   rule while naming their concrete tools.

## Decision

Proceed with the native-question hard gate.

The fallback question block remains available, but it is no longer a peer path. The
native structured question tool is now the required path whenever the runtime exposes
it.
