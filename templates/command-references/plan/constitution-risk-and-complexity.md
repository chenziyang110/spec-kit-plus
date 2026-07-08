Trigger: when constitution checks, risk classification, complexity tracking, or alignment risks shape the plan.

Purpose: preserve constitution, complexity, input-risk, implementation-constitution, and risk carry-forward rules.

Preserved Contract: constitution/risk checks and locked upstream decisions must remain explicit planning constraints.

## Input Risks From Alignment

- [Risk 1 from alignment.md, or "None"]
- [Risk 2 from alignment.md, or omit if none]

## Key Rules

- Use absolute paths for local file reads and artifact references. Exception: `artifact scaffold --out` must use a project-relative path; never pass an absolute `FEATURE_DIR` to scaffold commands.
- ERROR on gate failures or unresolved clarifications
- Match the user's current language for all user-visible output unless a literal command name, file path, or fixed status value must remain unchanged.
