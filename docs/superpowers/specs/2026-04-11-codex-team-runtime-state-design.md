# Codex Team Runtime State Design

## Overview
Task 1 focuses on shipping the canonical filesystem contract and JSON surface that every later Codex team runtime operation will build on. This slice defines the `.specify/codex-team/state/` tree, the filenames each runtime actor writes to, the stable JSON payloads they exchange, and the append-only event log that captures lifecycle signaling. Keeping this foundation lean and test-driven lets the next slices (task lifecycle, worker/mailbox ops, session management) depend on well-known paths and schemas without reworking the basics.

## Filesystem layout
- `.specify/codex-team/state/` remains the root.
- Subdirectories and file prefixes will be:
  - `tasks/task-<task_id>.json`
  - `workers/identity-worker-<worker_id>.json`
  - `workers/heartbeat-worker-<worker_id>.json`
  - `mailboxes/mailbox-<worker_id>.json`
  - `dispatch/dispatch-<request_id>.json`
  - `phases/phase-<phase_name>.json`
  - `events/events-<session_id or "default">.log`
  - `shutdown/shutdown-<session_id or "request">.json`
Utility helpers in `state_paths.py` will build these paths so callers never assemble strings inline.

## Record schemas
Each record class (team config, task record, task claim, worker identity, worker heartbeat, monitor snapshot) is versioned with a shared `schema_version` constant and timestamped in `__post_init__`. Helper functions produce dictionaries ready for JSON serialization, and companion `*_from_json` helpers rehydrate the dataclasses for validation/round-tripping. The fields are intentionally minimal (IDs, status/display fields, counts) so the records can be extended in future slices without reworking the base serialization layer.

## Event logging
The append-only event log sits under `events/events-*.log` and stores newline-delimited JSON entries. Each entry is an `EventRecord` containing an `event_id`, `kind`, `payload`, and `schema_version`. `events.py` will provide `append_event`, `iter_event_log`, and helpers to parse log lines with the same schema version logic as the other records.

## Testing
New pytest coverage targets `tests/codex_team/test_runtime_state.py` and `tests/codex_team/test_events.py`. The runtime-state test asserts the canonical paths, validates each record builder/parser, and passes bogus json through the parsing helpers. The event test exercises `append_event` and `iter_event_log`. Running `pytest tests/codex_team/test_runtime_state.py tests/codex_team/test_events.py -q` should fail until the new modules exist, and then pass after implementation.
