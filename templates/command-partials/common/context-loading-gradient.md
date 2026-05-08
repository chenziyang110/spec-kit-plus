## Runtime Handbook Gate

This command must treat the workflow handbooks as the mandatory pre-source knowledge base.

### Hard Rule

Do not inspect implementation source, run reproduction or tests, compile a
plan, prepare a fix, or emit technical recommendations until the handbook gate has
passed.

### Required Runtime Handbook

- Use `DEBUG-HANDBOOK.md` for `sp-debug`.
- Use `BUILD-HANDBOOK.md` for ordinary non-debug `sp-*` workflows.

### Fixed Chapter Consumption

Every workflow must read the required chapter IDs explicitly required by its command contract.
Do not replace chapter consumption with broad freeform scanning of the handbook.

### Command Tier Depth

Tier determines how deeply the workflow must continue through handbook chapters
after the minimum gate, not whether it may skip handbook consumption.

- `trivial`: minimum required chapter set only
- `light`: minimum chapter set plus relevant routing or playbook chapters
- `heavy`: minimum chapter set plus all relevant collaboration, propagation, and verification chapters

### Freshness

Treat handbook freshness as a gate:

- `missing` -> block and refresh through `sp-map-scan -> sp-map-build`
- `stale` -> block and refresh through `sp-map-scan -> sp-map-build`
- `possibly_stale` -> inspect `must_refresh_topics` and `review_topics`; if
  current-task topics intersect `must_refresh_topics`, block and refresh before continuing

### Primary Read Restriction

Do not treat layered project-map files as primary runtime read surfaces. If handbook
coverage is insufficient, refresh the handbooks or move to live repository evidence
instead of forcing a second atlas traversal phase.
