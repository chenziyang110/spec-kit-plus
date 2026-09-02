Trigger: Before creating or revising the current visual concept.
Purpose: Resolve the highest-impact design ambiguity one question at a time and persist a usable design brief.
Preserved Contract: Ground recommendations in product context, keep unanswered questions open, and do not advance past material ambiguity.

# Design discovery dialogue

Use this reference before creating or revising a visual prototype.

## Begin from evidence

1. Inspect the current product, design contracts, real content, supplied
   references, target platforms, and known user constraints.
2. State a short `design_read`: product subject, audience, single job, likely
   visual/interaction character, and the evidence behind that reading.
3. Record confidence and the few missing decisions that could materially alter
   hierarchy, navigation, density, interaction, platform fit, accessibility, or
   the approval boundary.
4. Never ask for information already available in the repository or supplied
   context. The first question must demonstrate that the context was read.

## Ask one consequential question

- Keep exactly one active question. Ask the highest-leverage unresolved
  decision, not the easiest item on a checklist.
- Explain why the answer changes the design. Offer a concrete recommendation
  and two or three bounded choices when that reduces effort for the user.
  These are 2-3 textual choices only: they calibrate the one current concept
  during concept-calibration and must not become three full boards, three
  unrelated HTML concepts, or a silent profile expansion.
- Include the agent's current guess when evidence supports one. Make the
  assumption visible instead of silently designing around it.
- If the user asks for context, examples, or trade-offs, answer that request and
  re-ask the same decision more clearly. Do not advance past an unanswered
  question.
- Record the answer and its affected `DS-*` decisions in the brief. Do not store
  a transcript.

## Stop questioning at the right time

Move to a concept only when the agent can explain the experience to another
designer without inventing product facts: subject, audience, single job,
platform/input modes, content, hierarchy, critical states, adaptation strategy,
must-preserve boundaries, and a testable definition of satisfaction.

Do not manufacture questions after the brief is sufficient. State remaining
low-risk assumptions and proceed. Use a visual artifact only when seeing the
answer will be clearer than discussing it in text.

## Approval language

Treat only an explicit approval of the named round as approval. Praise,
acknowledgment, silence, or a request for explanation is not approval. If the
user is dissatisfied, keep the same direction open and move to critique and
revision.

If the user explicitly confirms the named visual direction before formal
approval, record that as direction-confirmed only after the runtime
direction-confirm sidecar exists. Do not call direction-confirm from lint or
agent confidence alone. Direction-confirmed is non-consumable: it does not
approve the design, does not bind `spec-contract.json`, and does not let Plan
or Implement consume the UI direction.

Sources informing this workflow:

- https://github.com/obra/superpowers/blob/main/skills/brainstorming/SKILL.md
- https://github.com/borhen68/SkillEngine/blob/main/skills/interview-me/SKILL.md
