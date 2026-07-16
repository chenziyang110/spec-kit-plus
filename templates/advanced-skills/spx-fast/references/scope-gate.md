# Fast scope gate

Use `spx-fast` only when all are true:

- the requested outcome and solution are already clear;
- the change is local, normally within three files;
- no public contract, shared registry, dependency, migration, security control,
  generated protocol, or product decision changes;
- the likely edit set and meaningful verification are known;
- failure can be reverted locally without coordinated recovery.

Route to `spx-debug` when the cause is unknown, `spx-quick` when the work needs
state or bounded investigation, and `spx-specify` when acceptance or behavior
must be decided. A small diff is not automatically a fast task.

Behavior changes need a failing signal or credible before-state when one is
practical. Formatting, copy, and mechanically provable changes may use a direct
post-change check.
