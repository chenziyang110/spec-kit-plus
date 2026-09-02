# Claude Agent Teams execution

Require Claude Code Agent Teams to expose its native team-create, shared task
ledger, teammate launch, message, join, and shutdown surfaces. If the first
operation reports the feature unavailable, return an agent-owned
`fallback_action` carrying the exact feature/task/revision context back to
`$spx-implement`. The current orchestrator executes that action automatically
when implementation—not Teams specifically—was authorized. Preserve a genuine
Teams-only request as a capability blocker; never tell the user to repair
workflow state or emulate a team in chat.

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
