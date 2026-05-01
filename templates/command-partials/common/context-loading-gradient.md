## Context Loading

This command is tier: `{TIER}`. Load only the layers this tier requires.

### Layer Access by Tier

| Tier | Commands | Layers | Freshness Check |
|------|----------|--------|-----------------|
| trivial | sp-fast | Layer 1 only + target source | Skip |
| light | sp-quick, sp-debug | Layer 1 + Layer 2 summary + target Layer 3 sections | Warn if stale, do not block |
| heavy | sp-specify, sp-plan, sp-tasks, sp-implement | Layer 1 + Layer 2 + Layer 3 full | Enforce; stale triggers scoped rescan |

### Loading Order (all tiers)

1. Read `.specify/project-map/QUICK-NAV.md` first — determine which document to open
2. Read the routed document's Layer 2 summary section
3. [light/heavy only] Read target module's Layer 3 OVERVIEW.md (target sections only for light)
4. [heavy only] Read `root/CONVENTIONS.md` relevant sections + `index/relations.json` for cross-module impact
5. [all tiers] Read source files on-demand when docs are insufficient or marked `gap`

### Freshness (layered, not binary)

- Layer 1 (QUICK-NAV.md): almost never stale — skip check
- Layer 2 (summary cards in ARCHITECTURE.md): changes slowly — warn only
- Layer 3 (module OVERVIEW.md): changes faster — enforce for heavy commands

Check: compare `index/status.json` → `global.commit_hash` with current HEAD.
- Same commit → fresh
- Different, but only Layer 3 files changed → Layer 1+2 still valid
- Different, structural files changed → all layers may be stale

When stale: heavy commands run scoped rescan of affected module only (not global rebuild).
Light commands proceed with a warning.
Trivial commands skip freshness entirely.
