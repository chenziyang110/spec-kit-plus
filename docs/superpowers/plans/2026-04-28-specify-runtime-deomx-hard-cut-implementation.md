# Specify Runtime De-OMX Hard-Cut Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hard-cut all active OMX naming from the runtime surface and replace it with `sp-*` / `specify_*` / `.specify/*` conventions.

**Architecture:** Apply the migration in one naming slice: lock behavior with tests, rename public runtime/team surfaces, rename MCP identities and runtime roots, then sweep docs/config generation and verification. Do not delete MCP functionality in this pass.

**Tech Stack:** Python Typer CLI, TypeScript MCP/runtime engine, Markdown docs/tests, Rust runtime binary naming references

---

### Task 1: Lock New Naming Contract In Tests

**Files:**
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/contract/test_codex_team_generated_assets.py`
- Modify: `tests/codex_team/test_codex_guidance_routing.py`
- Modify: `tests/test_specify_guidance_docs.py`

- [ ] **Step 1: Add failing tests for `sp-teams` public surface**
- [ ] **Step 2: Add failing tests for `.specify/teams/*` runtime asset paths**
- [ ] **Step 3: Add failing tests for `specify_*` MCP identifiers and `.specify/runtime/*` roots**
- [ ] **Step 4: Run the focused test set and confirm RED**

### Task 2: Rename Public Team Surface

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `src/specify_cli/codex_team/commands.py`
- Modify: `src/specify_cli/codex_team/installer.py`

- [ ] **Step 1: Replace `specify team` / `sp-team` with `sp-teams` in public command metadata and help text**
- [ ] **Step 2: Move generated runtime asset references from `.specify/codex-team/` to `.specify/teams/`**
- [ ] **Step 3: Update emitted integration metadata and CLI copy**
- [ ] **Step 4: Run focused runtime-surface tests and confirm GREEN**

### Task 3: Rename MCP Identities And Runtime Roots

**Files:**
- Modify: `extensions/agent-teams/engine/src/mcp/*.ts`
- Modify: `extensions/agent-teams/engine/src/utils/paths.ts`
- Modify: `extensions/agent-teams/engine/src/config/generator.ts`
- Modify: `extensions/agent-teams/engine/src/cli/mcp-parity.ts`

- [ ] **Step 1: Replace `omx_*` MCP names with `specify_*`**
- [ ] **Step 2: Replace `.omx/*` runtime storage roots with `.specify/runtime/*`**
- [ ] **Step 3: Replace `OMX_*` env vars with `SPECIFY_*`**
- [ ] **Step 4: Replace `omx-runtime` references with `specify-runtime` where the name is part of the active runtime contract**
- [ ] **Step 5: Run engine MCP/runtime contract tests and confirm GREEN**

### Task 4: Sweep Docs And Operator Scripts

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/quickstart.md`
- Modify: `scripts/sync-ecc-to-codex.sh`
- Modify: `scripts/powershell/sync-ecc-to-codex.ps1`

- [ ] **Step 1: Remove `OMX` / `omx` branding from active product docs**
- [ ] **Step 2: Update sync/setup scripts so they no longer advertise `omx setup`**
- [ ] **Step 3: Verify no public docs still teach `specify team` or `omx`**

### Task 5: Verification Sweep

**Files:**
- Verify only

- [ ] **Step 1: Run targeted Python contract/integration suites**
- [ ] **Step 2: Run targeted TypeScript engine tests that cover MCP naming and runtime roots**
- [ ] **Step 3: Review diff for unintended non-rename drift**
