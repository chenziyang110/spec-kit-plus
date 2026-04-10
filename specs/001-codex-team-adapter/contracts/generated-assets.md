# Contract: Generated Assets

## Intent

Define which generated artifacts are expected for Codex projects in the first release and how they differ from non-Codex projects.

## Codex project contract

A fresh `specify init --ai codex` project must receive:

- Codex-facing generated skill assets under `.agents/skills/`
- Updated Codex context through `AGENTS.md`
- Integration manifest records under `.specify/integrations/`
- Any runtime helper/config assets required by the new Codex-only team capability

## Non-Codex contract

A fresh non-Codex project must not receive:

- Codex-only team/runtime skills
- Codex-only runtime helper/config assets
- Codex-only advertised team command surface

## Tracking contract

- New generated files must be hash-tracked by the existing integration manifest mechanism where applicable.
- Asset generation must remain reviewable and removable without affecting unrelated integrations.
