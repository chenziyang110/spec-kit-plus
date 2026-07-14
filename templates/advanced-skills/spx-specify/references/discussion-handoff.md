# Discussion handoff

Use this only when requirements span turns or an existing confirmed discussion
must feed the specification. Prefer the installed deterministic discussion
commands for init, resume, handoff validation, ready, and consumed state.

Keep one compact decision digest containing confirmed scope, rejected options,
assumptions, unresolved user-owned decisions, UI/reference inputs, and the
current semantic delta. Confirm the digest before treating it as authoritative.

A handoff is usable only when its referenced evidence exists, blocking
questions are resolved or explicitly retained, and the specification can trace
every material confirmed decision. If live repository evidence contradicts the
handoff, surface the conflict; do not silently favor either source.

Mark the handoff consumed only after validation and successful compilation into
the spec contract. `$spx-discussion` owns the producer lifecycle; this reference
only governs safe consumption, and discussion is never mandatory for a clear
request.
