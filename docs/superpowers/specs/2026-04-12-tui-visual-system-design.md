# TUI Visual System Design

**Date:** 2026-04-12  
**Status:** Proposed  
**Owner:** Codex

## Summary

This design defines a unified terminal UI language for Spec Kit Plus.

The immediate trigger is visual inconsistency and poor alignment in current output, especially the boxed question-card style that uses right-side `|` borders. Those borders break visually when lines wrap, look uneven across terminal widths, and make the interaction feel heavier than necessary.

The new direction is:

- remove right-side borders
- avoid closed ASCII boxes for primary interaction patterns
- keep left-side emphasis where it adds clarity
- use spacing, headings, status labels, and section hierarchy instead of full-character frames
- keep the overall look restrained, but allow strong emphasis for important states, warnings, and next steps

This is a deep TUI design pass, not a one-off prompt cleanup. It should unify:

- `specify` interactive questioning
- `clarify` compatibility flow
- `spec-extend`
- `explain`
- CLI status and next-step panels in `specify init`
- warning, error, success, and enhancement surfaces in Rich-rendered CLI output

## Problem

Current TUI output has three main issues:

1. **Visual brittleness**
   - Right-side borders and full ASCII frames rely on line-length discipline.
   - Once content wraps, the output looks misaligned and low quality.

2. **Fragmented visual language**
   - Template-driven question cards, explanation surfaces, and Rich panels do not feel like one system.
   - Some outputs look like rigid ASCII forms, others like generic Rich panels.

3. **Weak hierarchy**
   - Important states and next steps compete visually with ordinary text.
   - Some panels over-emphasize everything, while others under-emphasize what matters.

## Goals

- Remove right-side border dependence from core interaction surfaces.
- Replace boxed-card alignment with a more robust, width-tolerant layout system.
- Create one shared TUI design language across template-driven and Rich-rendered output.
- Keep the overall look clean and restrained.
- Allow strong emphasis for important items:
  - current stage
  - current status
  - risks
  - errors
  - next actions
- Improve readability across narrow and wide terminal widths.
- Make the output feel deliberate and modern rather than ASCII-heavy.

## Non-Goals

- Do not introduce decorative or playful terminal art for its own sake.
- Do not redesign workflow semantics in this pass.
- Do not replace Markdown or Rich with a different rendering stack.
- Do not optimize for pixel-perfect alignment across every terminal font; optimize for robust structure instead.

## Design Direction

The approved direction is:

- overall style: restrained
- emphasis: allowed for anything important
- frame treatment: keep optional left-side emphasis, remove right-side borders
- preferred system: open layout, not closed boxes

This leads to a design system based on **open blocks with single-side emphasis**.

## Core Principles

### 1. Open, Not Closed

Primary interaction surfaces should not use full rectangular borders.

Use:

- heading rows
- left-side emphasis lines
- whitespace separation
- inline status labels

Avoid:

- right-side `|`
- closing ASCII rectangles around long content
- layouts that depend on every line reaching the same width

### 2. Hierarchy Over Decoration

Information should be organized by:

- title size/weight
- section ordering
- spacing
- labels
- grouped content blocks

The design should not rely on heavy borders to communicate importance.

### 3. Strong Emphasis for Important State

The system should allow stronger visual treatment for:

- stage title
- current status
- warnings and risks
- explicit next steps
- compatibility mode

Ordinary explanatory text should remain calm so the emphasized blocks have contrast.

### 4. Width Tolerance

Layouts must still look intentional when:

- the terminal is narrow
- text wraps naturally
- translated or user-generated content is longer than expected

That means the layout system must prefer vertical structure over horizontal closure.

## Component System

The visual system is built from six component families.

### 1. Stage Header

Purpose:
- identify where the user is in the workflow

Structure:
- strong title
- optional stage counter or short subtitle
- optional thin divider or spacing below

Rules:
- no surrounding box
- may use a top-aligned accent or header line
- should be visually stable even with wrapped subtitles

### 2. Status Block

Purpose:
- communicate current state quickly

Examples:
- ready
- compatibility
- blocked
- warning
- complete

Structure:
- left-side emphasis
- status label or chip
- one to three short lines of summary

Rules:
- stronger emphasis than body text
- not a closed panel
- should be easy to scan before reading detail

### 3. Explanation Block

Purpose:
- hold longer plain-language interpretation

Used in:
- `explain`
- current-understanding recaps in `specify`
- migration notes or compatibility notes

Structure:
- section title
- grouped paragraphs or bullets
- optional inline subheadings

Rules:
- calm presentation
- no box enclosure
- left-side emphasis optional, not mandatory

### 4. Risk Block

Purpose:
- isolate unresolved items or important cautions

Structure:
- stronger left accent
- short title
- concise content list

Rules:
- more prominent than ordinary explanation
- separate from the main narrative
- should never be visually confused with success/ready state

### 5. Option List

Purpose:
- present choices in `specify` and related flows

Structure:
- question header
- short prompt
- optional example
- recommended item callout
- option rows
- reply instruction

Rules:
- no closed ASCII card
- no right border
- recommendation must stand out without dominating the whole block
- options must remain readable after wrapping

### 6. Next-Step Block

Purpose:
- tell the user what to do next

Structure:
- short `Next` label or equivalent
- one command or action
- one-line explanation
- optional secondary actions

Rules:
- high emphasis
- compact
- command should be the visual focal point

## Surface-by-Surface Application

### `specify`

Current issue:
- the question-card protocol still reads like a boxed terminal form

Change:
- convert to open question blocks
- preserve:
  - question counter
  - one-sentence prompt
  - example row
  - recommended answer
  - reply instruction
- remove:
  - right-side border dependence
  - box-closure aesthetic

### `clarify`

Current role:
- compatibility bridge

Change:
- visually present it as a compatibility mode surface
- compatibility state should be strongly signaled
- the rest of the layout should match `specify` and `spec-extend`

### `spec-extend`

Change:
- use explanation + risk + next-step blocks
- reflect that this is enhancement work on an existing spec package
- emphasize what changed and why

### `explain`

Change:
- become the cleanest expression of the new visual system
- layout should center on:
  - stage header
  - status block
  - explanation body
  - risk block
  - next-step block

This command should feel like a terminal briefing, not an ASCII card.

### `specify init` and Rich CLI panels

Current issue:
- Rich panels are useful but not visually aligned with template-driven TUI

Change:
- unify panel tone with the new system
- reduce heavy boxed feeling where practical
- standardize:
  - title phrasing
  - emphasis placement
  - next-step presentation
  - enhancement block presentation

## Visual Rules

### Border Rules

- right-side borders: disallowed for primary TUI cards
- full ASCII rectangles: disallowed for primary interaction cards
- left-side emphasis: allowed and encouraged where useful
- Rich boxed panels: allowed selectively in CLI infrastructure, but should trend toward lighter presentation and consistent hierarchy

### Emphasis Rules

Allowed emphasis tools:

- color
- weight
- status labels
- left accents
- symbolic markers where helpful

Do not:

- emphasize every section equally
- use multiple competing emphasis styles in the same block
- make the interface visually noisy

### Spacing Rules

- adjacent semantic blocks must have visible separation
- titles should not collide with body content
- response instructions should sit apart from options
- next steps should never be buried in paragraph text

### Copy Rules

- body text should stay direct and calm
- emphasized blocks should be shorter than ordinary narrative blocks
- warnings and next steps should avoid bloated prose
- explanation sections can be longer, but must stay segmented

## Implementation Scope

This design applies to two implementation layers.

### Layer 1: Template-Driven Surfaces

Files expected to change:

- `templates/commands/specify.md`
- `templates/commands/clarify.md`
- `templates/commands/spec-extend.md`
- `templates/commands/explain.md`

### Layer 2: Rich CLI Surfaces

Primary file expected to change:

- `src/specify_cli/__init__.py`

Key panels to normalize:

- next-step panels
- enhancement panels
- warning and error panels
- status or environment panels where relevant

## Testing and Contract Strategy

This design should be locked with contract-level tests, not overly brittle copy checks.

Tests should verify:

- right-side box framing is no longer the expected structure for primary interaction cards
- open-layout questioning is used for `specify`
- `explain` has the expected structural sections
- next-step surfaces remain emphasized and distinct
- compatibility messaging remains visually distinct in `clarify`

Tests should avoid:

- exact whitespace snapshots unless structure truly depends on them
- overfitting to a single sentence wording when the design concern is structural

## Risks

### Risk 1: Partial adoption

If only some surfaces adopt the new system, the UI will look more inconsistent than before.

Mitigation:
- define the design contract first
- apply it to the full core interaction family

### Risk 2: Overcorrection

Removing all framing without replacing hierarchy could make the output feel flat.

Mitigation:
- keep left-side emphasis and strong state blocks
- rely on hierarchy, not minimalism alone

### Risk 3: Test brittleness

TUI tests can become copy-locked too easily.

Mitigation:
- test structure and semantics
- avoid exact wording when not essential

## Recommendation

Proceed with a deep TUI design pass using the **open, single-side emphasis** system.

Implementation order:

1. write this design contract
2. update template-driven surfaces
3. update Rich CLI surfaces
4. add structural tests to prevent regression

## Decision

Adopt the following design contract:

- remove right-side borders from primary TUI cards
- stop using closed ASCII boxes for core interactive surfaces
- keep optional left-side emphasis
- use restrained overall styling
- allow strong emphasis for anything important
- unify `specify`, `clarify`, `spec-extend`, `explain`, and CLI next-step/status surfaces under one visual language
