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

### Debug Note

`sp-debug` now uses a project-map-backed intake contract by default and deep Stage 1A/1B intake as fallback. Do not use this shared partial to justify bypassing the debug workflow's completed intake fields. Reproduction, log review, test inspection, source-code reads, evidence collection, and fixing still wait on the canonical intake artifacts described by the debug workflow itself.
