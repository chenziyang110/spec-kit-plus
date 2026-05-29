# Graph-Backed Project Cognition Lexicon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `project-cognition lexicon` return graph-backed project concept candidates and make `project-cognition query` resolve selected concepts with generation provenance.

**Architecture:** Keep the existing `lexicon -> query_plan -> query` workflow, but move lexicon candidate construction from raw query token wrapping to active graph candidate loading. The Go runtime owns candidate IDs, generation provenance, matching, and concept resolution; shared templates and integration renderers teach agents to select from returned graph-backed concept candidates.

**Tech Stack:** Go 1.21, SQLite through `database/sql` and `modernc.org/sqlite`, Python 3.11+ integration generation, pytest, PowerShell, Markdown templates.

---

## Reference Spec

- `docs/superpowers/specs/2026-05-28-graph-backed-project-cognition-lexicon-design.md`

## Scope Decisions

- First implementation derives aliases at query time from already imported graph data: node title, node id, node type, node attrs, path index rows, evidence source paths, and evidence-backed observation summaries.
- Do not depend on `alias_index` or `symbol_index` population in this plan. Persisted alias index population can be added after this behavior is proven and must update scan/build/import contracts in the same change set.
- Keep `selected_concepts` and `rejected_concepts` as string arrays for compatibility.
- Add `concept_decisions` as the durable per-concept rationale field.
- Treat `--intent` as a ranking and bundle-shaping profile. All intents use the same graph-backed candidate universe.
- Use `concept:<active_generation_id>:<node_id>` as the first candidate ID format. Suffix forms can be accepted by the parser, but this plan does not require emitting alias/path suffix IDs.

## File Structure

Runtime contract and graph lookup:

- `tools/project-cognition/internal/query/query.go`: query plan fields, concept decision model, concept ID parsing, concept resolution, generation mismatch payloads.
- `tools/project-cognition/internal/query/lexicon.go`: graph-backed lexicon payload, candidate ranking, query-time alias derivation, matching profile, unmapped intent reporting.
- `tools/project-cognition/internal/query/query_test.go`: runtime tests for parsing, lexicon candidate generation, query concept resolution, and generation mismatch behavior.
- `tools/project-cognition/internal/store/store.go`: active graph candidate loader and active-node lookup helpers.
- `tools/project-cognition/internal/store/import_test.go`: store-level tests for candidate loader material from imported nodes, attrs, paths, evidence, and observations.
- `tools/project-cognition/internal/cli/cli_test.go`: CLI JSON contract smoke tests for top-level lexicon/query fields.

Shared generated workflow contract:

- `templates/command-partials/common/context-loading-gradient.md`: shared non-planning cognition flow.
- `templates/command-partials/common/planning-context-loading-gradient.md`: shared planning cognition flow.
- `templates/command-partials/common/navigation-check.md`: shared navigation checks.
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`: passive cognition gate.
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`: passive routing skill.
- `templates/commands/{specify,clarify,deep-research,plan,tasks,analyze,fast,quick,implement,debug,discussion,checklist,prd-scan,map-build}.md`: direct workflow text that mentions lexicon/query.
- `src/specify_cli/integrations/base.py`: generated command appenders that inject project cognition guidance after template processing.
- `src/specify_cli/integrations/**`: agent-specific templates that mention lexicon/query.

Regression tests:

- `tests/test_map_runtime_template_guidance.py`
- `tests/test_runtime_handbook_contract.py`
- `tests/test_alignment_templates.py`
- `tests/test_passive_skill_guidance.py`
- `tests/test_quick_template_guidance.py`
- `tests/test_fast_template_guidance.py`
- `tests/integrations/test_integration_base_markdown.py`
- `tests/integrations/test_integration_base_toml.py`
- `tests/integrations/test_integration_base_skills.py`
- `tests/integrations/test_integration_codex.py`
- `tests/test_extension_skills.py`

---

### Task 1: Add Query Plan Provenance And Per-Concept Decisions

**Files:**
- Modify: `tools/project-cognition/internal/query/query.go`
- Modify: `tools/project-cognition/internal/query/query_test.go`

- [ ] **Step 1: Add failing tests for the expanded query plan contract**

Append these tests to `tools/project-cognition/internal/query/query_test.go`:

```go
func TestParsePlanAcceptsConceptDecisionsAndGeneration(t *testing.T) {
	plan, err := ParsePlan(`{
		"raw_query": "GUI feels laggy",
		"lexicon_generation_id": "GEN-ui",
		"selected_concepts": ["concept:GEN-ui:N-gui"],
		"rejected_concepts": ["concept:GEN-ui:N-login"],
		"concept_decisions": [
			{
				"concept_id": "concept:GEN-ui:N-gui",
				"decision": "selected",
				"selection_reason": "GUI owns the whole surface described by the user.",
				"confidence": "high",
				"paths": ["src/gui/window.tsx"]
			},
			{
				"concept_id": "concept:GEN-ui:N-login",
				"decision": "rejected",
				"selection_reason": "Login is a GUI flow but the request is not authentication-specific.",
				"confidence": "medium",
				"risk": "over-narrowing"
			}
		],
		"reason": "Selected the whole GUI concept and rejected a narrower flow."
	}`, "")
	if err != nil {
		t.Fatal(err)
	}
	if plan.LexiconGenerationID != "GEN-ui" {
		t.Fatalf("LexiconGenerationID = %q, want GEN-ui", plan.LexiconGenerationID)
	}
	if plan.SelectionReason == "" {
		t.Fatal("SelectionReason was not populated from reason")
	}
	if len(plan.ConceptDecisions) != 2 {
		t.Fatalf("ConceptDecisions = %#v, want two decisions", plan.ConceptDecisions)
	}
	if got := plan.ConceptDecisions[0].Paths; len(got) != 1 || got[0] != "src/gui/window.tsx" {
		t.Fatalf("decision paths = %#v, want src/gui/window.tsx", got)
	}
}

func TestNormalizePlanBackfillsLegacyConceptDecisions(t *testing.T) {
	plan := NormalizePlan(Plan{
		SelectedConcepts: []string{"concept:GEN-ui:N-gui", "concept:GEN-ui:N-gui"},
		RejectedConcepts: []string{"concept:GEN-ui:N-login"},
		SelectionReason: "GUI is relevant; login is too narrow.",
	})

	if got := plan.SelectedConcepts; len(got) != 1 || got[0] != "concept:GEN-ui:N-gui" {
		t.Fatalf("SelectedConcepts = %#v", got)
	}
	if len(plan.ConceptDecisions) != 2 {
		t.Fatalf("ConceptDecisions = %#v, want selected and rejected compatibility decisions", plan.ConceptDecisions)
	}
	if plan.ConceptDecisions[0].Decision != "selected" {
		t.Fatalf("first decision = %#v, want selected", plan.ConceptDecisions[0])
	}
	if plan.ConceptDecisions[1].Decision != "rejected" {
		t.Fatalf("second decision = %#v, want rejected", plan.ConceptDecisions[1])
	}
}
```

- [ ] **Step 2: Run the failing tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/query -run "TestParsePlanAcceptsConceptDecisionsAndGeneration|TestNormalizePlanBackfillsLegacyConceptDecisions" -count=1
```

Expected: fail because `Plan` does not yet define `LexiconGenerationID` or `ConceptDecisions`.

- [ ] **Step 3: Add contract types and normalize compatibility fields**

In `tools/project-cognition/internal/query/query.go`, add these declarations near `type Plan`:

```go
const CandidateUniverseVersion = 1

type ConceptDecision struct {
	ConceptID       string   `json:"concept_id"`
	Decision        string   `json:"decision"`
	SelectionReason string   `json:"selection_reason,omitempty"`
	Confidence      string   `json:"confidence,omitempty"`
	Paths           []string `json:"paths,omitempty"`
	Risk            string   `json:"risk,omitempty"`
}
```

Change `Plan` to include the new fields while preserving every existing field:

```go
type Plan struct {
	RawQuery            string            `json:"raw_query,omitempty"`
	ExpandedQueries     []string          `json:"expanded_queries,omitempty"`
	Paths               []string          `json:"paths,omitempty"`
	PathHints           []string          `json:"path_hints,omitempty"`
	SelectedConcepts    []string          `json:"selected_concepts,omitempty"`
	RejectedConcepts    []string          `json:"rejected_concepts,omitempty"`
	ConceptDecisions    []ConceptDecision `json:"concept_decisions,omitempty"`
	LexiconGenerationID string            `json:"lexicon_generation_id,omitempty"`
	SelectionReason     string            `json:"selection_reason,omitempty"`
	Reason              string            `json:"reason,omitempty"`
}
```

Extend `NormalizePlan` so it deduplicates concept arrays and backfills `concept_decisions` from legacy arrays:

```go
func NormalizePlan(plan Plan) Plan {
	if len(plan.Paths) == 0 && len(plan.PathHints) > 0 {
		plan.Paths = append([]string{}, plan.PathHints...)
	}
	if plan.SelectionReason == "" && plan.Reason != "" {
		plan.SelectionReason = plan.Reason
	}
	plan.Paths = normalizePaths(plan.Paths)
	plan.PathHints = normalizePaths(plan.PathHints)
	plan.SelectedConcepts = normalizeStrings(plan.SelectedConcepts)
	plan.RejectedConcepts = normalizeStrings(plan.RejectedConcepts)
	plan.ConceptDecisions = normalizeConceptDecisions(plan.ConceptDecisions, plan.SelectedConcepts, plan.RejectedConcepts, plan.SelectionReason)
	return plan
}
```

Add these helpers below `normalizePaths`:

```go
func normalizeStrings(values []string) []string {
	seen := map[string]bool{}
	out := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	return out
}

func normalizeConceptDecisions(decisions []ConceptDecision, selected []string, rejected []string, summary string) []ConceptDecision {
	seen := map[string]bool{}
	out := make([]ConceptDecision, 0, len(decisions)+len(selected)+len(rejected))
	for _, decision := range decisions {
		decision.ConceptID = strings.TrimSpace(decision.ConceptID)
		decision.Decision = strings.TrimSpace(decision.Decision)
		decision.SelectionReason = strings.TrimSpace(decision.SelectionReason)
		decision.Confidence = strings.TrimSpace(decision.Confidence)
		decision.Risk = strings.TrimSpace(decision.Risk)
		decision.Paths = normalizePaths(decision.Paths)
		if decision.ConceptID == "" || decision.Decision == "" {
			continue
		}
		key := decision.ConceptID + "\x00" + decision.Decision
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, decision)
	}
	for _, conceptID := range selected {
		key := conceptID + "\x00selected"
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, ConceptDecision{
			ConceptID:       conceptID,
			Decision:        "selected",
			SelectionReason: summary,
		})
	}
	for _, conceptID := range rejected {
		key := conceptID + "\x00rejected"
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, ConceptDecision{
			ConceptID:       conceptID,
			Decision:        "rejected",
			SelectionReason: summary,
		})
	}
	return out
}
```

- [ ] **Step 4: Verify the query plan tests pass**

Run:

```powershell
cd tools/project-cognition
go test ./internal/query -run "TestParsePlanAcceptsConceptDecisionsAndGeneration|TestNormalizePlanBackfillsLegacyConceptDecisions|TestParsePlanNormalizesLegacyAliases" -count=1
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add tools/project-cognition/internal/query/query.go tools/project-cognition/internal/query/query_test.go
git commit -m "feat: add project cognition concept decision plan fields"
```

---

### Task 2: Add Active Graph Candidate Store Helpers

**Files:**
- Modify: `tools/project-cognition/internal/store/store.go`
- Modify: `tools/project-cognition/internal/store/import_test.go`

- [ ] **Step 1: Add failing store tests for graph-backed candidate material**

Append this test to `tools/project-cognition/internal/store/import_test.go`:

```go
func TestActiveConceptCandidateRowsDeriveGraphMaterial(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	input := validImportInput("GEN-ui")
	input.Evidence = []EvidenceImport{{
		ID:          "E-gui",
		SourceKind:  "source",
		SourcePath:  "src/gui/window.tsx",
		CommitSHA:   "abc123",
		Extractor:   "test",
		ContentHash: "hash-gui",
	}}
	input.Nodes = []NodeImport{{
		ID:          "N-gui",
		Type:        "capability",
		Title:       "GUI Shell",
		Confidence:  "verified",
		EvidenceIDs: []string{"E-gui"},
		Attrs: map[string]any{
			"aliases":            []any{"GUI", "desktop UI"},
			"domain":             "desktop",
			"owner":              "frontend",
			"route_hints":        []any{"src/gui"},
			"verification_hints": []any{"npm test -- gui"},
		},
	}}
	input.Observations = []ObservationImport{{
		ID:              "OBS-gui",
		ObservationType: "summary",
		Summary:         "GUI Shell owns frame rendering and input dispatch.",
		EvidenceIDs:     []string{"E-gui"},
	}}
	input.PathIndex = []PathIndexImport{{
		ID:         "P-gui",
		Path:       "src/gui/window.tsx",
		NodeID:     "N-gui",
		Relation:   "owns",
		Confidence: "verified",
		EvidenceID: "E-gui",
	}}
	if _, err := st.ImportGeneration(ctx, input); err != nil {
		t.Fatal(err)
	}

	rows, err := st.ActiveConceptCandidateRows(ctx, 25)
	if err != nil {
		t.Fatal(err)
	}
	if len(rows) != 1 {
		t.Fatalf("rows = %#v, want one candidate row", rows)
	}
	row := rows[0]
	if row.GenerationID != "GEN-ui" || row.NodeID != "N-gui" || row.Title != "GUI Shell" {
		t.Fatalf("row identity = %#v", row)
	}
	assertStringSliceContains(t, row.Paths, "src/gui/window.tsx")
	assertStringSliceContains(t, row.EvidenceIDs, "E-gui")
	assertStringSliceContains(t, row.EvidencePaths, "src/gui/window.tsx")
	assertStringSliceContains(t, row.ObservationSummaries, "GUI Shell owns frame rendering and input dispatch.")
	if !strings.Contains(row.AttrsJSON, "desktop UI") {
		t.Fatalf("AttrsJSON = %s, want attrs with alias material", row.AttrsJSON)
	}
}

func TestNodesForIDsUsesOnlyActiveGeneration(t *testing.T) {
	ctx := context.Background()
	st := openImportTestStore(t)
	defer st.Close()

	if _, err := st.ImportGeneration(ctx, validImportInput("GEN-old")); err != nil {
		t.Fatal(err)
	}
	next := validImportInput("GEN-new")
	next.Nodes[0].Title = "Current App"
	if _, err := st.ImportGeneration(ctx, next); err != nil {
		t.Fatal(err)
	}

	nodes, err := st.NodesForIDs(ctx, []string{"N-app"})
	if err != nil {
		t.Fatal(err)
	}
	if len(nodes) != 1 || nodes[0]["title"] != "Current App" {
		t.Fatalf("nodes = %#v, want current active generation node", nodes)
	}
}
```

Add this helper near `assertSnapshotIdentity`:

```go
func assertStringSliceContains(t *testing.T, values []string, want string) {
	t.Helper()
	for _, value := range values {
		if value == want {
			return
		}
	}
	t.Fatalf("%#v does not contain %q", values, want)
}
```

- [ ] **Step 2: Run the failing store tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/store -run "TestActiveConceptCandidateRowsDeriveGraphMaterial|TestNodesForIDsUsesOnlyActiveGeneration" -count=1
```

Expected: fail because `ActiveConceptCandidateRows` and `NodesForIDs` are not defined.

- [ ] **Step 3: Add store helper types**

In `tools/project-cognition/internal/store/store.go`, add this type near `type Store`:

```go
type ConceptCandidateRow struct {
	GenerationID          string
	NodeID                string
	NodeType              string
	Title                 string
	Confidence            string
	AttrsJSON             string
	Paths                 []string
	EvidenceIDs           []string
	EvidencePaths         []string
	ObservationSummaries  []string
}
```

- [ ] **Step 4: Add active candidate loading and active-node lookup**

In `tools/project-cognition/internal/store/store.go`, add these methods after `NodesForPaths`:

```go
func (s *Store) ActiveConceptCandidateRows(ctx context.Context, limit int) ([]ConceptCandidateRow, error) {
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return nil, err
	}
	if generationID == "" {
		return []ConceptCandidateRow{}, nil
	}
	if limit <= 0 {
		limit = 200
	}
	rows, err := s.db.QueryContext(ctx, `
SELECT
	n.generation_id,
	n.id,
	n.type,
	n.title,
	n.confidence,
	n.attrs_json,
	COALESCE(group_concat(DISTINCT p.path), ''),
	COALESCE(group_concat(DISTINCT ne.evidence_id), ''),
	COALESCE(group_concat(DISTINCT e.source_path), ''),
	COALESCE(group_concat(DISTINCT o.summary), '')
FROM nodes n
LEFT JOIN path_index p
	ON p.generation_id = n.generation_id AND p.node_id = n.id
LEFT JOIN node_evidence ne
	ON ne.node_id = n.id
LEFT JOIN evidence e
	ON e.generation_id = n.generation_id AND e.id = ne.evidence_id
LEFT JOIN observation_evidence oe
	ON oe.evidence_id = ne.evidence_id
LEFT JOIN observations o
	ON o.generation_id = n.generation_id AND o.id = oe.observation_id
WHERE n.generation_id = ?
GROUP BY n.generation_id, n.id, n.type, n.title, n.confidence, n.attrs_json
ORDER BY n.id
LIMIT ?`, generationID, limit)
	if err != nil {
		return nil, fmt.Errorf("query active concept candidates: %w", err)
	}
	defer rows.Close()

	out := make([]ConceptCandidateRow, 0)
	for rows.Next() {
		var row ConceptCandidateRow
		var paths, evidenceIDs, evidencePaths, observations string
		if err := rows.Scan(
			&row.GenerationID,
			&row.NodeID,
			&row.NodeType,
			&row.Title,
			&row.Confidence,
			&row.AttrsJSON,
			&paths,
			&evidenceIDs,
			&evidencePaths,
			&observations,
		); err != nil {
			return nil, fmt.Errorf("scan active concept candidate: %w", err)
		}
		row.Paths = splitSQLiteList(paths)
		row.EvidenceIDs = splitSQLiteList(evidenceIDs)
		row.EvidencePaths = splitSQLiteList(evidencePaths)
		row.ObservationSummaries = splitSQLiteList(observations)
		out = append(out, row)
	}
	return out, rows.Err()
}

func (s *Store) NodesForIDs(ctx context.Context, nodeIDs []string) ([]map[string]any, error) {
	generationID, err := s.ActiveGenerationID(ctx)
	if err != nil {
		return nil, err
	}
	if generationID == "" {
		return []map[string]any{}, nil
	}
	nodeIDs = normalizeStoreStrings(nodeIDs)
	if len(nodeIDs) == 0 {
		return []map[string]any{}, nil
	}
	out := make([]map[string]any, 0, len(nodeIDs))
	for _, nodeID := range nodeIDs {
		rows, err := s.db.QueryContext(ctx, `
SELECT DISTINCT n.id, n.type, n.title, COALESCE(p.path, '')
FROM nodes n
LEFT JOIN path_index p
	ON p.generation_id = n.generation_id AND p.node_id = n.id
WHERE n.generation_id = ? AND n.id = ?
ORDER BY p.path, n.id`, generationID, nodeID)
		if err != nil {
			return nil, fmt.Errorf("query node %s: %w", nodeID, err)
		}
		nodes, err := scanNodeRows(rows)
		if err != nil {
			return nil, err
		}
		out = append(out, nodes...)
	}
	return out, nil
}
```

Add these helpers below `scanNodeRows`:

```go
func splitSQLiteList(value string) []string {
	if value == "" {
		return []string{}
	}
	parts := strings.Split(value, ",")
	return normalizeStoreStrings(parts)
}

func normalizeStoreStrings(values []string) []string {
	seen := map[string]bool{}
	out := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value == "" || seen[value] {
			continue
		}
		seen[value] = true
		out = append(out, value)
	}
	return out
}
```

- [ ] **Step 5: Verify store helpers**

Run:

```powershell
cd tools/project-cognition
go test ./internal/store -run "TestActiveConceptCandidateRowsDeriveGraphMaterial|TestNodesForIDsUsesOnlyActiveGeneration|TestImportGenerationPublishesActiveIdentitySnapshot" -count=1
```

Expected: pass.

- [ ] **Step 6: Commit**

```powershell
git add tools/project-cognition/internal/store/store.go tools/project-cognition/internal/store/import_test.go
git commit -m "feat: load graph-backed project cognition candidates"
```

---

### Task 3: Replace Token-Only Lexicon With Graph-Backed Candidate Ranking

**Files:**
- Modify: `tools/project-cognition/internal/query/lexicon.go`
- Modify: `tools/project-cognition/internal/query/query_test.go`

- [ ] **Step 1: Add failing lexicon tests**

Append these tests to `tools/project-cognition/internal/query/query_test.go`:

```go
func TestLexiconReturnsGraphCandidatesWithoutInventedTermConcepts(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-ui",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-gui",
			SourceKind:  "source",
			SourcePath:  "src/gui/window.tsx",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-gui",
		}, {
			ID:          "E-login",
			SourceKind:  "source",
			SourcePath:  "src/auth/login.tsx",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-login",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-gui",
			Type:        "capability",
			Title:       "GUI Shell",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-gui"},
			Attrs: map[string]any{
				"aliases":            []any{"GUI", "desktop UI", "smoothness"},
				"domain":             "desktop",
				"owner":              "frontend",
				"verification_hints": []any{"npm test -- gui"},
			},
		}, {
			ID:          "N-login",
			Type:        "capability",
			Title:       "Login Flow",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-login"},
			Attrs:       map[string]any{"aliases": []any{"login", "auth"}},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-gui",
			Path:       "src/gui/window.tsx",
			NodeID:     "N-gui",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-gui",
		}, {
			ID:         "P-login",
			Path:       "src/auth/login.tsx",
			NodeID:     "N-login",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-login",
		}},
	})

	payload, err := Lexicon(paths, "debug", "The GUI feels laggy and not smooth", 10)
	if err != nil {
		t.Fatal(err)
	}
	if payload.ActiveGenerationID != "GEN-ui" || payload.LexiconGenerationID != "GEN-ui" {
		t.Fatalf("generation fields = %#v", payload)
	}
	if payload.CandidateUniverseVersion != CandidateUniverseVersion {
		t.Fatalf("CandidateUniverseVersion = %d", payload.CandidateUniverseVersion)
	}
	if len(payload.ConceptCandidates) == 0 {
		t.Fatal("ConceptCandidates is empty")
	}
	first := payload.ConceptCandidates[0]
	if first["concept_id"] != "concept:GEN-ui:N-gui" {
		t.Fatalf("first candidate = %#v, want GUI concept", first)
	}
	for _, candidate := range payload.ConceptCandidates {
		if strings.HasPrefix(candidate["concept_id"].(string), "term:") {
			t.Fatalf("lexicon invented term candidate: %#v", candidate)
		}
	}
	if payload.UnmappedIntent {
		t.Fatalf("UnmappedIntent = true with GUI graph candidate: %#v", payload)
	}
}

func TestLexiconReportsUnmappedIntentWhenNoGraphCandidateMatches(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-ui",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-gui",
			SourceKind:  "source",
			SourcePath:  "src/gui/window.tsx",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-gui",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-gui",
			Type:        "capability",
			Title:       "GUI Shell",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-gui"},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-gui",
			Path:       "src/gui/window.tsx",
			NodeID:     "N-gui",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-gui",
		}},
	})

	payload, err := Lexicon(paths, "implement", "payment settlement ledger rounding", 10)
	if err != nil {
		t.Fatal(err)
	}
	if !payload.UnmappedIntent {
		t.Fatalf("UnmappedIntent = false, payload = %#v", payload)
	}
	if !hasString(payload.MissingCoverage, "no_graph_candidate_matched_query") {
		t.Fatalf("MissingCoverage = %#v, want no_graph_candidate_matched_query", payload.MissingCoverage)
	}
	for _, candidate := range payload.ConceptCandidates {
		if strings.HasPrefix(candidate["concept_id"].(string), "term:") {
			t.Fatalf("lexicon invented term candidate: %#v", candidate)
		}
	}
}
```

Add this helper below `seedSplitBrainRuntime`:

```go
func seedReadyGraph(t *testing.T, paths rt.Paths, input store.ImportInput) {
	t.Helper()
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := st.ImportGeneration(context.Background(), input); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	generationID, err := st.ActiveGenerationID(context.Background())
	if err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if _, _, err := st.PublishRuntimeMetadata(context.Background(), generationID); err != nil {
		_ = st.Close()
		t.Fatal(err)
	}
	if err := st.Close(); err != nil {
		t.Fatal(err)
	}
	status := rt.DefaultStatus(paths)
	status.Status = "ok"
	status.Freshness = rt.ReadyFreshness
	status.Readiness = rt.ReadyReadiness
	status.RecommendedNextAction = "use_project_cognition"
	status.GraphReady = true
	status.ActiveGenerationID = generationID
	status.QueryContractVersion = 1
	status.UpdateContractVersion = 1
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
}

func hasString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}
```

- [ ] **Step 2: Run the failing lexicon tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/query -run "TestLexiconReturnsGraphCandidatesWithoutInventedTermConcepts|TestLexiconReportsUnmappedIntentWhenNoGraphCandidateMatches" -count=1
```

Expected: fail because current lexicon emits `term:` candidates and lacks generation fields.

- [ ] **Step 3: Add graph-backed lexicon payload fields**

In `tools/project-cognition/internal/query/lexicon.go`, replace `LexiconPayload` with:

```go
type LexiconPayload struct {
	Readiness                 string           `json:"readiness"`
	RecommendedNextAction     string           `json:"recommended_next_action"`
	Intent                    string           `json:"intent"`
	Query                     string           `json:"query"`
	ActiveGenerationID        string           `json:"active_generation_id,omitempty"`
	LexiconGenerationID       string           `json:"lexicon_generation_id,omitempty"`
	CandidateUniverseVersion  int              `json:"candidate_universe_version"`
	Terms                     []string         `json:"terms"`
	AvailableTerms            []string         `json:"available_terms"`
	ConceptCandidates         []map[string]any `json:"concept_candidates"`
	QueryPlanningContract     map[string]any   `json:"query_planning_contract"`
	CandidateUniverse         map[string]any   `json:"candidate_universe"`
	MatchingProfile           map[string]any   `json:"matching_profile"`
	UnmappedIntent            bool             `json:"unmapped_intent"`
	MissingCoverage           []string         `json:"missing_coverage"`
}
```

Keep `ConceptCandidates []map[string]any` for compatibility with current tests and generated consumers.

- [ ] **Step 4: Replace token-only construction with graph candidate ranking**

In `tools/project-cognition/internal/query/lexicon.go`, rewrite `Lexicon` so it:

1. Reads status as it does today.
2. Opens the existing store if it exists and is compatible.
3. Loads `st.ActiveConceptCandidateRows(context.Background(), max(limit*4, 50))`.
4. Builds query tokens with Unicode-aware matching.
5. Derives aliases from graph rows.
6. Scores candidates by query matches and intent profile.
7. Returns only graph-backed candidates.
8. Sets `unmapped_intent` and `missing_coverage` when no candidate scores above zero.

Use this function shape:

```go
func Lexicon(paths rt.Paths, intent, text string, limit int) (LexiconPayload, error) {
	if err := blockSplitBrainBaseline(paths); err != nil {
		return LexiconPayload{}, err
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		return LexiconPayload{}, err
	}
	if limit <= 0 {
		limit = 10
	}
	terms := termsFrom(text, limit)
	payload := LexiconPayload{
		Readiness:                status.Readiness,
		RecommendedNextAction:    status.RecommendedNextAction,
		Intent:                   intent,
		Query:                    text,
		ActiveGenerationID:       status.ActiveGenerationID,
		LexiconGenerationID:      status.ActiveGenerationID,
		CandidateUniverseVersion: CandidateUniverseVersion,
		Terms:                    terms,
		AvailableTerms:           []string{},
		ConceptCandidates:        []map[string]any{},
		CandidateUniverse: map[string]any{
			"counts":           map[string]any{"nodes": 0, "candidates": 0},
			"truncated":        false,
			"selection_window": limit,
		},
		MatchingProfile: map[string]any{
			"intent": intent,
			"uses_graph_backed_candidate_universe": true,
		},
		MissingCoverage: []string{},
		QueryPlanningContract: queryPlanningContract(),
	}

	st, err := store.OpenExisting(paths)
	if errors.Is(err, os.ErrNotExist) {
		payload.UnmappedIntent = true
		payload.MissingCoverage = []string{"project_cognition_database_missing"}
		return payload, nil
	}
	if err != nil {
		return LexiconPayload{}, err
	}
	defer st.Close()

	rows, err := st.ActiveConceptCandidateRows(context.Background(), maxInt(limit*4, 50))
	if err != nil {
		return LexiconPayload{}, err
	}
	candidates := rankConceptCandidates(rows, intent, text, terms)
	payload.CandidateUniverse = map[string]any{
		"counts": map[string]any{
			"nodes":      len(rows),
			"candidates": len(candidates),
		},
		"truncated":        len(candidates) > limit,
		"selection_window": limit,
	}
	if len(candidates) > limit {
		candidates = candidates[:limit]
	}
	payload.ConceptCandidates = candidateMaps(candidates)
	payload.AvailableTerms = availableCandidateTerms(candidates)
	if len(rows) > 0 && !hasPositiveCandidate(candidates) {
		payload.UnmappedIntent = true
		payload.MissingCoverage = []string{"no_graph_candidate_matched_query"}
	}
	if len(rows) == 0 {
		payload.UnmappedIntent = true
		payload.MissingCoverage = []string{"empty_graph_candidate_universe"}
	}
	return payload, nil
}
```

Add imports for `context`, `encoding/json`, `errors`, `fmt`, `os`, `path/filepath`, `sort`, and `unicode`.

- [ ] **Step 5: Add candidate derivation helpers**

In `tools/project-cognition/internal/query/lexicon.go`, add focused helpers:

```go
type rankedConceptCandidate struct {
	ConceptID         string
	NodeID            string
	Label             string
	Title             string
	TargetType        string
	NodeType          string
	Aliases           []string
	MatchedTerms      []string
	ColloquialMatches []string
	Paths             []string
	EvidenceIDs       []string
	Confidence        string
	Score             int
	Rank              int
	Domain            string
	Owner             string
	RouteHints         []string
	VerificationHints  []string
	DisambiguationHint string
	SelectionGuidance  string
}

func rankConceptCandidates(rows []store.ConceptCandidateRow, intent, query string, terms []string) []rankedConceptCandidate {
	candidates := make([]rankedConceptCandidate, 0, len(rows))
	for _, row := range rows {
		attrs := map[string]any{}
		_ = json.Unmarshal([]byte(row.AttrsJSON), &attrs)
		aliases := deriveAliases(row, attrs)
		matched := matchedTerms(query, terms, aliases, row)
		score := len(matched) * 10
		score += intentScore(intent, row, attrs)
		if strings.Contains(strings.ToLower(row.Title), "gui") && strings.Contains(strings.ToLower(query), "gui") {
			score += 5
		}
		candidates = append(candidates, rankedConceptCandidate{
			ConceptID:          fmt.Sprintf("concept:%s:%s", row.GenerationID, row.NodeID),
			NodeID:             row.NodeID,
			Label:              row.Title,
			Title:              row.Title,
			TargetType:         "graph_node",
			NodeType:           row.NodeType,
			Aliases:            aliases,
			MatchedTerms:       matched,
			ColloquialMatches:  matched,
			Paths:              row.Paths,
			EvidenceIDs:        row.EvidenceIDs,
			Confidence:         row.Confidence,
			Score:              score,
			Domain:             stringAttr(attrs, "domain"),
			Owner:              stringAttr(attrs, "owner"),
			RouteHints:          stringListAttr(attrs, "route_hints"),
			VerificationHints:   stringListAttr(attrs, "verification_hints"),
			DisambiguationHint: disambiguationHint(row, matched),
			SelectionGuidance:  selectionGuidance(score),
		})
	}
	sort.SliceStable(candidates, func(i, j int) bool {
		if candidates[i].Score == candidates[j].Score {
			return candidates[i].ConceptID < candidates[j].ConceptID
		}
		return candidates[i].Score > candidates[j].Score
	})
	for i := range candidates {
		candidates[i].Rank = i + 1
	}
	return candidates
}
```

Implement the helper bodies with these rules:

- `deriveAliases` includes row title, row node id, row node type, attrs `aliases`, attrs `domain`, attrs `owner`, attrs `workflow`, attrs `route`, each path, path base name without extension, path directory segments, evidence source paths, and observation summaries.
- `matchedTerms` lowercases all values and uses `strings.Contains` both ways for query/alias matching.
- `termsFrom` uses `unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_' || r == '-'` so non-ASCII letters are retained instead of discarded.
- `intentScore("implement", ...)` adds weight for source-like paths and verification hints.
- `intentScore("debug", ...)` adds weight for aliases or observations containing `symptom`, `log`, `render`, `latency`, `slow`, `lag`, `profile`, or `repro`.
- `intentScore("plan", ...)` adds weight for node types or aliases containing `capability`, `workflow`, `spec`, `plan`, or `architecture`.

Use these exact helper signatures so the rest of the runtime compiles:

```go
func candidateMaps(candidates []rankedConceptCandidate) []map[string]any {
	out := make([]map[string]any, 0, len(candidates))
	for _, candidate := range candidates {
		out = append(out, map[string]any{
			"concept_id":          candidate.ConceptID,
			"node_id":             candidate.NodeID,
			"label":               candidate.Label,
			"title":               candidate.Title,
			"target_type":         candidate.TargetType,
			"node_type":           candidate.NodeType,
			"aliases":             candidate.Aliases,
			"matched_terms":       candidate.MatchedTerms,
			"colloquial_matches":  candidate.ColloquialMatches,
			"paths":               candidate.Paths,
			"evidence_ids":        candidate.EvidenceIDs,
			"confidence":          candidate.Confidence,
			"score":               candidate.Score,
			"rank":                candidate.Rank,
			"domain":              candidate.Domain,
			"owner":               candidate.Owner,
			"route_hints":         candidate.RouteHints,
			"verification_hints":  candidate.VerificationHints,
			"disambiguation_hint": candidate.DisambiguationHint,
			"selection_guidance":  candidate.SelectionGuidance,
		})
	}
	return out
}

func availableCandidateTerms(candidates []rankedConceptCandidate) []string {
	values := []string{}
	for _, candidate := range candidates {
		values = append(values, candidate.Aliases...)
	}
	return normalizeStrings(values)
}

func hasPositiveCandidate(candidates []rankedConceptCandidate) bool {
	for _, candidate := range candidates {
		if candidate.Score > 0 {
			return true
		}
	}
	return false
}

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}

func deriveAliases(row store.ConceptCandidateRow, attrs map[string]any) []string {
	values := []string{row.Title, row.NodeID, row.NodeType}
	for _, key := range []string{"aliases", "domain", "owner", "workflow", "route"} {
		values = append(values, stringListAttr(attrs, key)...)
		if value := stringAttr(attrs, key); value != "" {
			values = append(values, value)
		}
	}
	values = append(values, row.Paths...)
	values = append(values, row.EvidencePaths...)
	values = append(values, row.ObservationSummaries...)
	for _, path := range append(append([]string{}, row.Paths...), row.EvidencePaths...) {
		values = append(values, pathAliases(path)...)
	}
	return normalizeStrings(values)
}

func pathAliases(path string) []string {
	path = filepath.ToSlash(strings.TrimSpace(path))
	if path == "" {
		return []string{}
	}
	aliases := []string{path}
	parts := strings.Split(path, "/")
	aliases = append(aliases, parts...)
	base := filepath.Base(path)
	aliases = append(aliases, base)
	aliases = append(aliases, strings.TrimSuffix(base, filepath.Ext(base)))
	return normalizeStrings(aliases)
}

func matchedTerms(query string, terms []string, aliases []string, row store.ConceptCandidateRow) []string {
	normalizedQuery := normalizeMatchText(query)
	values := append(append([]string{}, aliases...), row.Title, row.NodeID, row.NodeType)
	matches := []string{}
	for _, term := range terms {
		normalizedTerm := normalizeMatchText(term)
		if normalizedTerm == "" {
			continue
		}
		for _, value := range values {
			normalizedValue := normalizeMatchText(value)
			if normalizedValue == "" {
				continue
			}
			if strings.Contains(normalizedValue, normalizedTerm) || strings.Contains(normalizedQuery, normalizedValue) {
				matches = append(matches, term)
				break
			}
		}
	}
	return normalizeStrings(matches)
}

func normalizeMatchText(value string) string {
	return strings.ToLower(strings.TrimSpace(value))
}

func stringAttr(attrs map[string]any, key string) string {
	value, ok := attrs[key]
	if !ok {
		return ""
	}
	text, ok := value.(string)
	if !ok {
		return ""
	}
	return strings.TrimSpace(text)
}

func stringListAttr(attrs map[string]any, key string) []string {
	value, ok := attrs[key]
	if !ok {
		return []string{}
	}
	switch typed := value.(type) {
	case []any:
		out := []string{}
		for _, item := range typed {
			if text, ok := item.(string); ok {
				out = append(out, text)
			}
		}
		return normalizeStrings(out)
	case []string:
		return normalizeStrings(typed)
	case string:
		return normalizeStrings([]string{typed})
	default:
		return []string{}
	}
}

func intentScore(intent string, row store.ConceptCandidateRow, attrs map[string]any) int {
	haystack := strings.ToLower(strings.Join(append(append(deriveAliases(row, attrs), row.Paths...), row.ObservationSummaries...), " "))
	score := 0
	switch strings.ToLower(strings.TrimSpace(intent)) {
	case "implement":
		for _, marker := range []string{"src/", "test", "spec", "verification", "component", "module"} {
			if strings.Contains(haystack, marker) {
				score += 2
			}
		}
	case "debug":
		for _, marker := range []string{"symptom", "log", "render", "latency", "slow", "lag", "profile", "repro"} {
			if strings.Contains(haystack, marker) {
				score += 2
			}
		}
	case "plan":
		for _, marker := range []string{"capability", "workflow", "spec", "plan", "architecture"} {
			if strings.Contains(haystack, marker) {
				score += 2
			}
		}
	}
	return score
}

func disambiguationHint(row store.ConceptCandidateRow, matched []string) string {
	if len(matched) == 0 {
		return "Weak graph-backed candidate; select only if live evidence supports this route."
	}
	return "Matched graph-backed aliases or paths for " + row.Title + "."
}

func selectionGuidance(score int) string {
	if score <= 0 {
		return "weak_match"
	}
	if score < 10 {
		return "review_before_selecting"
	}
	return "strong_candidate"
}
```

- [ ] **Step 6: Update the query planning contract**

Replace the inline `QueryPlanningContract` map with:

```go
func queryPlanningContract() map[string]any {
	return map[string]any{
		"accepted_fields": []string{
			"raw_query",
			"expanded_queries",
			"paths",
			"path_hints",
			"selected_concepts",
			"rejected_concepts",
			"concept_decisions",
			"lexicon_generation_id",
			"selection_reason",
			"reason",
		},
		"path_hint_alias": "paths",
		"reason_alias":    "selection_reason",
		"candidate_id_format": "concept:<active_generation_id>:<node_id>",
	}
}
```

- [ ] **Step 7: Verify lexicon behavior**

Run:

```powershell
cd tools/project-cognition
gofmt -w internal/query/lexicon.go internal/query/query.go internal/query/query_test.go
go test ./internal/query -run "TestLexiconReturnsGraphCandidatesWithoutInventedTermConcepts|TestLexiconReportsUnmappedIntentWhenNoGraphCandidateMatches|TestLexiconBlocksSplitBrainBaseline" -count=1
```

Expected: pass.

- [ ] **Step 8: Commit**

```powershell
git add tools/project-cognition/internal/query/lexicon.go tools/project-cognition/internal/query/query_test.go
git commit -m "feat: rank graph-backed project cognition lexicon candidates"
```

---

### Task 4: Resolve Selected Concepts In Query

**Files:**
- Modify: `tools/project-cognition/internal/query/query.go`
- Modify: `tools/project-cognition/internal/query/query_test.go`

- [ ] **Step 1: Add failing query resolution tests**

Append these tests to `tools/project-cognition/internal/query/query_test.go`:

```go
func TestRunResolvesSelectedConceptsToNodesAndReads(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-ui",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-gui",
			SourceKind:  "source",
			SourcePath:  "src/gui/window.tsx",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-gui",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-gui",
			Type:        "capability",
			Title:       "GUI Shell",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-gui"},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-gui",
			Path:       "src/gui/window.tsx",
			NodeID:     "N-gui",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-gui",
		}},
	})

	payload, err := Run(paths, QueryInput{
		Intent: "debug",
		Query:  "GUI feels laggy",
		Plan: Plan{
			RawQuery:            "GUI feels laggy",
			LexiconGenerationID: "GEN-ui",
			SelectedConcepts:    []string{"concept:GEN-ui:N-gui"},
			ConceptDecisions: []ConceptDecision{{
				ConceptID:       "concept:GEN-ui:N-gui",
				Decision:        "selected",
				SelectionReason: "GUI owns the laggy surface.",
				Confidence:      "high",
			}},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Readiness != rt.ReadyReadiness {
		t.Fatalf("Readiness = %q, want query_ready", payload.Readiness)
	}
	if len(payload.AffectedNodes) == 0 {
		t.Fatalf("AffectedNodes = %#v, want selected concept node", payload.AffectedNodes)
	}
	if !hasString(payload.MinimalLiveReads, "src/gui/window.tsx") {
		t.Fatalf("MinimalLiveReads = %#v, want src/gui/window.tsx", payload.MinimalLiveReads)
	}
	if len(payload.QueryPlan.ConceptDecisions) != 1 {
		t.Fatalf("QueryPlan.ConceptDecisions = %#v", payload.QueryPlan.ConceptDecisions)
	}
}

func TestRunReportsLexiconGenerationMismatch(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-current",
		Kind:         "full",
		SourceCommit: "abc123",
		Evidence: []store.EvidenceImport{{
			ID:          "E-gui",
			SourceKind:  "source",
			SourcePath:  "src/gui/window.tsx",
			CommitSHA:   "abc123",
			Extractor:   "test",
			ContentHash: "hash-gui",
		}},
		Nodes: []store.NodeImport{{
			ID:          "N-gui",
			Type:        "capability",
			Title:       "GUI Shell",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-gui"},
		}},
		PathIndex: []store.PathIndexImport{{
			ID:         "P-gui",
			Path:       "src/gui/window.tsx",
			NodeID:     "N-gui",
			Relation:   "owns",
			Confidence: "verified",
			EvidenceID: "E-gui",
		}},
	})

	payload, err := Run(paths, QueryInput{
		Intent: "debug",
		Query:  "GUI feels laggy",
		Plan: Plan{
			LexiconGenerationID: "GEN-old",
			SelectedConcepts:    []string{"concept:GEN-old:N-gui"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Readiness != "ambiguous" {
		t.Fatalf("Readiness = %q, want ambiguous", payload.Readiness)
	}
	if payload.RecommendedNextAction != "rerun_project_cognition_lexicon" {
		t.Fatalf("RecommendedNextAction = %q", payload.RecommendedNextAction)
	}
	if !hasString(payload.MissingCoverage, "lexicon_generation_mismatch") {
		t.Fatalf("MissingCoverage = %#v, want lexicon_generation_mismatch", payload.MissingCoverage)
	}
}

func TestRunReportsUnknownSelectedConcept(t *testing.T) {
	paths := queryTestPaths(t)
	seedReadyGraph(t, paths, store.ImportInput{
		GenerationID: "GEN-ui",
		Kind:         "full",
		SourceCommit: "abc123",
	})

	payload, err := Run(paths, QueryInput{
		Intent: "implement",
		Query:  "GUI feels laggy",
		Plan: Plan{
			LexiconGenerationID: "GEN-ui",
			SelectedConcepts:    []string{"concept:GEN-ui:N-missing"},
		},
	})
	if err != nil {
		t.Fatal(err)
	}
	if payload.Readiness != "review" {
		t.Fatalf("Readiness = %q, want review", payload.Readiness)
	}
	if !hasString(payload.MissingCoverage, "unknown_selected_concept:concept:GEN-ui:N-missing") {
		t.Fatalf("MissingCoverage = %#v", payload.MissingCoverage)
	}
}
```

- [ ] **Step 2: Run the failing query resolution tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/query -run "TestRunResolvesSelectedConceptsToNodesAndReads|TestRunReportsLexiconGenerationMismatch|TestRunReportsUnknownSelectedConcept" -count=1
```

Expected: fail because `Run` only reads `plan.Paths`.

- [ ] **Step 3: Add concept ID parsing**

In `tools/project-cognition/internal/query/query.go`, add:

```go
type conceptRef struct {
	GenerationID string
	NodeID       string
}

func parseConceptID(value string) (conceptRef, bool) {
	parts := strings.Split(strings.TrimSpace(value), ":")
	if len(parts) < 3 || parts[0] != "concept" {
		return conceptRef{}, false
	}
	if parts[1] == "" || parts[2] == "" {
		return conceptRef{}, false
	}
	return conceptRef{GenerationID: parts[1], NodeID: parts[2]}, true
}

func selectedNodeIDs(selectedConcepts []string, activeGenerationID string) ([]string, []string) {
	nodeIDs := []string{}
	missing := []string{}
	for _, conceptID := range selectedConcepts {
		ref, ok := parseConceptID(conceptID)
		if !ok {
			nodeIDs = append(nodeIDs, conceptID)
			continue
		}
		if ref.GenerationID != activeGenerationID {
			missing = append(missing, "selected_concept_generation_mismatch:"+conceptID)
			continue
		}
		nodeIDs = append(nodeIDs, ref.NodeID)
	}
	return normalizeStrings(nodeIDs), missing
}
```

- [ ] **Step 4: Update `Run` to resolve concepts before path-only fallback**

In `Run`, after opening the store, get `activeGenerationID` from the store when present. Then:

```go
activeGenerationID := status.ActiveGenerationID
if st != nil {
	activeGenerationID, err = st.ActiveGenerationID(context.Background())
	if err != nil {
		return QueryPayload{}, err
	}
}
if plan.LexiconGenerationID != "" && activeGenerationID != "" && plan.LexiconGenerationID != activeGenerationID {
	return generationMismatchPayload(status, input, plan, activeGenerationID), nil
}
```

Replace the current `NodesForPaths`-only block with:

```go
nodes := []map[string]any{}
missingCoverage := []string{}
if st != nil {
	selectedIDs, selectedIDGaps := selectedNodeIDs(plan.SelectedConcepts, activeGenerationID)
	missingCoverage = append(missingCoverage, selectedIDGaps...)
	if len(selectedIDs) > 0 {
		nodes, err = st.NodesForIDs(context.Background(), selectedIDs)
		if err != nil {
			return QueryPayload{}, err
		}
		if len(nodes) == 0 {
			for _, conceptID := range plan.SelectedConcepts {
				missingCoverage = append(missingCoverage, "unknown_selected_concept:"+conceptID)
			}
		}
	}
	if len(nodes) == 0 {
		nodes, err = st.NodesForPaths(context.Background(), plan.Paths)
		if err != nil {
			return QueryPayload{}, err
		}
	}
}
nodePaths := pathsFromNodes(nodes)
if len(plan.Paths) == 0 && len(nodePaths) > 0 {
	plan.Paths = nodePaths
}
reads := normalizeStrings(append(append([]string{}, plan.Paths...), nodePaths...))
if len(reads) == 0 {
	reads = []string{".specify/project-cognition/status.json", ".specify/project-cognition/project-cognition.db"}
}
readiness := status.Readiness
recommendedNextAction := status.RecommendedNextAction
if hasUnknownSelectedConcept(missingCoverage) && readiness == rt.ReadyReadiness {
	readiness = "review"
	recommendedNextAction = "use_minimal_live_reads_and_review_missing_coverage"
}
```

Add these helpers:

```go
func pathsFromNodes(nodes []map[string]any) []string {
	paths := []string{}
	for _, node := range nodes {
		if value, ok := node["path"].(string); ok {
			paths = append(paths, value)
		}
	}
	return normalizePaths(paths)
}

func hasUnknownSelectedConcept(values []string) bool {
	for _, value := range values {
		if strings.HasPrefix(value, "unknown_selected_concept:") {
			return true
		}
	}
	return false
}
```

Set `MissingCoverage: missingCoverage`, `Readiness: readiness`, and `RecommendedNextAction: recommendedNextAction` in the returned `QueryPayload`.

- [ ] **Step 5: Add generation mismatch payload**

Add this helper in `tools/project-cognition/internal/query/query.go`:

```go
func generationMismatchPayload(status rt.Status, input QueryInput, plan Plan, activeGenerationID string) QueryPayload {
	missingCoverage := []string{"lexicon_generation_mismatch"}
	routePack := map[string]any{
		"items":              []map[string]any{},
		"routes":             []string{},
		"minimal_live_reads": []string{".specify/project-cognition/status.json", ".specify/project-cognition/project-cognition.db"},
		"why_these_reads":    "The query plan was created for a different project cognition graph generation.",
	}
	return QueryPayload{
		BaselineHealth: map[string]any{
			"freshness": status.Freshness,
			"readiness": status.Readiness,
			"dirty":     status.Dirty,
			"active_generation_id": activeGenerationID,
		},
		QueryCoverage: map[string]any{
			"paths": plan.Paths,
			"nodes": 0,
			"lexicon_generation_id": plan.LexiconGenerationID,
			"active_generation_id": activeGenerationID,
		},
		WorkflowRequirement:   "rerun_project_cognition_lexicon_before_query",
		PathAdoption:          map[string]any{"paths": []string{}},
		Readiness:             "ambiguous",
		RecommendedNextAction: "rerun_project_cognition_lexicon",
		Intent:                input.Intent,
		Query:                 input.Query,
		QueryPlan:             plan,
		SelectedConcepts:      plan.SelectedConcepts,
		RejectedConcepts:      plan.RejectedConcepts,
		SelectionReason:       plan.SelectionReason,
		CapabilityCandidates:  []map[string]any{},
		SymptomCandidates:     []map[string]any{},
		AffectedNodes:         []map[string]any{},
		MinimalLiveReads:      []string{".specify/project-cognition/status.json", ".specify/project-cognition/project-cognition.db"},
		MissingCoverage:       missingCoverage,
		RoutePack:             routePack,
		Subgraph: map[string]any{
			"nodes":     []map[string]any{},
			"edges":     []map[string]any{},
			"claims":    []map[string]any{},
			"conflicts": []map[string]any{},
		},
	}
}
```

- [ ] **Step 6: Verify query concept resolution**

Run:

```powershell
cd tools/project-cognition
gofmt -w internal/query/query.go internal/query/query_test.go
go test ./internal/query -run "TestRunResolvesSelectedConceptsToNodesAndReads|TestRunReportsLexiconGenerationMismatch|TestRunReportsUnknownSelectedConcept|TestRunMissingBaselineReturnsNeedsRebuildWithoutCreatingDatabase" -count=1
```

Expected: pass.

- [ ] **Step 7: Commit**

```powershell
git add tools/project-cognition/internal/query/query.go tools/project-cognition/internal/query/query_test.go
git commit -m "feat: resolve selected project cognition concepts"
```

---

### Task 5: Add CLI JSON Contract Smoke Tests

**Files:**
- Modify: `tools/project-cognition/internal/cli/cli_test.go`

- [ ] **Step 1: Add failing CLI tests for lexicon and query JSON fields**

Append these tests to `tools/project-cognition/internal/cli/cli_test.go`:

```go
func TestLexiconCommandEmitsGraphBackedContractFields(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var buildStdout, buildStderr bytes.Buffer
	if code := Run([]string{"build-from-scan", "--format", "json"}, &buildStdout, &buildStderr, "test"); code != 0 {
		t.Fatalf("build code = %d stderr=%s stdout=%s", code, buildStderr.String(), buildStdout.String())
	}
	var publishStdout, publishStderr bytes.Buffer
	if code := Run([]string{"publish-runtime-metadata", "--format", "json"}, &publishStdout, &publishStderr, "test"); code != 0 {
		t.Fatalf("publish code = %d stderr=%s stdout=%s", code, publishStderr.String(), publishStdout.String())
	}

	var stdout, stderr bytes.Buffer
	code := Run([]string{"lexicon", "--intent", "implement", "--query", "App GUI", "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["active_generation_id"] == "" {
		t.Fatalf("payload = %#v, want active_generation_id", payload)
	}
	if payload["candidate_universe_version"].(float64) != 1 {
		t.Fatalf("candidate_universe_version = %#v", payload["candidate_universe_version"])
	}
	if _, ok := payload["candidate_universe"].(map[string]any); !ok {
		t.Fatalf("payload = %#v, want candidate_universe", payload)
	}
	contract := payload["query_planning_contract"].(map[string]any)
	if !jsonStringSliceContains(contract["accepted_fields"], "concept_decisions") {
		t.Fatalf("accepted_fields = %#v, want concept_decisions", contract["accepted_fields"])
	}
}

func TestQueryCommandAcceptsConceptDecisionPlan(t *testing.T) {
	root := writeMinimalCLIScanPackage(t)
	old, _ := os.Getwd()
	if err := os.Chdir(root); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = os.Chdir(old) })

	var buildStdout, buildStderr bytes.Buffer
	if code := Run([]string{"build-from-scan", "--format", "json"}, &buildStdout, &buildStderr, "test"); code != 0 {
		t.Fatalf("build code = %d stderr=%s stdout=%s", code, buildStderr.String(), buildStdout.String())
	}
	var publishStdout, publishStderr bytes.Buffer
	if code := Run([]string{"publish-runtime-metadata", "--format", "json"}, &publishStdout, &publishStderr, "test"); code != 0 {
		t.Fatalf("publish code = %d stderr=%s stdout=%s", code, publishStderr.String(), publishStdout.String())
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	status, err := rt.ReadStatus(paths)
	if err != nil {
		t.Fatal(err)
	}
	queryPlan := `{"lexicon_generation_id":"` + status.ActiveGenerationID + `","selected_concepts":["concept:` + status.ActiveGenerationID + `:N-app"],"concept_decisions":[{"concept_id":"concept:` + status.ActiveGenerationID + `:N-app","decision":"selected","selection_reason":"App owns the requested surface.","confidence":"high"}]}`

	var stdout, stderr bytes.Buffer
	code := Run([]string{"query", "--intent", "implement", "--query-plan", queryPlan, "--format", "json"}, &stdout, &stderr, "test")
	if code != 0 {
		t.Fatalf("code = %d stderr=%s stdout=%s", code, stderr.String(), stdout.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["readiness"] != "query_ready" {
		t.Fatalf("payload = %#v", payload)
	}
	if !jsonStringSliceContains(payload["minimal_live_reads"], "src/app.go") {
		t.Fatalf("minimal_live_reads = %#v, want src/app.go", payload["minimal_live_reads"])
	}
}
```

- [ ] **Step 2: Run CLI smoke tests**

Run:

```powershell
cd tools/project-cognition
go test ./internal/cli -run "TestLexiconCommandEmitsGraphBackedContractFields|TestQueryCommandAcceptsConceptDecisionPlan" -count=1
```

Expected: pass after Tasks 1-4 are complete.

- [ ] **Step 3: Run Go runtime package tests**

Run:

```powershell
cd tools/project-cognition
gofmt -w internal/cli/cli_test.go internal/query internal/store
go test ./internal/query ./internal/store ./internal/cli -count=1
```

Expected: pass.

- [ ] **Step 4: Commit**

```powershell
git add tools/project-cognition/internal/cli/cli_test.go
git commit -m "test: cover graph-backed project cognition query contract"
```

---

### Task 6: Update Shared Project Cognition Workflow Templates

**Files:**
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/command-partials/common/planning-context-loading-gradient.md`
- Modify: `templates/command-partials/common/navigation-check.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/clarify.md`
- Modify: `templates/commands/deep-research.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/analyze.md`
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/discussion.md`
- Modify: `templates/commands/checklist.md`
- Modify: `templates/commands/prd-scan.md`
- Modify: `templates/commands/map-build.md`
- Modify: `tests/test_map_runtime_template_guidance.py`
- Modify: `tests/test_runtime_handbook_contract.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_passive_skill_guidance.py`
- Modify: `tests/test_quick_template_guidance.py`
- Modify: `tests/test_fast_template_guidance.py`

- [ ] **Step 1: Add failing template assertions for the new mental model**

Update `tests/test_map_runtime_template_guidance.py` in `test_workflows_use_project_cognition_query_instead_of_raw_graph_reads`:

```python
        assert "returned graph-backed project concept candidates" in content
        assert "concept_decisions" in content
        assert "lexicon_generation_id" in content
        assert "returned map terms" not in content
        assert "raw user intent plus returned map terms" not in content
```

Update `tests/test_runtime_handbook_contract.py` in `test_context_loading_gradient_uses_cognition_runtime_gate`:

```python
    assert "graph-backed project concept candidates" in lowered
    assert "concept_decisions" in content
    assert "lexicon_generation_id" in content
    assert "returned map terms" not in lowered
```

Update `tests/test_passive_skill_guidance.py` in the project cognition gate test:

```python
    assert "graph-backed project concept candidates" in content
    assert "concept_decisions" in content
    assert "lexicon_generation_id" in content
    assert "returned map terms" not in content
```

- [ ] **Step 2: Run the failing template tests**

Run:

```powershell
pytest tests/test_map_runtime_template_guidance.py tests/test_runtime_handbook_contract.py tests/test_passive_skill_guidance.py tests/test_quick_template_guidance.py tests/test_fast_template_guidance.py -q
```

Expected: fail on old wording such as `returned map terms`.

- [ ] **Step 3: Update shared partial wording**

In `templates/command-partials/common/context-loading-gradient.md` and `templates/command-partials/common/planning-context-loading-gradient.md`, replace the current lexicon paragraph with this contract:

```markdown
When project cognition is available, run `project-cognition lexicon` to retrieve
graph-backed project concept candidates. Inspect `concept_candidates`, select
task-relevant existing project concepts in `selected_concepts`, record
non-selected or unsafe candidates in `rejected_concepts`, and write
per-concept rationale in `concept_decisions`. Carry `lexicon_generation_id`
into the `query_plan` so `project-cognition query` can detect generation
drift. The `query_plan` should include `selected_concepts`,
`rejected_concepts`, `concept_decisions`, `expanded_queries`, and justified
`paths`, then be sent to `project-cognition query --query-plan`.
```

Keep the existing readiness guidance, `minimal_live_reads` guidance, advisory navigation wording, and live-evidence proof wording.

- [ ] **Step 4: Update workflow-local command snippets**

For each of these files:

```text
templates/commands/specify.md
templates/commands/clarify.md
templates/commands/deep-research.md
templates/commands/plan.md
templates/commands/tasks.md
templates/commands/fast.md
templates/commands/quick.md
templates/commands/implement.md
templates/commands/debug.md
templates/commands/prd-scan.md
templates/commands/map-build.md
```

Replace command comments of this form:

```markdown
# Agent: generate <query_plan_json> from raw user intent plus returned map terms.
```

with:

```markdown
# Agent: select from returned graph-backed project concept candidates; include selected_concepts, rejected_concepts, concept_decisions, lexicon_generation_id, expanded_queries, and justified paths in <query_plan_json>.
```

For prose sentences that say `generate a query_plan from returned map terms`, replace with:

```markdown
select from returned graph-backed project concept candidates, write `concept_decisions`, carry `lexicon_generation_id`, then generate a `query_plan`
```

- [ ] **Step 5: Update discussion and analyze wording**

In `templates/commands/discussion.md`, replace:

```markdown
Translate the returned map terms into a bounded `query_plan` with `selected_concepts`, `rejected_concepts`, `expanded_queries`, `paths`, and `selection_reason`.
```

with:

```markdown
Select from the returned graph-backed project concept candidates and create a bounded `query_plan` with `selected_concepts`, `rejected_concepts`, `concept_decisions`, `lexicon_generation_id`, `expanded_queries`, justified `paths`, and `selection_reason`.
```

In `templates/commands/analyze.md`, make the project cognition line mention `concept_decisions` and `lexicon_generation_id` in the same way.

- [ ] **Step 6: Update passive skills**

In `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`, update the opening usage contract to say:

```markdown
Run `project-cognition lexicon` first to get graph-backed project concept
candidates from the active project cognition graph. The user request ranks
and filters existing project concepts; it does not create project concepts.
Choose task-relevant `selected_concepts`, record considered but unsafe or
irrelevant `rejected_concepts`, write per-concept `concept_decisions`, carry
`lexicon_generation_id`, and then run `project-cognition query --query-plan`.
```

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, replace `using returned map terms` with:

```markdown
using returned graph-backed project concept candidates, `concept_decisions`,
and `lexicon_generation_id`
```

- [ ] **Step 7: Verify no old wording remains in templates**

Run:

```powershell
rg -n "returned map terms|raw user intent plus returned map terms|translate the returned map terms|using returned map terms" templates
```

Expected: no matches.

- [ ] **Step 8: Verify template tests**

Run:

```powershell
pytest tests/test_map_runtime_template_guidance.py tests/test_runtime_handbook_contract.py tests/test_alignment_templates.py tests/test_passive_skill_guidance.py tests/test_quick_template_guidance.py tests/test_fast_template_guidance.py -q
```

Expected: pass.

- [ ] **Step 9: Commit**

```powershell
git add templates tests/test_map_runtime_template_guidance.py tests/test_runtime_handbook_contract.py tests/test_alignment_templates.py tests/test_passive_skill_guidance.py tests/test_quick_template_guidance.py tests/test_fast_template_guidance.py
git commit -m "docs: teach graph-backed project cognition query planning"
```

---

### Task 7: Update Integration Renderers And Generated Surface Tests

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `src/specify_cli/integrations/**`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/test_extension_skills.py`

- [ ] **Step 1: Add failing generated-output assertions**

In `tests/integrations/test_integration_base_markdown.py`, add these checks inside `test_generated_commands_do_not_include_obsolete_cognition_addenda` after `assert "project-cognition query" in generated`:

```python
        assert "graph-backed project concept candidates" in generated
        assert "concept_decisions" in generated
        assert "lexicon_generation_id" in generated
        assert "returned map terms" not in generated
        assert "using returned map terms" not in generated
```

In `tests/integrations/test_integration_base_toml.py`, `tests/integrations/test_integration_base_skills.py`, and `tests/integrations/test_integration_codex.py`, add equivalent generated content assertions to the existing project cognition guidance tests:

```python
    assert "graph-backed project concept candidates" in content
    assert "concept_decisions" in content
    assert "lexicon_generation_id" in content
    assert "returned map terms" not in content
```

- [ ] **Step 2: Run the failing integration tests**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/test_extension_skills.py -q
```

Expected: fail because `src/specify_cli/integrations/base.py` still injects old wording.

- [ ] **Step 3: Update generated planning addenda**

In `src/specify_cli/integrations/base.py`, update `_append_specify_pre_analysis_protocol` from:

```python
"- Run project cognition planning navigation with `project-cognition lexicon --intent plan`, then generate a `query_plan`, then run `project-cognition query --intent plan --query-plan`; carry returned `minimal_live_reads` into the coverage-model check.\n"
```

to:

```python
"- Run project cognition planning navigation with `project-cognition lexicon --intent plan`, select from graph-backed project concept candidates, carry `lexicon_generation_id`, write `concept_decisions`, then run `project-cognition query --intent plan --query-plan`; carry returned `minimal_live_reads` into the coverage-model check.\n"
```

Update `_append_checklist_project_cognition_guidance` from:

```python
"- Run `project-cognition lexicon --intent plan`, generate a `query_plan`, then run `project-cognition query --intent plan --query-plan` before shaping the checklist.\n"
```

to:

```python
"- Run `project-cognition lexicon --intent plan`, select from graph-backed project concept candidates, include `concept_decisions` and `lexicon_generation_id` in the `query_plan`, then run `project-cognition query --intent plan --query-plan` before shaping the checklist.\n"
```

- [ ] **Step 4: Update `_project_cognition_query_gate_line`**

In `src/specify_cli/integrations/base.py`, replace the current returned-map-terms sentence with:

```python
return (
    "Before broad source inspection, "
    f"retrieve graph-backed project concept candidates with `{{{{specify-subcmd:project-cognition lexicon --intent {intent} --query=\"$ARGUMENTS\" --format json}}}}`, "
    "select relevant existing concepts, record rejected concepts, write `concept_decisions`, carry `lexicon_generation_id`, then run "
    f"`{{{{specify-subcmd:project-cognition query --intent {intent} --query-plan \"<query_plan_json>\" --format json}}}}` "
    "and follow `minimal_live_reads` plus readiness guidance."
)
```

- [ ] **Step 5: Audit agent-specific integration templates**

Run:

```powershell
rg -n "returned map terms|using returned map terms|raw user intent into a query_plan|generate a query_plan from returned" src/specify_cli/integrations
```

For every match, replace the old phrase with:

```text
select from returned graph-backed project concept candidates, write `concept_decisions`, carry `lexicon_generation_id`, then generate a `query_plan`
```

Keep literal command names and intent values unchanged.

- [ ] **Step 6: Verify generated surfaces**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/test_extension_skills.py -q
```

Expected: pass.

- [ ] **Step 7: Commit**

```powershell
git add src/specify_cli/integrations tests/integrations tests/test_extension_skills.py
git commit -m "docs: align generated cognition guidance with graph concepts"
```

---

### Task 8: Update Handbook And Operator Documentation

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `tests/test_runtime_handbook_contract.py`
- Modify: `tests/test_specify_guidance_docs.py`

- [ ] **Step 1: Add doc assertions for provenance fields**

In `tests/test_runtime_handbook_contract.py`, extend `test_runtime_handbook_docs_are_query_backed`:

```python
    assert "graph-backed project concept candidates" in lowered
    assert "concept_decisions" in content
    assert "lexicon_generation_id" in content
    assert "candidate_universe_version" in content
    assert "returned map terms" not in lowered
```

In `tests/test_specify_guidance_docs.py`, add equivalent assertions in the tests that read `README.md`, `PROJECT-HANDBOOK.md`, and `templates/project-handbook-template.md`.

- [ ] **Step 2: Run failing doc tests**

Run:

```powershell
pytest tests/test_runtime_handbook_contract.py tests/test_specify_guidance_docs.py -q
```

Expected: fail until docs mention graph-backed candidates and provenance fields.

- [ ] **Step 3: Update docs**

In `README.md`, `PROJECT-HANDBOOK.md`, and `templates/project-handbook-template.md`, update the project cognition query explanation to include this wording:

```markdown
`project-cognition lexicon` returns graph-backed project concept candidates
from the active project cognition graph. The agent selects existing concepts,
records rejected concepts, writes `concept_decisions`, carries
`lexicon_generation_id`, and then runs `project-cognition query --query-plan`.
The lexicon payload includes `candidate_universe_version` and
`active_generation_id` so query planning stays tied to the graph generation
that produced the candidates.
```

Keep existing guidance that project cognition is advisory navigation and live repository evidence proves technical claims.

- [ ] **Step 4: Verify docs**

Run:

```powershell
pytest tests/test_runtime_handbook_contract.py tests/test_specify_guidance_docs.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```powershell
git add README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md tests/test_runtime_handbook_contract.py tests/test_specify_guidance_docs.py
git commit -m "docs: document graph-backed project cognition lexicon"
```

---

### Task 9: Full Verification And Contract Sweep

**Files:**
- No planned new ownership. Only adjust files already named above when a verification command identifies a missed contract.

- [ ] **Step 1: Run Go verification**

Run:

```powershell
cd tools/project-cognition
gofmt -w internal/query internal/store internal/cli
go test ./...
go vet ./...
go build -o bin/project-cognition.exe .
cd ..\..
```

Expected: all commands pass.

- [ ] **Step 2: Run focused Python template and integration regressions**

Run:

```powershell
pytest tests/test_map_runtime_template_guidance.py tests/test_runtime_handbook_contract.py tests/test_alignment_templates.py tests/test_passive_skill_guidance.py tests/test_quick_template_guidance.py tests/test_fast_template_guidance.py tests/test_specify_guidance_docs.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/test_extension_skills.py -q
```

Expected: pass.

- [ ] **Step 3: Sweep for obsolete lexicon mental model**

Run:

```powershell
rg -n "returned map terms|raw user intent plus returned map terms|translate the returned map terms|using returned map terms|term:" templates src tools tests README.md PROJECT-HANDBOOK.md docs
```

Expected:

- no matches for old wording
- `term:` appears only in historical tests removed by this plan or in tests asserting it is absent

- [ ] **Step 4: Verify JSON contract field coverage**

Run:

```powershell
rg -n "candidate_universe_version|active_generation_id|lexicon_generation_id|concept_decisions|graph-backed project concept candidates" tools templates src tests README.md PROJECT-HANDBOOK.md
```

Expected: matches in runtime code, shared templates, integration renderers, docs, and tests.

- [ ] **Step 5: Run whitespace and status checks**

Run:

```powershell
git diff --check
git status --short
```

Expected: no whitespace errors. `git status --short` is clean if all task commits were made.

- [ ] **Step 6: Commit final regression adjustments if any were needed**

If Step 1 through Step 5 required fixes after the previous task commits:

```powershell
git add tools templates src tests README.md PROJECT-HANDBOOK.md docs
git commit -m "test: verify graph-backed project cognition lexicon rollout"
```

If no files changed during Task 9, skip this commit.

## Self-Review

- Spec coverage: Tasks 1-5 implement runtime fields, graph-backed lexicon ranking, query-time alias derivation, per-concept decisions, generation provenance, selected concept resolution, unmapped intent, missing coverage, and generation mismatch behavior.
- Shared workflow coverage: Tasks 6-8 update shared partials, passive skills, direct workflow templates, generated integration appenders, agent-specific templates, README, handbook, and generated project handbook template.
- Alias source coverage: Task 2 and Task 3 use query-time material from imported nodes, attrs, paths, evidence, and observations; no task relies on populated `alias_index`.
- Compatibility coverage: `selected_concepts`, `rejected_concepts`, `selection_reason`, `reason`, `paths`, and `path_hints` keep their existing input shapes while `concept_decisions` and `lexicon_generation_id` add traceability.
- Placeholder scan: This plan contains concrete files, commands, field names, and code snippets for each implementation step.
- Type consistency: Runtime snippets consistently use `CandidateUniverseVersion`, `ConceptDecision`, `LexiconGenerationID`, `concept:<generation>:<node>`, `ActiveConceptCandidateRows`, and `NodesForIDs`.
