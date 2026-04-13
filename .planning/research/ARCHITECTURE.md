# Architecture Research: Stronger `sp-specify` Questioning

**Domain:** Prompt-contract architecture for `specify`
**Researched:** 2026-04-13

## Current Architecture

The current `specify` questioning experience is distributed across four important surfaces:

1. `templates/commands/specify.md`
   The shared command template and the closest thing to the authoritative workflow contract.
2. `.agents/skills/sp-specify/SKILL.md`
   The local Codex-facing mirror that users may actually execute.
3. `tests/test_alignment_templates.py`
   The main contract test for the shared `specify` template behavior.
4. Supporting design docs under `docs/superpowers/`
   Historical reasoning that explains why `specify` became analysis-first in the first place.

## Architectural Finding

The repo currently has a **contract-drift problem**:

- `templates/commands/specify.md` describes a richer, more analysis-heavy, open-question-block workflow.
- `.agents/skills/sp-specify/SKILL.md` still reflects an older contract with boxed question-card wording, a narrower analysis model, and no `references.md` step.
- Existing tests strongly validate the template, but they do not fully prove that the shipped skill mirrors stay aligned.

This means the milestone should be designed as a **single behavior contract with multiple output surfaces**, not as a prompt tweak in one file.

## Recommended Integration Points

| Integration Point | Why It Matters | Change Type |
|-------------------|----------------|-------------|
| `templates/commands/specify.md` | Defines the main questioning behavior | Behavior design |
| `.agents/skills/sp-specify/SKILL.md` | Must mirror the shipped behavior users actually experience | Sync + regression |
| `tests/test_alignment_templates.py` | Protects the shared template contract | Expand assertions |
| `tests/test_extension_skills.py` or similar generated-surface tests | Best place to catch future drift between template and shipped skill content | Add or extend |
| Workflow docs / README copy where needed | Keeps user expectations aligned with the new questioning quality promise | Optional but useful |

## Suggested Build Order

1. Finalize the target questioning contract for `specify`.
2. Update the authoritative command template.
3. Resync the generated/local skill mirror.
4. Add regression coverage that catches template-to-skill drift and depth regressions.
5. Update surrounding docs only where they materially affect user expectations.

## Architectural Guardrails

- Keep the `specify -> plan` mainline intact.
- Do not move requirement-depth responsibility back into `clarify`.
- Preserve structured interaction blocks as the outer shell.
- Improve the adaptive questioning logic inside that shell.
- Prefer contract tests that describe behavior, not brittle snapshot tests of every line.

## Design Implications for Roadmap

The roadmap should likely separate:

1. **Questioning contract redesign**
2. **Surface synchronization and test hardening**
3. **User-facing docs/polish and final alignment**

That split matches both the current architecture and the user's stated priority on real experience change.
