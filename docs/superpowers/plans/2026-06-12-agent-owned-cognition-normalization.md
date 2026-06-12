# Agent-Owned Cognition Normalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make project cognition surface a mechanical `agent_normalization` reminder and make every affected workflow teach that the agent, not the CLI, owns semantic normalization.

**Architecture:** Add a small Go diagnostic object to `project-cognition lexicon` that is omitted unless a usable alias catalog exists and raw matching needs agent interpretation. Then tighten shared workflow prompts and regression tests so `score=0`, CJK, mixed CJK/ASCII, colloquial, and symptom-first prompts drive agent-written `semantic_intake` instead of runtime translation. Keep project cognition advisory: the CLI provides route vocabulary, while live source reads prove behavior.

**Tech Stack:** Go `project-cognition` runtime, Markdown command templates/passive skills, Python pytest template and integration tests, Go unit tests.

---

## Reference Spec

- `docs/superpowers/specs/2026-06-12-agent-owned-cognition-normalization-design.md`
- Related: `docs/superpowers/specs/2026-06-02-shared-semantic-cognition-intake-design.md`
- Related: `docs/superpowers/specs/2026-06-03-cognition-intake-experience-alignment-design.md`

## File Structure

Runtime diagnostic:

- Modify `tools/project-cognition/internal/query/lexicon.go`
  - Add `AgentNormalizationDiagnostic`.
  - Add an optional `agent_normalization` field on `LexiconPayload`.
  - Add mechanical trigger helpers for CJK/mixed CJK+ASCII and zero-match/no-coverage cases.
- Modify `tools/project-cognition/internal/query/query_test.go`
  - Add tests for zero positive matches, CJK with positive raw matches, omitted diagnostic on ordinary raw matches, and no invented concepts.

Shared workflow and generated guidance:

- Modify `templates/command-partials/common/context-loading-gradient.md`
- Modify `templates/command-partials/common/planning-context-loading-gradient.md`
- Modify `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify `src/specify_cli/integrations/base.py`
- Modify direct command templates found by the required sweep, expected at least:
  - `templates/commands/analyze.md`
  - `templates/commands/checklist.md`
  - `templates/commands/clarify.md`
  - `templates/commands/debug.md`
  - `templates/commands/deep-research.md`
  - `templates/commands/discussion.md`
  - `templates/commands/fast.md`
  - `templates/commands/implement.md`
  - `templates/commands/map-build.md`
  - `templates/commands/map-scan.md`
  - `templates/commands/map-update.md`
  - `templates/commands/plan.md`
  - `templates/commands/prd-scan.md`
  - `templates/commands/quick.md`
  - `templates/commands/specify.md`
  - `templates/commands/tasks.md`

Docs and tests:

- Modify `README.md`
- Modify `PROJECT-HANDBOOK.md`
- Modify `templates/project-handbook-template.md`
- Modify `tests/test_map_runtime_template_guidance.py`
- Modify `tests/test_alignment_templates.py` when integration-rendered guidance needs a broader assertion home.
- Modify generated integration tests only if focused runs show rendered outputs missing the shared wording.

---

## Task 1: Confirm Affected Surfaces Before Editing

**Files:**
- Read-only: `templates/**`
- Read-only: `templates/passive-skills/**`
- Read-only: `src/**`
- Read-only: `scripts/**`
- Read-only: `tests/**`
- Read-only: `README.md`
- Read-only: `PROJECT-HANDBOOK.md`
- Read-only: `docs/**`

- [ ] **Step 1: Run the required sweep**

Run:

```powershell
rg -n "project-cognition lexicon|project-cognition query|Agent-owned semantic normalization|score=0|mixed-language|CJK|semantic_intake|agent_normalization" templates templates/passive-skills src scripts tests README.md PROJECT-HANDBOOK.md docs
```

Expected: command exits `0` and prints the current cognition guidance surfaces. Preserve this output in the implementation notes or commit message summary; it is the source of truth for which direct templates need wording updates.

- [ ] **Step 2: Check current git state**

Run:

```powershell
git status --short
```

Expected: either clean output or only known user-owned changes. Do not overwrite unrelated user changes.

---

## Task 2: Add Runtime Diagnostic Tests

**Files:**
- Modify: `tools/project-cognition/internal/query/query_test.go`

- [ ] **Step 1: Add zero-match diagnostic test**

Append this test near the existing lexicon catalog tests in `tools/project-cognition/internal/query/query_test.go`:

```go
func TestLexiconAgentNormalizationRequiredForZeroPositiveMatchesWithCatalog(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-normalization-zero",
		Kind:         "full",
		SourceCommit: "abc123",
		Nodes: []store.NodeImport{{
			ID:         "N-lifecycle-confirmation",
			Type:       "capability",
			Title:      "Lifecycle Confirmation Preview",
			Confidence: "verified",
			Attrs: map[string]any{
				"aliases": []any{"install lifecycle", "confirmation preview", "action plan preview"},
			},
		}},
	})

	payload, err := LexiconWithOptions(paths, LexiconInput{
		Intent: "debug",
		Query:  "payment ledger rounding",
		Limit:  10,
		Mode:   "catalog",
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.AgentNormalization == nil {
		t.Fatalf("AgentNormalization = nil, want required diagnostic")
	}
	if !payload.AgentNormalization.Required {
		t.Fatalf("AgentNormalization.Required = false, want true")
	}
	if payload.AgentNormalization.Action != "write_semantic_intake_from_alias_catalog" {
		t.Fatalf("AgentNormalization.Action = %q", payload.AgentNormalization.Action)
	}
	if !hasString(payload.AgentNormalization.Triggers, "zero_positive_matches") {
		t.Fatalf("AgentNormalization.Triggers = %#v, want zero_positive_matches", payload.AgentNormalization.Triggers)
	}
	if !hasString(payload.AgentNormalization.Triggers, "no_graph_candidate_matched_query") {
		t.Fatalf("AgentNormalization.Triggers = %#v, want no_graph_candidate_matched_query", payload.AgentNormalization.Triggers)
	}
	if len(payload.AliasCatalog) == 0 {
		t.Fatalf("AliasCatalog = %#v, want usable catalog", payload.AliasCatalog)
	}
}
```

- [ ] **Step 2: Add CJK positive-match diagnostic test**

Add this test after the zero-match test:

```go
func TestLexiconAgentNormalizationRequiredForCJKWithPositiveRawMatch(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-normalization-cjk",
		Kind:         "full",
		SourceCommit: "abc123",
		Nodes: []store.NodeImport{{
			ID:         "N-tui-install",
			Type:       "capability",
			Title:      "TUI Install Lifecycle",
			Confidence: "verified",
			Attrs: map[string]any{
				"aliases": []any{"tui install lifecycle", "install confirmation"},
			},
		}},
	})

	payload, err := LexiconWithOptions(paths, LexiconInput{
		Intent: "debug",
		Query:  "使用tui安装后确认弹窗不一样",
		Limit:  10,
		Mode:   "catalog",
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.MatchingProfile["positive_matches"] == 0 {
		t.Fatalf("positive_matches = 0, want raw match through embedded tui term")
	}
	if payload.AgentNormalization == nil {
		t.Fatalf("AgentNormalization = nil, want required diagnostic for mixed CJK/ASCII")
	}
	if !hasString(payload.AgentNormalization.Triggers, "cjk_or_mixed_language_query") {
		t.Fatalf("AgentNormalization.Triggers = %#v, want cjk_or_mixed_language_query", payload.AgentNormalization.Triggers)
	}
}
```

- [ ] **Step 3: Add omitted diagnostic test**

Add this test after the CJK positive-match test:

```go
func TestLexiconOmitsAgentNormalizationForPlainEnglishRawMatch(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-normalization-english",
		Kind:         "full",
		SourceCommit: "abc123",
		Nodes: []store.NodeImport{{
			ID:         "N-lifecycle-confirmation",
			Type:       "capability",
			Title:      "Lifecycle Confirmation Preview",
			Confidence: "verified",
			Attrs: map[string]any{
				"aliases": []any{"install lifecycle", "confirmation preview"},
			},
		}},
	})

	payload, err := LexiconWithOptions(paths, LexiconInput{
		Intent: "debug",
		Query:  "install lifecycle confirmation preview",
		Limit:  10,
		Mode:   "catalog",
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.AgentNormalization != nil {
		t.Fatalf("AgentNormalization = %#v, want omitted diagnostic", payload.AgentNormalization)
	}
}
```

- [ ] **Step 4: Run the focused Go tests and verify red**

Run:

```powershell
go test ./internal/query -run "TestLexiconAgentNormalizationRequired|TestLexiconOmitsAgentNormalization" -count=1
```

from:

```powershell
cd tools/project-cognition
```

Expected: FAIL because `LexiconPayload.AgentNormalization` is not defined.

---

## Task 3: Implement Runtime Diagnostic

**Files:**
- Modify: `tools/project-cognition/internal/query/lexicon.go`
- Test: `tools/project-cognition/internal/query/query_test.go`

- [ ] **Step 1: Add payload struct fields**

In `tools/project-cognition/internal/query/lexicon.go`, add this field to `LexiconPayload` after `AliasCatalogTruncated`:

```go
	AgentNormalization      *AgentNormalizationDiagnostic `json:"agent_normalization,omitempty"`
```

Add this struct after `LexiconPayload`:

```go
type AgentNormalizationDiagnostic struct {
	Required bool     `json:"required"`
	Reason   string   `json:"reason"`
	Triggers []string `json:"triggers"`
	Action   string   `json:"action"`
	Reminder string   `json:"reminder"`
}
```

- [ ] **Step 2: Set the diagnostic after missing coverage is finalized**

In `LexiconWithOptions`, after the existing `switch` that sets `payload.UnmappedIntent` and `payload.MissingCoverage`, add:

```go
	payload.AgentNormalization = agentNormalizationDiagnostic(payload.AliasCatalog, positiveMatches, payload.MissingCoverage, text)
```

Keep this after the `switch` so the diagnostic can inspect `no_graph_candidate_matched_query`.

- [ ] **Step 3: Add mechanical helper functions**

Add these helpers near `classifyTermRune`:

```go
func agentNormalizationDiagnostic(aliasCatalog []map[string]any, positiveMatches int, missingCoverage []string, rawQuery string) *AgentNormalizationDiagnostic {
	if len(aliasCatalog) == 0 {
		return nil
	}
	triggers := []string{}
	if positiveMatches == 0 {
		triggers = append(triggers, "zero_positive_matches")
	}
	if hasStringValue(missingCoverage, "no_graph_candidate_matched_query") {
		triggers = append(triggers, "no_graph_candidate_matched_query")
	}
	if queryHasCJKOrMixedCJKASCII(rawQuery) {
		triggers = append(triggers, "cjk_or_mixed_language_query")
	}
	if len(triggers) == 0 {
		return nil
	}
	return &AgentNormalizationDiagnostic{
		Required: true,
		Reason:   "raw_terms_did_not_match_project_aliases",
		Triggers: uniqueStrings(triggers),
		Action:   "write_semantic_intake_from_alias_catalog",
		Reminder: "Do not stop at score=0. Translate user language into project vocabulary using the alias catalog.",
	}
}

func queryHasCJKOrMixedCJKASCII(text string) bool {
	hasCJK := false
	hasASCII := false
	for _, r := range text {
		if unicode.In(r, unicode.Han, unicode.Hiragana, unicode.Katakana, unicode.Hangul) {
			hasCJK = true
			continue
		}
		if r <= unicode.MaxASCII && (unicode.IsLetter(r) || unicode.IsDigit(r)) {
			hasASCII = true
		}
	}
	return hasCJK || (hasCJK && hasASCII)
}

func hasStringValue(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}
```

Note: `queryHasCJKOrMixedCJKASCII` intentionally returns true for CJK-only and mixed CJK/ASCII input. The spec names both as prompts needing agent-owned semantic normalization.

- [ ] **Step 4: Run focused Go tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/query -run "TestLexiconAgentNormalizationRequired|TestLexiconOmitsAgentNormalization" -count=1
```

Expected: PASS.

- [ ] **Step 5: Run full query package tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/query -count=1
```

Expected: PASS.

- [ ] **Step 6: Commit runtime diagnostic**

Run:

```powershell
git add tools/project-cognition/internal/query/lexicon.go tools/project-cognition/internal/query/query_test.go
git commit -m "feat: add agent normalization lexicon diagnostic"
```

Expected: commit succeeds.

---

## Task 4: Add Prompt And Template Regression Tests

**Files:**
- Modify: `tests/test_map_runtime_template_guidance.py`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add shared guidance assertion**

In `tests/test_map_runtime_template_guidance.py`, extend `test_shared_project_cognition_partials_assign_semantic_normalization_to_agent` or add this sibling test:

```python
def test_shared_project_cognition_partials_explain_agent_normalization_diagnostic() -> None:
    required_terms = (
        "agent_normalization",
        "required=true",
        "write_semantic_intake_from_alias_catalog",
        "omitted",
        "required=false",
        "cjk or mixed cjk/ascii",
        "positive raw lexical matches",
        "agent still owns translation",
        "not a route decision",
    )
    for path in [
        "templates/command-partials/common/context-loading-gradient.md",
        "templates/command-partials/common/planning-context-loading-gradient.md",
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
        "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
    ]:
        content = _compact(_read(path).lower())
        for term in required_terms:
            assert term in content, f"{path} missing agent_normalization guidance term: {term}"
```

- [ ] **Step 2: Add direct workflow assertion**

In `tests/test_map_runtime_template_guidance.py`, add:

```python
def test_cognition_workflows_preserve_agent_normalization_diagnostic_guidance() -> None:
    required_terms = (
        "agent_normalization",
        "write_semantic_intake_from_alias_catalog",
        "omitted",
        "required=false",
        "cjk or mixed cjk/ascii",
        "positive raw lexical matches",
        "agent still owns translation",
    )
    for name in COGNITION_INTAKE_COMMANDS:
        content = read_template(f"templates/commands/{name}").lower()
        for term in required_terms:
            assert term in content, f"{name} missing agent_normalization term {term}"
```

If `COGNITION_INTAKE_COMMANDS` is not imported in this file, reuse the existing constant in the file rather than creating a second list.

- [ ] **Step 3: Add docs assertion**

In `tests/test_alignment_templates.py`, add:

```python
def test_docs_explain_agent_as_brain_cli_as_tool_boundary() -> None:
    for path in ["README.md", "PROJECT-HANDBOOK.md", "templates/project-handbook-template.md"]:
        content = Path(path).read_text(encoding="utf-8").lower()
        assert "agent_normalization" in content, path
        assert "agent" in content and "semantic" in content, path
        assert "cli" in content and "tool" in content, path
        assert "not a route decision" in content, path
```

Use the existing file-reading helper in `tests/test_alignment_templates.py` if one is already present.

- [ ] **Step 4: Run focused template tests and verify red**

Run:

```powershell
uv run pytest tests/test_map_runtime_template_guidance.py tests/test_alignment_templates.py -q
```

Expected: FAIL because templates and docs do not yet mention `agent_normalization` semantics.

---

## Task 5: Update Shared Prompt Guidance And Docs

**Files:**
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/command-partials/common/planning-context-loading-gradient.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: direct `templates/commands/*.md` found in Task 1 sweep
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`

- [ ] **Step 1: Add shared diagnostic wording to both common partials**

In both common context-loading partials, replace the current agent-owned normalization paragraph with wording that includes this exact contract:

```markdown
Agent-owned semantic normalization is mandatory. The raw lexicon ranking is only a bootstrap for retrieving the alias catalog and candidate universe; it is not the route decision. Treat `agent_normalization.required=true` as a non-intelligent CLI reminder to write `semantic_intake` from the alias catalog. If `agent_normalization` is omitted, treat it as `required=false`; omission does not make raw lexical ranking authoritative. When `agent_normalization.required=true`, raw `concept_candidates` are all `score=0`, or the prompt is localized, mixed-language, CJK, colloquial, or symptom-first, do not stop at the raw score. CJK or mixed CJK/ASCII input still requires agent normalization even when positive raw lexical matches exist, because embedded project tokens do not translate the surrounding user language. Extract project terms such as command names, UI labels, file stems, state names, adapter names, and skill or package identifiers from the user's wording and the alias catalog. Put those translated terms into `normalized_query`, `alias_interpretations`, `intent_facets`, `expanded_queries`, and `repository_search_terms`, then select or reject concepts by facet coverage. `agent_normalization` is advisory guidance, not a route decision.
```

- [ ] **Step 2: Add passive skill wording**

Apply the same paragraph, adjusted for line wrapping only, to:

- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`

Keep the existing "Map points, code proves" wording near this paragraph.

- [ ] **Step 3: Update direct workflow templates**

For every direct command template from the Task 1 sweep that currently says:

```text
Agent-owned semantic normalization is mandatory: raw lexicon ranking is only a bootstrap, not the route decision; when every raw candidate is `score=0` or the prompt contains mixed-language or CJK text, extract embedded project terms from the user's wording and the alias catalog before selecting or rejecting concepts.
```

replace it with this shorter direct-template wording:

```text
Agent-owned semantic normalization is mandatory: raw lexicon ranking and `agent_normalization` are only bootstrap signals, not route decisions. If `agent_normalization.required=true`, every raw candidate is `score=0`, or the prompt is localized, mixed-language, CJK, colloquial, or symptom-first, write `semantic_intake` from the alias catalog before selecting or rejecting concepts. If `agent_normalization` is omitted, treat it as `required=false`; CJK or mixed CJK/ASCII input still requires agent normalization even when positive raw lexical matches exist because embedded project tokens do not translate the surrounding user language.
```

- [ ] **Step 4: Update generated integration base wording**

In `src/specify_cli/integrations/base.py`, update every cognition guidance string that contains `Agent-owned semantic normalization is mandatory` so generated commands receive the same direct-template wording from Step 3. Keep existing command macros unchanged, including concrete macros such as `{{specify-subcmd:project-cognition lexicon --intent plan --query="$ARGUMENTS" --mode catalog --format json}}`.

- [ ] **Step 5: Update docs**

In `README.md`, `PROJECT-HANDBOOK.md`, and `templates/project-handbook-template.md`, add one compact sentence near the existing alias-first project cognition description:

```markdown
When `project-cognition lexicon` returns `agent_normalization.required=true`, agents treat it as a non-intelligent CLI reminder to write `semantic_intake` from the alias catalog; when the field is omitted, treat it as `required=false`, not as proof that raw lexical ranking is authoritative. CJK or mixed CJK/ASCII prompts still require agent-owned translation even if embedded project terms produce positive raw lexical matches.
```

- [ ] **Step 6: Run focused template/docs tests**

Run:

```powershell
uv run pytest tests/test_map_runtime_template_guidance.py tests/test_alignment_templates.py -q
```

Expected: PASS.

- [ ] **Step 7: Run generated integration tests if base renderer changed**

Run:

```powershell
uv run pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit guidance updates**

Run:

```powershell
git add templates src README.md PROJECT-HANDBOOK.md tests
git commit -m "docs: teach agent-owned cognition normalization"
```

Expected: commit succeeds.

---

## Task 6: Final Runtime And Cross-Surface Verification

**Files:**
- No new source edits expected.
- Read: all changed files from Tasks 2 through 5.

- [ ] **Step 1: Run Go runtime tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/query ./internal/cli -count=1
```

Expected: PASS.

- [ ] **Step 2: Run focused Python regression tests**

Run from repository root:

```powershell
uv run pytest tests/test_map_runtime_template_guidance.py tests/test_alignment_templates.py tests/test_debug_template_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py -q
```

Expected: PASS.

- [ ] **Step 3: Run integration rendering tests touched by guidance**

Run:

```powershell
uv run pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py -q
```

Expected: PASS.

- [ ] **Step 4: Inspect final diff**

Run:

```powershell
git diff --stat HEAD
git diff --check
```

Expected: `git diff --check` exits `0`. The diff should show only runtime diagnostic, tests, prompt guidance, and docs related to agent-owned cognition normalization.

- [ ] **Step 5: Confirm working tree**

Run:

```powershell
git status --short
```

Expected: clean output after all task commits.

## Implementation Notes

- Do not add Chinese-to-English synonym maps, vector search, or runtime semantic selection.
- Do not create synthetic candidates for unmatched terms.
- Do not treat `agent_normalization` as readiness. Readiness and runtime agreement remain primary.
- `agent_normalization` should only be present when required. Omission means `required=false`.
- CJK-only and mixed CJK/ASCII prompts both require agent normalization when a usable alias catalog exists.
- Positive raw lexical matches do not waive agent normalization for CJK/mixed prompts.
