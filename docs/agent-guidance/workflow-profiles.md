- **Advanced** is supported by skills-based integrations and generates the
  independent `spx-*` catalog from `templates/advanced-skills/**`. It is
  command-equivalent and prompt-optimized for advanced models: every Classic
  command has an independent SPX counterpart, while `spx-map-rebuild` is an
  additional convenience orchestrator. The current topology is 29 SPX skills:
  28 one-to-one Classic command counterparts plus `spx-map-rebuild`. Advanced
  keeps command ownership, read/write boundaries, resumable stops, and
- `sp-test-design` / `spx-test-design` is an optional planning-only lane after
  Plan and before Tasks, or an independent project-baseline lane. It owns a
  frozen test universe, professional case/data/gap package, bounded read-only
  leader/subagent discovery, independent audit, and pointer-only Tasks handoff;
  it never claims absolute completeness or implements executable test assets.
- `sp-e2e` / `spx-e2e` is an explicitly invoked scenario-first testing lane for
  desktop/mobile clients, web, CLI and services. It derives operation-level
  negative, boundary, state, timing and recovery obligations before selecting
  visual-model tools or a suitable native runner. Browser automation and test
  source files are not prerequisites for client scenario design or visual
  execution. Preserve Test Design as an optional read-only input, never mutate
  feature lifecycle state, and retain mandatory Review/Accept. Scoped test-asset
  changes use canonical `sp-e2e` cognition closeout; observation alone never
  authorizes product changes. Every missing tool, oracle or case remains a gap.
- **Intentional map exception:** every Advanced install also generates the
