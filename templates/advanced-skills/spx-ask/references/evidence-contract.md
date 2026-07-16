# Evidence contract

Use this reference when the answer crosses modules, describes architecture or
status, or predicts change impact.

- State the conclusion first.
- Separate `verified`, `inferred`, and `unknown`; never let model memory or a
  cognition route stand in for current repository evidence.
- Support material claims with the smallest useful set of concrete paths,
  symbols, tests, configuration, or runtime output.
- For architecture, name the entry point, owner, state/data boundary, important
  consumers, and verification surface. Omit categories that do not apply.
- For impact, distinguish direct dependencies from plausible secondary effects
  and say what evidence would resolve uncertainty.
- If evidence conflicts, report the conflict instead of choosing the convenient
  source. Prefer live behavior and executable contracts over stale prose.
- Do not generate a report artifact unless the user explicitly requests one.

Stop when additional reads would repeat the same evidence rather than change
the answer or its confidence.
