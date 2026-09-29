   silently invoke another workflow. Runtime help/discovery is authoritative:
   `specify e2e` is an informational native-entrypoint hint, not a test runner.
   Never invent `specify-runtime e2e` or an `execution announce` E2E enum.
   Use the bootstrap's **other modifying workflows** Work Board route;
   unsupported runtime/cognition tokens are capability gaps, not permission to
   impersonate another workflow or hand-write runtime state.
ways to discover test conditions, not synonyms for pairwise parameter coverage.
Unknown expected behavior is an oracle gap, not an invented product rule.

Enumerate each concrete input class, exact boundary value, decision-rule row,
state transition and high-risk compound condition in the operation's optional
`conditions: [{id, dimension, description, source_refs}]` inventory. New books
must enumerate the discovered conditions; absence is supported only to read
legacy v1 books, never proof that a broad dimension label covers its values.
For example, L-1, L and L+1 are three conditions, each with the actual value,
measurement unit and authoritative rule in its description/source.

Bind each condition in a scenario through
`condition_checks: [{condition, step_id, oracle_id}]`: the step actually creates
or exercises that condition and the oracle checks its expected result. Distinct
conditions in the same dimension require distinct witness steps; one input
cannot count as both L and L+1. Separate scenarios are preferred when state or
oracles differ. `check` reports unbound conditions even when the dimension has
another case; `audit` lists which conditions and timing obligations have a
passing scenario. Neither infers missing classes or proves semantic adequacy.

For rename, ask about missing/moved/externally renamed/replaced objects, a new
object at the old path, target-name conflicts, permission/lock changes, invalid
registered design/source-continuity IDs. A screenshot is visual evidence, not
proof of file identity, durable storage, server state, or correct background work:
verify those through independent filesystem/API/CLI/database readback.
Logs may corroborate an action or checkpoint, but a success log alone cannot
satisfy a durable-effect oracle. The readback must inspect the actual outcome.
Unavailable effect oracles remain blocked or pending, even if the UI looks right.
completeness, product acceptance or release safety. Formal delivery remains
`tasks -> implement -> review -> accept`; E2E is additional evidence, not a bypass.

For actual scoped test-asset changes, use canonical `sp-e2e` cognition closeout
below before claiming clean completion. Do not include unrelated user changes or
runtime result directories in product mutation scope. An observation-only run
has no source mutation to close; do not fabricate a passing test or graph update.
Missing runtime support stays a named capability/recovery gap.

{{spec-kit-include: ../command-partials/common/inline-project-cognition-update.md}}

At a blocked exit preserve stage, category, owner, exact cause, sanitized evidence,
attempted recovery, affected IDs, next action, observable unblock criteria and
