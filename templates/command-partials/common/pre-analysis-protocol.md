## Pre-Analysis Protocol

Shared "understand before acting" framework. Used by sp-specify and sp-debug.
Each command defines only its specialized phases; this format is the common output.

### Required Output Fields

- **Scope boundary**: What is in scope? What is explicitly out of scope?
- **Key constraints**: What must not change? What invariants must hold?
- **Affected surface area**: Which modules, files, APIs, or contracts are touched?
- **Known unknowns**: What is unclear? What needs verification before proceeding?
- **Recommended next step**: Based on the analysis, what is the safest next action?

### Inter-Command Recognition

If a pre-analysis output already exists from a prior command (e.g., sp-specify completed before sp-debug), read that output. Do not re-analyze the same surface. Add only the specialized analysis your command requires.

### Fast-Path (debug only)

When all three conditions are met, observer framing can be fast-pathed:
1. Exact error location is known (file + line or function)
2. Clear reproduction steps are provided
3. Impact surface is bounded (single module, no cross-module coupling)

If fast-path: manually set `observer_framing_completed: true`, fill minimal `observer_framing` fields (summary, primary_suspected_loop, etc.), and record `observer_mode: compressed` with `skip_observer_reason`. The graph engine will skip the think-subagent gate and proceed directly to the reproduction gate.

Record the fast-path decision with: "Fast-path: error location known, repro steps clear, impact bounded to [module]."
