# Roadmap: spec-kit-plus

## Overview

The roadmap now moves from stronger planning-time questioning into deeper execution-time orchestration. Milestone v1.3 focuses on one specific product gap: `sp-implement` still cannot reliably drive a whole milestone to completion because the invoking agent remains the executor, phase progression stops too early, and worker results do not converge into a durable milestone-level loop. The execution path for this milestone is to first establish a leader-only scheduler contract, then ship worker dispatch and mixed failure handling, and finally align state artifacts, shipped surfaces, and regression coverage around the new runtime.

## Milestones

- Good **v1.0 Debug Workflow** - Phases 1-3 (shipped 2026-04-13)
- Good **v1.1 Analysis and Planning Workflows** - Phases 4-6 (shipped 2026-04-13)
- Good **v1.2 Stronger Specify Questioning** - Phases 7-9 (shipped 2026-04-14, see `milestones/v1.2-ROADMAP.md`)
- Good **v1.3 Implement Orchestrator Runtime** - Phases 10-12 (shipped 2026-04-14, see `milestones/v1.3-ROADMAP.md`)

## Active Roadmap

No active milestone is currently defined.

Run `/gsd-new-milestone` to start the next milestone and create a fresh milestone-scoped roadmap and requirements set.

## Progress

| Milestone | Status | Phase Range | Shipped |
|-----------|--------|-------------|---------|
| v1.0 Debug Workflow | Complete | 1-3 | 2026-04-13 |
| v1.1 Analysis and Planning Workflows | Complete | 4-6 | 2026-04-13 |
| v1.2 Stronger Specify Questioning | Complete | 7-9 | 2026-04-14 |
| v1.3 Implement Orchestrator Runtime | Complete | 10-12 | 2026-04-14 |
