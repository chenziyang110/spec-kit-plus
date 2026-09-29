- **Advanced** is supported by skills-based integrations and generates the
  independent `spx-*` catalog from `templates/advanced-skills/**`. It is
  command-equivalent and prompt-optimized for advanced models: every Classic
  command has an independent SPX counterpart, while `spx-map-rebuild` is an
  additional convenience orchestrator. The current topology is 28 SPX skills:
  27 one-to-one Classic command counterparts plus `spx-map-rebuild`. Advanced
  keeps command ownership, read/write boundaries, resumable stops, and
- `sp-test-design` / `spx-test-design` is an optional planning-only lane after
  Plan and before Tasks, or an independent project-baseline lane. It owns a
  frozen test universe, professional case/data/gap package, bounded read-only
  leader/subagent discovery, independent audit, and pointer-only Tasks handoff;
  it never claims absolute completeness or implements executable test assets.
- **Intentional map exception:** every Advanced install also generates the
