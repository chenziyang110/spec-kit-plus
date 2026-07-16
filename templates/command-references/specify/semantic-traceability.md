Trigger: during requirement discovery, ambiguity resolution, semantic decomposition, approach selection, or section approval.

Purpose: preserve clarification cadence, semantic traceability, capability decomposition, and approach approval behavior.

Preserved Contract: one-question cadence, semantic term decisions, approach comparison, scope-reduction confirmation, and section approval gates remain mandatory.

## Clarification Loop

- The user's text is the starting point, not the finished requirement package. Analyze the whole feature first and produce a planning-ready requirement package, not a surface summary.
- Run the anti-surface warning signs check before treating the request as planning-ready. Words like "simple", "intuitive", "robust", or "clean" are not requirements when boundary conditions, failure behavior, or affected neighboring workflow remain unclear, when there is still no acceptance proof for how success will be judged, or when the proposed behavior may conflict with the current owning module or existing repository pattern.
- Do not release `Aligned: ready for plan` when the current understanding still depends on taste words, implicit defaults, untested assumptions, or missing behavior boundaries, failure handling, compatibility impact, and acceptance-shaping detail.
- Treat phrases such as "make it more intuitive", "handle permissions normally", "keep it compatible", "show an error if something goes wrong", "use the existing pattern", "it should feel fast", "just validate the data properly", "admins can handle the special cases", and "don't break existing clients" as prompts to convert the vague intent into concrete behavior, edge handling, compatibility scope, or acceptance evidence.
- Classify unresolved vague wording as a vague success standard, vague data rule, vague permission boundary, or vague compatibility claim. Terms such as "fast", "smooth", "easy", "clear", or "works well"; "valid", "clean", "normalized", or "properly formatted"; "normal permissions", "admin behavior", or "authorized users"; and "keep compatibility" or "don't break clients" require concrete acceptance-shaping details before planning handoff.
- Run an engineering-completeness gate for boundary-sensitive work. Capture the trigger/event source when behavior depends on a cross-component signal, payload, identifiers, ordering, or delivery contract, state lifecycle, retention, archival, or cleanup expectations, retry/dedup/idempotency expectations for async or event-driven behavior, user-visible failure, stale-state, or recovery behavior, configuration surface and when changes take effect, and observability or support evidence needed to diagnose failures.
- If the user already described the desired UX in natural language, preserve that product behavior while avoiding forcing a transport or browser-API choice unless the requirement truly demands it.
- Do not release for cross-boundary or event-driven features while the trigger or event source, retry, deduplication, idempotency, or replay expectations are still unknown.
- Conversation memory is not a valid handoff surface. An unknown is not an ignored value; record each unresolved planning-critical item as `resolve-now`, `resolve-by-evidence`, `defer-with-contract`, or `waive-with-risk`, and reopen upstream truth when the current specification depends on a missing or contradictory source.
- Ask one high-impact question at a time.
- Ask at most one unanswered high-impact question per message.
- Ask exactly one unresolved high-impact question per turn.
- A question is high-impact when its answer can change scope, acceptance, architecture, compatibility, security, data shape, external integration, UX behavior, migration path, or downstream planning.
- Run a high-impact ambiguity scan across targeted repository evidence and user-supplied references, examples, or linked material.
- Identify 3-5 planning-relevant gray areas before choosing the next single question.
- Derive gray areas from the combination of user intent, the project cognition runtime, and targeted repository evidence. Do not use generic labels like "UX", "behavior", or "data handling".
- Each gray area should be captured internally with: why the decision changes implementation or test shape, desired happy-path behavior, edge case or failure-path behavior, and compatibility, migration, or neighboring-workflow impact.
- Do not batch unrelated high-impact questions. Ask, receive the answer, update the understanding, then decide whether another question is still necessary.
- each clarification turn should contain at most one short checkpoint.
- Do not ask a second high-impact question before the first one is closed.
- Grouped questions are allowed only when the current domain is already narrowed to a local low-risk scope.
- Make the next question build directly on the user's most recent answer rather than resetting to generic prompts.
- If the user's answer remains vague, shallow, or contradictory, ask a targeted narrowing question, example, or recommendation. Do not accept long but still ambiguous answers as sufficient.
- Do not turn this into a freeform brainstorming workflow. Keep it as guided requirement discovery.
- Default to concise clarification turns. Do not restate the full current understanding after every answer. Save the full synthesis for the alignment-ready turn.
- Do not repeat the same question unless the user's answer changes the prior premise or explicitly asks to revisit it.
- If the runtime exposes separate progress/commentary and final reply channels, keep progress in commentary and ask the current clarification question in the final user-visible reply. The user should see the current clarification question exactly once.
- Before generating any clarification question, confirmation, or bounded selection, apply the `sp-auto` Recommended Default Continuation when `auto_default_recommendation: true` is active. If that gate does not auto-resolve the question, check whether a native structured question tool is available. If a native structured question tool is available, you must use it.
- When using a native structured question tool, map the same stage header plus topic label into the native header or title field.
- Do not render the textual fallback block when the native tool is available. Do not self-authorize textual fallback because the question seems simple. Only fall back after the native tool is unavailable or the tool call fails.
- Treat the shared open question block structure below as fallback-only text format guidance.
- Use this open question block structure in the user's current language when rendering the textual fallback block: stage header, question header, prompt, example, recommendation, options, and reply instruction.
- Keep recommendation and example scaffolding short and specific.
- Low-risk defaults may be adopted without interrupting the user, but record them as assumptions in `alignment.md`.
- If the user explicitly accepts unresolved risk, record the risk and use `Force proceed with known risks`; otherwise unresolved planning-critical ambiguity routes to `/sp.clarify`.

## Semantic Term Decomposition

- Decompose ambiguous product terms before writing the final spec.
- If the request contains 2 or more distinct deliverables, enhancements, or behavior changes that would independently change implementation or validation shape, decompose it into capabilities. Present the capability split before asking any detailed clarification question about one capability.
- Label that preview as the proposed capability split so the user can correct the grouping.
- Default to one spec with capability decomposition when the work still belongs to one coherent feature boundary.
- Help the user decompose it into bounded capabilities inside the same spec first.
- Only escalate to separate specs or clearly phased releases when one spec would no longer be coherent to plan or test.
- Do not jump straight into a detailed gray-area question while multiple sibling capabilities are still unsplit or unprioritized.
- confirm which capability should be clarified first while keeping the work in the current spec unless the user explicitly wants separate specs or phased release planning.
- Do not spend one clarification pass collecting requirements for multiple independent capabilities.
- If the request is already one bounded capability, say so briefly and continue inside the current spec.
- Use this section in `alignment.md` for high-value terms whose meanings could change the delivered product:

Use a simple row per term:

- Term: [ambiguous user term]
- Possible Meanings: [meaning A; meaning B; meaning C]
- Selected Meanings: [confirmed selected meanings]
- Excluded Meanings: [confirmed exclusions]
- User Confirmation: [who/when or missing]

- If selected or excluded meanings are missing user confirmation and the term is product-critical, keep the package out of planning-ready state.
- Scope reduction requires confirmation. Do not convert a broad request into an MVP, prototype, demo, or smaller delivery unless the user requested it or explicitly accepted the narrower version.

## Approach Comparison

- When this command runs with `auto_default_recommendation: true`, apply the `sp-auto` Recommended Default Continuation before every bounded question, approach comparison, or section approval gate. If one safe recommended/default answer exists, record it and continue instead of asking; if it is not safe to assume, keep the confirmation gate and include a self-unblock recommendation.
- Present two or three approaches before committing to the spec shape.
- For a requirement-shaping decision, switch into decision-fork mode and present 2-3 concrete options when the choice changes behavior, boundary, compatibility, or acceptance proof.
- Do not use this mode for implementation architecture brainstorming.
- For each approach, summarize product fit, implementation risk, user-visible trade-offs, compatibility impact, and verification implications.
- Recommend one approach and explain why it best preserves the user's stated intent.
- When this command is resumed through `sp-auto` with `auto_default_recommendation: true`, and the only blocked state is `approach_comparison_status: awaiting-user-confirmation` for a previously presented bounded choice, automatically choose the single explicitly recommended approach if it preserves the user's stated intent and does not narrow scope, defer or drop an upstream capability signal, waive a risk, or contradict explicit user input. Record `approach_comparison_status: auto-accepted-recommended`, the selected approach, and the reason in `workflow-state.md` or `alignment.md`, then continue.
- Under `auto_default_recommendation: true`, do not ask the user to reply `1`, `2`, or `3` when the single safe pending action is accepting that recommended approach.
- Scope reduction still requires explicit user confirmation. Out-of-scope conflicts still require explicit user confirmation. Unresolved planning-critical ambiguity still blocks planning readiness.
- If the user chooses a different approach, record that as a locked decision rather than re-litigating it later.

## Spec Section Approval

- Before final artifact release, present the intended spec section shape for user approval.
- The review preview must cover:
  - goal and users
  - confirmed scope
  - out-of-scope and deferred items
  - capability decomposition
  - acceptance proof
  - semantic term decisions
  - upstream signal dispositions
  - open questions or known risks
- When this command is resumed through `sp-auto` with `auto_default_recommendation: true`, and the only blocked state is section-shape confirmation with no requested changes and one safe recommended/default section shape, automatically approve that shape. Record `section_approval_status: auto-approved-recommended` and continue to artifact writing.
- Do not auto-approve a section shape that removes, narrows, defers, or drops user-requested scope, hides an unresolved planning-critical ambiguity, or resolves an out-of-scope conflict without explicit user confirmation.
- Under `auto_default_recommendation: true`, do not ask the user to reply `1`, `2`, or `3` when the single safe pending action is accepting that recommended section shape.
- If the user requests changes, update the working understanding before writing final artifacts.

**UI reference input handling**:
- Detect screenshots, HTML/CSS mockups, UI framework snippets, design exports, UI reference URLs or existing UI pages, and matching-language such as "make it like this" as UI reference input.
- Ask the user which fidelity mode applies when not already explicit: `approximate` (default), `high`, or `inspiration`.
- Use `choose_ui_reference_lane_dispatch(command_name="specify", snapshot, workload_shape)` and record `lane_mode: ui-reference-artifact`.
- For `approximate` and `high`, native subagents are required by default; if native subagents are unavailable, follow the decision from `choose_ui_reference_lane_dispatch` and proceed inline only when it returns a gated `leader-inline` fallback with explicit user approval recorded, otherwise block with the missing capability instead of guessing.
- For `inspiration`, inline fallback may proceed only after `choose_ui_reference_lane_dispatch` returns a gated `leader-inline` soft-risk decision with safe lane and contract-ready state satisfied.
- Dispatch the UI reference lane to write only `ui-reference-notes.md`, `ui-brief.md`, and optional `ui-target.html`.
- Validate that `ui-target.html`, when present, is static HTML/CSS only: single-file, low-dependency, no `<script>`, no inline event handlers such as `onclick`, no JS-driven behavior, no external CSS/JS, no CDN, no remote runtime dependencies, no production-source claim, and preserves information density over decorative polish.
- For `approximate` and `high`, activate the `Reference-Implementation` profile contract, require `Fidelity Requirements`, and persist canonical `required_evidence` terms: `reference source evidence`, `fidelity criteria`, `verification entry points`, `difference inventory`, and `accepted deviations`; for `high`, require a deviation log as an artifact form for `difference inventory` / `accepted deviations`.
- Persist only the canonical reference-evidence labels and current structured UI
  evidence kinds. Do not emit shorthand aliases or translate them downstream.
