# Codex Native Hooks

The native hook layer is responsible for lightweight lifecycle integration around the Specify runtime.

## Wiki Lifecycle

Storage for project wiki pages is `.specify/runtime/wiki/`.

`SessionStart` may inject bounded wiki context when a project wiki already exists. This context is advisory and must stay small enough to avoid crowding out task context.

`SessionEnd` uses the runtime/notify-path as a non-blocking lifecycle signal. It may enqueue wiki capture work, but it must not block the user-facing Codex session shutdown path.

PreCompact parity is intentionally deferred until the lifecycle contract is explicit and tested.

For routing, prefer `$wiki` and avoid implicit bare `wiki` noun activation.
