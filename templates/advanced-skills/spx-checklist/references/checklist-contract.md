# Checklist contract

A requirements-quality item asks whether the written contract says the right
thing precisely enough. It does not ask whether code, tests, or UI currently
work.

Good items target one uncertainty and name its requirement, scenario, section,
or boundary. Cover only triggered dimensions: scope and exclusions, actors and
permissions, inputs and outputs, state transitions, error/recovery behavior,
compatibility, security, performance, accessibility, migration, observability,
and acceptance measurability.

Reject items such as "test the endpoint" or "verify the button works". Prefer
questions such as "Are retry limits and the user-visible exhausted state
specified? [Recovery]". Keep the set focused enough that a reviewer can use it
as a real gate rather than a compliance inventory.
