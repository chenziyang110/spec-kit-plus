## Project-Map Hard Gate

This command must treat the atlas as a mandatory pre-source knowledge base.

### Hard Rule

Do not inspect implementation source, run reproduction or tests, compile a
plan, prepare a fix, or emit technical recommendations until the atlas gate has
passed.

### Minimum Atlas Read Set

Every ordinary `sp-*` workflow must read:

1. `PROJECT-HANDBOOK.md`
2. `atlas.entry`
3. `atlas.index.status`
4. `atlas.index.atlas`
5. at least one relevant root topic document
6. at least one relevant module overview document

If the touched area crosses shared surfaces, integration seams, workflow joins,
or verification-sensitive boundaries, also read:

- `atlas.index.relations`
- any additional root topic documents named by the entry layer

### Command Tier Depth

Tier determines how deeply the workflow must continue through atlas layers
after the minimum gate, not whether it may skip atlas consumption.

- `trivial` (`sp-fast`): stay at the minimum atlas read set unless the entry
  layer names shared-surface risk
- `light` (`sp-quick`, `sp-debug`): read all root topics and module sections
  named by Layer 1 for the touched area
- `heavy` (`sp-specify`, `sp-plan`, `sp-tasks`, `sp-implement`): read all
  relevant root topics, module docs, and relation surfaces needed for the
  current decision

### Freshness

Treat atlas freshness as a gate:

- `missing` -> block and refresh through `sp-map-scan -> sp-map-build`
- `stale` -> block and refresh through `sp-map-scan -> sp-map-build`
- `possibly_stale` -> inspect `must_refresh_topics` and `review_topics`; if
  current-task topics intersect `must_refresh_topics`, block and refresh before
  continuing

The old `warn but proceed` behavior is not allowed.
