# Claude Agent Teams execution

Require Claude Code Agent Teams to be enabled and expose its native team-create,
shared task ledger, teammate launch, message, join, and shutdown surfaces. If
the first native team operation reports the feature unavailable, stop and tell
the user to enable Agent Teams; do not fall back to ordinary Agent subagents.

Resume one existing feature team or create one leader-owned team. Compile each
ready task into a bounded teammate contract with authoritative inputs, isolated
writes, forbidden paths, acceptance, baseline/RED evidence, verification, and a
structured result shape. Publish dependencies and join points in the shared
ledger before launch.

Wait for every teammate's terminal structured handoff. Validate changed paths,
evidence, assumptions, and blockers before accepting the shared task or join.
The leader inspects the combined diff and reruns real-entrypoint verification.
Shut down the team only after accepted joins and ordinary implementation
closeout; preserve incomplete state needed for recovery.
