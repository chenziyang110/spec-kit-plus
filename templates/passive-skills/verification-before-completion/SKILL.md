---
name: verification-before-completion
description: Use when about to claim work is complete, fixed, or passing, before committing or creating PRs. Requires current fingerprint-bound verification evidence; respects workflow-owned logical gates and attempts instead of duplicating commands.
---

# Verification Before Completion

## Overview

Claiming work is complete without verification is dishonesty, not efficiency.

**Core principle:** Evidence before claims, always.

**Violating the letter of this rule is violating the spirit of this rule.**

## Workflow-Owned Validation

When an active workflow provides a validation ledger, fresh evidence means
current source-fingerprint-bound evidence in that ledger. Inspect it before a
claim. Only the workflow's Leader may open a logical gate or an attempt inside
it. A worker, passive skill, join, resume, or message must not start an extra
gate or attempt merely to make a local claim.

For `sp-implement`, moving to the next Txx does not require another heavyweight
test run. Record cheap task checks and test impact, then let the Leader verify
the integrated change-set. The three-gate ledger remains shared across
Implement and Review and must not be reset at handoff; interrupted attempts
retry without consuming a gate.

## The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If the current source fingerprint has no accepted verification evidence, you
cannot claim it passes. Evidence may come from the active workflow's canonical
ledger; it need not be rerun in this message.

## The Gate Function

```
BEFORE claiming any status or expressing satisfaction:

1. IDENTIFY: What command proves this claim?
2. RUN OR REUSE: Outside a workflow budget, execute the full proving command.
   Inside one, reuse a passed gate attempt for the unchanged fingerprint or ask
   the Leader to open the next attempt; do not run independently.
3. READ: Full output, check exit code, count failures
4. VERIFY: Does output confirm the claim?
   - If NO: State actual status with evidence
   - If YES: State claim WITH evidence
5. ONLY THEN: Make the claim

Skip any step = lying, not verifying
```

## Common Failures

| Claim | Requires | Not Sufficient |
|-------|----------|----------------|
| Tests pass | Current-fingerprint command output or accepted gate-attempt evidence: 0 failures | Stale run, "should pass" |
| Linter clean | Linter output: 0 errors | Partial check, extrapolation |
| Build succeeds | Build command: exit 0 | Linter passing, logs look good |
| Bug fixed | Test original symptom: passes | Code changed, assumed fixed |
| Regression test works | Red-green cycle verified | Test passes once |
| Agent completed | VCS diff shows changes | Agent reports "success" |
| Requirements met | Line-by-line checklist | Tests passing |

## Red Flags - STOP

- Using "should", "probably", "seems to"
- Expressing satisfaction before verification ("Great!", "Perfect!", "Done!", etc.)
- About to commit/push/PR without verification
- Trusting agent success reports
- Relying on partial verification
- Thinking "just this once"
- Tired and wanting work over
- **ANY wording implying success without current verification evidence**

## Rationalization Prevention

| Excuse | Reality |
|--------|---------|
| "Should work now" | RUN the verification |
| "I'm confident" | Confidence ≠ evidence |
| "Just this once" | No exceptions |
| "Linter passed" | Linter ≠ compiler |
| "Agent said success" | Verify independently |
| "I'm tired" | Exhaustion ≠ excuse |
| "Partial check is enough" | Partial proves nothing |
| "Different words so rule doesn't apply" | Spirit over letter |

## Key Patterns

**Tests:**
```
✅ [Run test command] [See: 34/34 pass] "All tests pass"
❌ "Should pass now" / "Looks correct"
```

**Standalone regression tests (TDD Red-Green):**
```
✅ Outside a ledger-owned workflow: Write → Run (pass) → Revert fix → Run
(MUST FAIL) → Restore → Run (pass)
✅ Inside a ledger-owned workflow: use its recorded change-set RED and integrated
GREEN evidence; do not manufacture three extra runs.
❌ "I've written a regression test" (without red-green verification)
```

**Build:**
```
✅ [Run build] [See: exit 0] "Build passes"
❌ "Linter passed" (linter doesn't check compilation)
```

**Requirements:**
```
✅ Re-read plan → Create checklist → Verify each → Report gaps or completion
❌ "Tests pass, phase complete"
```

**Agent delegation:**
```
✅ Agent reports success → Check VCS diff → Verify changes → Report actual state
❌ Trust agent report
```

## Why This Matters

From 24 failure memories:
- your human partner said "I don't believe you" - trust broken
- Undefined functions shipped - would crash
- Missing requirements shipped - incomplete features
- Time wasted on false completion → redirect → rework
- Violates: "Honesty is a core value. If you lie, you'll be replaced."

## When To Apply

**ALWAYS before:**
- ANY variation of success/completion claims
- ANY expression of satisfaction
- ANY positive statement about work state
- Committing, PR creation, task completion
- Final workflow or delivery claims that are not already covered by current
  fingerprint-bound gate-attempt evidence

**Rule applies to:**
- Exact phrases
- Paraphrases and synonyms
- Implications of success
- ANY communication suggesting completion/correctness

## The Bottom Line

**No shortcuts for verification.**

Run the command when you own the gate, or inspect the canonical current attempt
when the workflow owns it. Read the evidence. Then claim only what it proves.

This is non-negotiable.
