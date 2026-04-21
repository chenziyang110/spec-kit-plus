# Tasks: Autonomous Execution

## Setup
- [X] T1: Research reference project `get-shit-done` `/gsd-autonomous` command
- [X] T2: Create specification for autonomous mode
- [X] T3: Create implementation plan

## Core Implementation
- [X] T4: Update `sp-implement` skill template (`templates/commands/implement.md`) with the autonomous loop section
- [X] T5: Register `specify autonomous` command in `src/specify_cli/__init__.py`
- [X] T6: Implement the `gsd:autonomous` skill file (`templates/commands/autonomous.md`)

## Integration
- [ ] T7: Connect `sp-autonomous` to the `ROADMAP.md` phase loop (Partially in skill file)
- [ ] T8: Verify `specify team auto-dispatch` integration works within the autonomous loop

## Testing & Validation
- [ ] T9: Create manual verification scenario for autonomous completion
- [ ] T10: Add unit/contract tests for autonomous state persistence
- [ ] T11: Verify cross-platform compatibility (sh vs ps)

## Documentation
- [ ] T12: Update `README.md` with `/gsd-autonomous` usage instructions
- [ ] T13: Document the `--autonomous` flag for `implement`
