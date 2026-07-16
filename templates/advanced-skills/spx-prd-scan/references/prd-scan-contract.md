# PRD scan contract

The scan package lives under `.specify/prd-runs/<run-id>/` and must contain the
installed canonical workflow state, scan report, coverage/capability/artifact/
entrypoint ledgers, configuration and protocol contracts, state machines, error
semantics, verification surfaces, packet evidence, and accepted worker results.

Use L4 reconstruction readiness for critical capabilities: the package must let
a later builder identify ownership, consumers, behavior, inputs/outputs, state
and failure semantics, configuration/protocol rules, and a real verification
route without reopening a broad repository scan. High-value gaps remain
explicit; path-only references are not reconstruction evidence.

Each delegated packet has concrete read scope, required contract fields,
acceptance, verification, and a structured result path. Account for every
assigned critical surface and wait for every dispatched result. Reject shallow,
contradictory, or uncited results packet-locally. Scan completion requires both
coverage and evidence depth, not a count of files read.
