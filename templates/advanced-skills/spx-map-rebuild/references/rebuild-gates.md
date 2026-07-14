# Rebuild gates

Rebuild only for a first brownfield baseline, missing or unusable database,
unsupported schema, invalid baseline identity, missing required indexes, or an
explicit full rebuild. An empty greenfield baseline is not a rebuild reason by
itself; localized staleness belongs in `$spx-map-update`.

The phases are intentionally independent:

- `$spx-map-scan` owns repository reads, low-cost packet work, acceptance, and
  scan validation. It cannot build or publish.
- `$spx-map-build` owns deterministic construction, publication, build
  validation, and representative query proof. It cannot scan or repair missing
  evidence.

Resume the phase that already has valid state. Never discard a scan workbench,
reread the repository during build, or bypass either validation gate merely to
make the rebuild appear terminal.
