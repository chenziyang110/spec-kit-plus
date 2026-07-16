Trigger: when generating conditional design artifacts and validation scenarios.

Purpose: preserve data-model, contracts, quickstart, and agent-context artifact generation conditions.

Preserved Contract: research.md, quickstart.md, data-model.md, and contracts/ are generated only when their planning or validation triggers are present.

## Phases

### Phase 0: Outline & Research

1. Check the spec contract and context capsule for unresolved implementation-shaping unknowns:
   - For each `NEEDS CLARIFICATION` -> research task
   - For each dependency -> best-practices task
   - For each integration -> patterns task
   - For each high-risk architectural choice -> stack/pattern/pitfall task
   - For each external tool, runtime, or service dependency -> availability and fallback task

2. When at least one unresolved item can change architecture, dependency choice, compatibility, security, or validation, generate bounded research tasks.
   - Prefer official documentation, standards, and primary sources for factual claims.
   - Treat model memory as provisional unless confirmed by a primary source or direct repository evidence.
   - Research must reduce planning ambiguity, not accumulate background reading.

3. When research ran, consolidate findings in `research.md` using:
   - Decision
   - Rationale
   - Alternatives considered
   - Source confidence (`verified`, `cited`, or `assumed`) for each consequential claim
   - Standard stack recommendations where the phase depends on specific libraries, tools, or frameworks
   - `Don't hand-roll` guidance for problems that should use established libraries or platform capabilities
   - Common pitfalls, failure modes, and anti-patterns the planner should explicitly avoid
   - Assumptions log for anything still not verified in this session
   - Validation notes describing how the researched choice should be proven during implementation or verification
   - Environment or dependency notes when the phase depends on tools, services, runtimes, or external infrastructure that may not be present

4. Research quality bar:
   - Do not present unverified claims as settled facts.
   - If a claim could materially change plan structure, security posture, compatibility, or verification scope, it must either be verified, explicitly cited, or moved into the assumptions log.
   - Prefer prescriptive recommendations over broad option dumps once the evidence is strong enough to guide planning.
   - The finished `research.md` should answer: "What does the planner need to know to produce a high-quality implementation plan without rediscovering the domain?"
   - Use `templates/research-template.md` as the default structure for `research.md`; remove sections that are not relevant rather than leaving placeholder text behind.

**Output**: conditional `research.md`; otherwise record `research_status: not-needed` in `plan-contract.json` without creating an empty file.

### Phase 1: Design & Contracts

**Prerequisites:** all planning-critical unknowns resolved, whether from existing evidence or conditional research.

1. **Conditional: `data-model.md`** — Required only when the spec introduces new entities, data structures, state transitions, or persistence concerns. For pure logic changes, bug fixes, or config-only work, skip and note the reason in plan.md.
2. **Conditional: `contracts/`** — Required only when the feature defines new external interfaces, APIs, cross-service contracts, or protocol boundaries. For internal-only changes, skip and note the reason.
3. **Conditional: `quickstart.md`** — Generate only when a representative end-to-end scenario materially reduces implementation or verification ambiguity. Otherwise keep the validation scenario in `plan-contract.json` and do not create a separate file.
4. Run `{AGENT_SCRIPT}` to update agent-specific context.

**Output**: `plan-contract.json` always; `research.md`, `quickstart.md`, `data-model.md`, and `contracts/*` only when their triggers are present. Record skipped-trigger reasons compactly in the contract rather than adding placeholder documents.
