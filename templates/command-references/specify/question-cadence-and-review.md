Trigger: before asking requirement-shaping questions or choosing the next command.

Purpose: ask only for user-owned semantic decisions and avoid reconfirming unchanged upstream truth.

Preserved Contract: user-owned scope, behavior, boundary, risk, and deferral changes require confirmation; repository-discoverable facts and unchanged confirmed decisions do not.

## Semantic Delta Review Gate

- In discovery mode, ask one planning-critical question at a time when no safe default exists.
- In compile mode, compare `spec-contract.json` with the confirmed requirement contract.
- If `semantic_delta` is empty and deterministic review passes, do not repeat user review; continue to the single valid next route.
- If a delta changes scope, product behavior, target boundary, risk acceptance, deferral, or another user-owned decision, present only that delta with the recommended resolution and meaningful alternatives.
- Resolve repository facts with bounded evidence instead of asking the user to restate them.
- If changes are requested, update the canonical contract, rerun deterministic review, and recompute the delta.

Choose exactly one next command:

- `/sp.plan` when the spec contract is planning-ready;
- `/sp.clarify` when planning-critical ambiguity remains;
- `/sp.deep-research` when requirements are clear but feasibility or implementation-chain evidence is missing.

After canonical specification output passes review, mark the source discussion consumed using the slug from `SOURCE_CONTRACT`. Do not depend on or reconstruct a Markdown handoff path.

## Completion Report

Report the human-relevant outcome: what is now specified, any confirmed delta, remaining risk, canonical contract path, project-facing spec path, and the single next command. Keep agent-only transition fields backstage unless diagnostics are requested.
