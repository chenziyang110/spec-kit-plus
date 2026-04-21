# Plan: Systematic and Resumable Debug Workflow

## Objective
Implement a dedicated debug workflow (`/sp-debug`) in `spec-kit-plus` that provides systematic investigation, persistent state tracking, and resumability, mirroring the advanced debugging capabilities of `get-shit-done`.

## Key Features
1. **Systematic Investigation**: Enforces a scientific method (Gather -> Investigate -> Fix -> Verify).
2. **Persistent Session**: Uses `.planning/debug/[slug].md` to track the state of an active debug session.
3. **Resumability**: Enables the AI to perfectly resume from an interruption by reading the debug file.
4. **Hypothesis-Driven**: Tracks tested hypotheses, evidence found, and eliminated possibilities to avoid redundant work.
5. **Human Checkpoints**: Provides structured ways to request user verification or action.

## Discovered from Reference (`get-shit-done`)
- `gsd-debugger.md`: The core logic for investigation and state management.
- `DEBUG.md`: The file format for tracking sessions.
- `knowledge-base.md`: A persistent log of resolved bugs to speed up future diagnosis.

## Proposed Changes

### 1. New Command: `/sp-debug`
- Create `templates/commands/debug.md` to define the command surface.
- Add logic to `specify` CLI to handle the `debug` command.

### 2. New Agent Skill: `sp-debug`
- Create `.agents/skills/sp-debug/SKILL.md`.
- This skill will implement the scientific method logic, hypothesis testing, and state file management.

### 3. Debug Template
- Create `templates/debug.md` based on the reference `DEBUG.md`.
- This template will be used to scaffold `.planning/debug/*.md` files.

### 4. Integration
- Update `CodexIntegration` and other relevant integrations to include the `debug` skill.
- Update `README.md` with usage instructions.

## Implementation Steps

### Phase 1: Templates and Skills
1. Create `templates/debug.md`.
2. Create `templates/commands/debug.md`.
3. Create `.agents/skills/sp-debug/SKILL.md`.

### Phase 2: CLI Integration
1. Update `src/specify_cli/__init__.py` to register the `debug` command.
2. Update integration loaders to ensure `sp-debug` is available to agents.

### Phase 3: Documentation and Verification
1. Update `README.md`.
2. Test the workflow with a mock bug scenario.
