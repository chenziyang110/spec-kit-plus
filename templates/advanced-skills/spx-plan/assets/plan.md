# Implementation Plan: {{feature_name}}

## Design Summary

## Repository Impact

## Interfaces and State

## UI Design Adoption

- Work type, surface type, and platforms:
- Subject, audience, and single job:
- Visual/content/interaction theses and signature:
- Approved project-level visual reference and direction ID:
- Reference intents and real content/image plans:
- Design and UI brief sources:
- Tokens/components and planned extensions:
- Interaction matrix: [surface; input; trigger; feedback/state/context/recovery expectation]
- Editing matrix: [input methods; composition; paste/autofill; selection/caret; formatting; validation; dirty/persistence; undo/redo; conflict; read-only/disabled; submission]
- Data-state matrix: [empty and populated plus applicable loading/partial/error/permission/offline/pending/success]
- Accessibility matrix: [semantics; reading/focus order; keyboard/drag alternative; announcement; target; contrast; zoom/reflow; forced colors; alternatives]
- Navigation matrix: [hierarchy; entry/destination; trigger; back/close; deep link; interruption recovery; landmarks]
- Content matrix: [CTA and state copy; action; trust/privacy; content limits; localization/RTL/date/number/time zone]
- Motion contract: [purpose; trigger/response; duration/easing; interruption; reduced motion; feedback thresholds]
- Usability validation: [risk; methods; critical tasks; success criteria; required target-user human review]
- Component interaction/data/governance: [variants; content constraints; semantic tokens; reuse/extend/new; iconography]
- Responsive/accessibility rules: [target/state; adaptation; continuous stretch behavior; overflow behavior; active-context preservation]
- Required motion moments, tokens, and reduced-motion equivalents:
- Fidelity and must-preserve constraints:
- Real entry points and risk-based input × data × size structure/visual/runtime evidence:
- Visual comparison, deviations, or human-review boundary:

Preserve exact `interaction_matrix`, `editing_matrix`, `data_state_matrix`,
`accessibility_matrix`, `navigation_matrix`, `content_matrix`,
`motion_contract`, and `usability_validation` values in the machine Plan
contract. Use risk-based or pairwise combinations, not an unbounded Cartesian
product; automation/screenshots cannot replace target-user usability review.

## Compatibility, Migration, and Recovery

## Operational Entrypoint Outcome Design

| Outcome / CA | Producer result | Consumer / transition | Interaction policy | Request retention | Retry identity | Cancel behavior | Validation |
| --- | --- | --- | --- | --- | --- | --- | --- |
| OUT-### / CA-### | [live result ref] | [owner and state/substate] | [owner and policy] | [retention rule] | [identity rule] | [observable result] | [real-entrypoint evidence] |

## Verification Strategy

## Risks and Decisions

## Conditional Research and Artifacts
