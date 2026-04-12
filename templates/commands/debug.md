---
description: Systematic and resumable bug investigation and fixing.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json
  ps: scripts/powershell/check-prerequisites.ps1 -Json
---

## User Input

```text
$ARGUMENTS
```

## Objective
Investigate and fix a bug using a systematic, persistent, and resumable workflow. This command ensures that investigation state is tracked in `.planning/debug/*.md` to avoid redundant work and enable recovery from interruptions.

## Process

1. **Check for Active Session**:
   - Look for existing files in `.planning/debug/*.md` (excluding `resolved/` subdirectory).
   - If a session exists and no new issue is described, resume it.
   - If a new issue is described, start a new session.

2. **Initialize/Resume Session**:
   - Create or read the session file in `.planning/debug/[slug].md`.
   - Announce the current status and hypothesis.

3. **Execute Debug Workflow**:
   - Follow the scientific method: Gather -> Investigate -> Fix -> Verify.
   - Update the debug file BEFORE taking any action.
   - Document every finding in the `Evidence` section.
   - Record disproven theories in the `Eliminated` section.

4. **Human Verification**:
   - Once a fix is verified by the agent, request a human checkpoint for final confirmation.

5. **Archive and Commit**:
   - After confirmation, move the session file to `resolved/`.
   - Commit the fix and the debug documentation.

To begin the debug session:
`EXECUTE_COMMAND: debug`
