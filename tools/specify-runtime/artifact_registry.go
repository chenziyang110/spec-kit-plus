package main

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

type ArtifactTypeMetadata struct {
	TypeID         string   `json:"type_id"`
	Owner          string   `json:"owner"`
	Role           string   `json:"role"`
	Schema         string   `json:"schema"`
	Operations     []string `json:"operations"`
	SummaryAdapter string   `json:"summary_adapter"`
}

type ArtifactListRequest struct {
	PathPrefix string
	TypeID     string
	Owner      string
	Limit      int
}

type artifactTypePattern struct {
	metadata ArtifactTypeMetadata
	match    func(string) bool
}

var artifactTypePatterns = []artifactTypePattern{
	{
		metadata: ArtifactTypeMetadata{TypeID: "project-design-contract", Owner: "specify-runtime design", Role: "canonical", Schema: "markdown/design-contract", Operations: []string{"show", "list"}, SummaryAdapter: "markdown-headings"},
		match:    func(path string) bool { return path == "DESIGN.md" },
	},
	newFeatureWorkspacePattern("task-index.json", ArtifactTypeMetadata{TypeID: "feature-task-index", Owner: "specify-runtime tasks", Role: "canonical", Schema: "json/task-index", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern("tasks.md", ArtifactTypeMetadata{TypeID: "feature-tasks", Owner: "specify-runtime tasks", Role: "derived", Schema: "markdown/tasks", Operations: []string{"show", "list"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspacePattern("implementation-handoff.json", ArtifactTypeMetadata{TypeID: "feature-implementation-handoff", Owner: "specify-runtime implement closeout", Role: "derived", Schema: "json/implementation-handoff", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern("implementation-summary.md", ArtifactTypeMetadata{TypeID: "feature-implementation-summary", Owner: "specify-runtime implement closeout", Role: "derived", Schema: "markdown/implementation-summary", Operations: []string{"show", "list"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspacePattern("implement-tracker.md", ArtifactTypeMetadata{TypeID: "feature-implement-tracker", Owner: "specify-runtime implement", Role: "derived", Schema: "markdown/implement-tracker", Operations: []string{"show", "list"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspacePattern("review-state.json", ArtifactTypeMetadata{TypeID: "feature-review-state", Owner: "specify-runtime review via artifact patch", Role: "canonical", Schema: "json/review-state", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern("human-acceptance.json", ArtifactTypeMetadata{TypeID: "feature-human-acceptance", Owner: "specify-runtime accept via artifact patch", Role: "canonical", Schema: "json/human-acceptance", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern(acceptanceRepairJournalFilename, ArtifactTypeMetadata{TypeID: "acceptance-repair-journal", Owner: "specify-runtime accept route-repair", Role: "runtime-internal", Schema: "json/acceptance-repair-journal", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern(acceptanceRepairBackupFilename, ArtifactTypeMetadata{TypeID: "acceptance-repair-backup", Owner: "specify-runtime accept route-repair", Role: "runtime-recovery", Schema: "json/human-acceptance", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern("plan-contract.json", ArtifactTypeMetadata{TypeID: "feature-plan-contract", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "json/plan-contract", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern("specify-draft.md", ArtifactTypeMetadata{TypeID: "feature-specify-draft", Owner: "feature bootstrap / specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "markdown/specify-draft", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspacePattern("ui-brief.md", ArtifactTypeMetadata{TypeID: "feature-ui-brief", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "markdown/ui-brief", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspacePattern("ui-reference-notes.md", ArtifactTypeMetadata{TypeID: "feature-ui-reference-notes", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "markdown/ui-reference-notes", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspacePattern("deep-research.md", ArtifactTypeMetadata{TypeID: "feature-deep-research", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "markdown/deep-research", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspacePattern("research.md", ArtifactTypeMetadata{TypeID: "feature-research", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "markdown/research", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspacePattern("quickstart.md", ArtifactTypeMetadata{TypeID: "feature-quickstart", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "markdown/quickstart", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspacePattern("data-model.md", ArtifactTypeMetadata{TypeID: "feature-data-model", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "markdown/data-model", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspacePattern("alignment.md", ArtifactTypeMetadata{TypeID: "feature-alignment", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "markdown/alignment", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspacePattern("context.md", ArtifactTypeMetadata{TypeID: "feature-context", Owner: "feature bootstrap / specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "markdown/context", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspacePattern("references.md", ArtifactTypeMetadata{TypeID: "feature-references", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "markdown/references", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspacePattern("ui-target.html", ArtifactTypeMetadata{TypeID: "feature-ui-target", Owner: "specify-runtime design ui-target", Role: "derived", Schema: "html/ui-target", Operations: []string{"show", "list"}, SummaryAdapter: "text-lines"}),
	newFeatureWorkspacePattern("workflow-state.md", ArtifactTypeMetadata{TypeID: "feature-workflow-state", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "markdown/workflow-state", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspacePattern("handoff-to-tasks.json", ArtifactTypeMetadata{TypeID: "feature-tasks-handoff", Owner: "specify-runtime tasks", Role: "derived", Schema: "json/tasks-handoff", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern("handoff-to-implement.json", ArtifactTypeMetadata{TypeID: "feature-implement-handoff", Owner: "specify-runtime tasks handoff", Role: "derived", Schema: "json/tasks-handoff", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern("brainstorming/handoff-to-specify.json", ArtifactTypeMetadata{TypeID: "brainstorming-compatibility-handoff", Owner: "specify-runtime discussion bind-consumer", Role: "derived", Schema: "json/discussion-handoff-pointer", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern("brainstorming/journal.ndjson", ArtifactTypeMetadata{TypeID: "brainstorming-compatibility-journal", Owner: "feature bootstrap / specify-runtime hook", Role: "derived", Schema: "ndjson/brainstorming-journal", Operations: []string{"show", "list"}, SummaryAdapter: "text-lines"}),
	newFeatureWorkspaceNestedPattern("brainstorming/", ".json", ArtifactTypeMetadata{TypeID: "brainstorming-compatibility-json", Owner: "feature bootstrap / specify-runtime hook", Role: "derived", Schema: "json/brainstorming-compatibility", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern("clarification/evidence-index.json", ArtifactTypeMetadata{TypeID: "clarification-evidence-index", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "json/evidence-index", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern("clarification/checkpoints.ndjson", ArtifactTypeMetadata{TypeID: "clarification-checkpoints", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "ndjson/clarification-events", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "text-lines"}),
	newFeatureWorkspaceNestedPattern("clarification/handoffs/", ".json", ArtifactTypeMetadata{TypeID: "clarification-handoff", Owner: "specify-runtime result submit", Role: "canonical", Schema: "json/worker-result", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspaceNestedPattern("clarification/", ".json", ArtifactTypeMetadata{TypeID: "clarification-json", Owner: "specify-runtime artifact", Role: "canonical", Schema: "json/clarification", Operations: []string{"prepare", "submit", "patch", "show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspaceNestedPattern("clarification/", ".ndjson", ArtifactTypeMetadata{TypeID: "clarification-events", Owner: "specify-runtime artifact", Role: "canonical", Schema: "ndjson/clarification-events", Operations: []string{"prepare", "submit", "patch", "show", "list"}, SummaryAdapter: "text-lines"}),
	newFeatureWorkspaceNestedPattern("implementation-review/tasks/", ".json", ArtifactTypeMetadata{TypeID: "task-lifecycle", Owner: "specify-runtime implement", Role: "canonical", Schema: "json/task-lifecycle", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspaceNestedPattern("implementation-review/task-reopen-history/", ".json", ArtifactTypeMetadata{TypeID: "task-reopen-history", Owner: "specify-runtime implement task-reopen", Role: "canonical", Schema: "json/task-reopen-history", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspaceNestedPattern("worker-results/", ".json", ArtifactTypeMetadata{TypeID: "worker-result", Owner: "specify-runtime result / specify-runtime implement result-merge", Role: "canonical", Schema: "json/worker-result", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspaceNestedPattern("review-evidence/", ".json", ArtifactTypeMetadata{TypeID: "review-evidence-json", Owner: "specify-runtime artifact", Role: "canonical", Schema: "json/review-evidence", Operations: []string{"prepare", "submit", "patch", "show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspaceNestedPattern("research-evidence/", ".json", ArtifactTypeMetadata{TypeID: "research-evidence-json", Owner: "specify-runtime artifact", Role: "canonical", Schema: "json/research-evidence", Operations: []string{"prepare", "submit", "patch", "show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspaceNestedPattern("checklists/", ".md", ArtifactTypeMetadata{TypeID: "feature-checklist", Owner: "specify-runtime artifact checklist / artifact patch", Role: "canonical", Schema: "markdown/checklist", Operations: []string{"checklist", "prepare", "patch", "show", "list", "delete"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspaceNestedPattern("implementation-review/packets/", ".json", ArtifactTypeMetadata{TypeID: "worker-packet", Owner: "specify-runtime implement packet-compile", Role: "derived", Schema: "json/worker-packet", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspaceNestedPattern("implementation-review/deferrals/", ".json", ArtifactTypeMetadata{TypeID: "implementation-deferral", Owner: "specify-runtime implement deferral-propose / deferral-confirm", Role: "canonical", Schema: "json/implementation-deferral", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern("implementation-review/validation-runs.json", ArtifactTypeMetadata{TypeID: "implementation-validation-ledger", Owner: "specify-runtime implement validation-start / validation-finish", Role: "canonical", Schema: "json/validation-ledger", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern("implementation-review/execution-state.json", ArtifactTypeMetadata{TypeID: "implementation-execution-state", Owner: "specify-runtime implement", Role: "canonical", Schema: "json/implementation-execution-state", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern("implementation-review/ledger.json", ArtifactTypeMetadata{TypeID: "implementation-review-ledger", Owner: "specify-runtime implement resume-audit", Role: "canonical", Schema: "json/implementation-review-ledger", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern("implementation-review/branch-review.md", ArtifactTypeMetadata{TypeID: "implementation-branch-review", Owner: "specify-runtime implement resume-audit", Role: "derived", Schema: "markdown/implementation-branch-review", Operations: []string{"show", "list"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspacePattern("implementation-review/reviews.ndjson", ArtifactTypeMetadata{TypeID: "implementation-review-events", Owner: "specify-runtime implement resume-audit", Role: "canonical", Schema: "ndjson/implementation-review", Operations: []string{"show", "list"}, SummaryAdapter: "text-lines"}),
	newFeatureWorkspacePattern("implementation-review/repairs.ndjson", ArtifactTypeMetadata{TypeID: "implementation-repair-events", Owner: "specify-runtime implement resume-audit", Role: "canonical", Schema: "ndjson/implementation-repair", Operations: []string{"show", "list"}, SummaryAdapter: "text-lines"}),
	newFeatureWorkspaceNestedPattern("implementation-review/task-briefs/", ".md", ArtifactTypeMetadata{TypeID: "implementation-task-brief", Owner: "specify-runtime implement resume-audit", Role: "derived", Schema: "markdown/implementation-task-brief", Operations: []string{"show", "list"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspaceNestedPattern("implementation-review/review-packages/", ".md", ArtifactTypeMetadata{TypeID: "implementation-review-package", Owner: "specify-runtime implement resume-audit", Role: "derived", Schema: "markdown/implementation-review-package", Operations: []string{"show", "list"}, SummaryAdapter: "markdown-headings"}),
	newFeatureWorkspaceNestedPattern("implementation-review/task-reviews/", ".json", ArtifactTypeMetadata{TypeID: "implementation-task-review", Owner: "specify-runtime implement resume-audit", Role: "canonical", Schema: "json/implementation-task-review", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspaceTreePattern("implementation-review/snapshots/", ArtifactTypeMetadata{TypeID: "implementation-review-snapshot", Owner: "specify-runtime implement resume-audit", Role: "derived", Schema: "text/implementation-review-snapshot", Operations: []string{"show", "list"}, SummaryAdapter: "text-lines"}),
	newFeatureWorkspaceTreePattern("implementation-review/validation-evidence/", ArtifactTypeMetadata{TypeID: "implementation-validation-evidence", Owner: "specify-runtime evidence / specify-runtime implement validation-finish", Role: "canonical", Schema: "text/implementation-validation-evidence", Operations: []string{"show", "list"}, SummaryAdapter: "text-lines"}),
	newFeatureWorkspaceNestedPattern("planning/handoffs/", ".json", ArtifactTypeMetadata{TypeID: "planning-lane-result", Owner: "specify-runtime result submit", Role: "canonical", Schema: "json/worker-result", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspaceNestedPattern("task-generation/handoffs/", ".json", ArtifactTypeMetadata{TypeID: "task-generation-lane-result", Owner: "specify-runtime result submit", Role: "canonical", Schema: "json/worker-result", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspaceNestedPattern("research/handoffs/", ".json", ArtifactTypeMetadata{TypeID: "research-lane-result", Owner: "specify-runtime result submit", Role: "canonical", Schema: "json/worker-result", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspaceNestedPattern("review-results/", ".json", ArtifactTypeMetadata{TypeID: "review-lane-result", Owner: "specify-runtime result submit", Role: "canonical", Schema: "json/worker-result", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern("planning/lane-manifest.json", ArtifactTypeMetadata{TypeID: "planning-lane-manifest", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "json/lane-manifest", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspacePattern("task-generation/lane-manifest.json", ArtifactTypeMetadata{TypeID: "task-generation-lane-manifest", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "json/lane-manifest", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspaceNestedPattern("contracts/", ".json", ArtifactTypeMetadata{TypeID: "feature-contract-json", Owner: "specify-runtime artifact", Role: "canonical", Schema: "json/feature-contract", Operations: []string{"prepare", "submit", "patch", "show", "list"}, SummaryAdapter: "json-top-level-keys"}),
	newFeatureWorkspaceTreePattern("contracts/", ArtifactTypeMetadata{TypeID: "feature-contract", Owner: "specify-runtime artifact", Role: "canonical", Schema: "text/feature-contract", Operations: []string{"prepare", "submit", "patch", "show", "list"}, SummaryAdapter: "text-lines"}),
	newFeatureWorkspaceTreePattern("research-spikes/", ArtifactTypeMetadata{TypeID: "feature-research-spike", Owner: "specify-runtime artifact", Role: "canonical", Schema: "text/research-spike", Operations: []string{"prepare", "submit", "patch", "show", "list"}, SummaryAdapter: "text-lines"}),
	{
		metadata: ArtifactTypeMetadata{TypeID: "feature-visual-comparison", Owner: "specify-runtime evidence visual-compare", Role: "canonical", Schema: "json/visual-comparison", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"},
		match: func(path string) bool {
			relative := featureWorkspaceRelative(path)
			name := filepath.Base(relative)
			return relative == name && strings.HasPrefix(name, "visual-comparison") && strings.HasSuffix(name, ".json")
		},
	},
	newFeatureArtifactPattern("spec.md", ArtifactTypeMetadata{
		TypeID:         "feature-spec",
		Owner:          "specify-runtime artifact",
		Role:           "canonical",
		Schema:         "markdown/spec",
		Operations:     []string{"prepare", "submit", "patch", "show", "list"},
		SummaryAdapter: "markdown-headings",
	}),
	newFeatureArtifactPattern("spec-contract.json", ArtifactTypeMetadata{
		TypeID:         "feature-spec-contract",
		Owner:          "specify-runtime artifact scaffold / artifact patch",
		Role:           "canonical",
		Schema:         "json/spec-contract",
		Operations:     []string{"prepare", "patch", "show", "list"},
		SummaryAdapter: "json-top-level-keys",
	}),
	newFeatureArtifactPattern("workflow-state.md", ArtifactTypeMetadata{
		TypeID:         "feature-workflow-state",
		Owner:          "specify-runtime artifact scaffold / artifact patch",
		Role:           "canonical",
		Schema:         "markdown/workflow-state",
		Operations:     []string{"prepare", "patch", "show", "list"},
		SummaryAdapter: "markdown-headings",
	}),
	{
		metadata: ArtifactTypeMetadata{TypeID: "semantic-audit-input", Owner: "specify-runtime cognition semantic-audit", Role: "canonical", Schema: "json/semantic-audit-input", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"},
		match: func(path string) bool {
			return isWorkflowLocalNamedArtifact(path, "semantic-audit-input.json")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "semantic-audit-output", Owner: "specify-runtime cognition semantic-audit", Role: "canonical", Schema: "json/semantic-audit-output", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"},
		match: func(path string) bool {
			return isWorkflowLocalNamedArtifact(path, "semantic-audit-output.json")
		},
	},
	newFeatureArtifactPattern("plan.md", ArtifactTypeMetadata{
		TypeID:         "feature-plan",
		Owner:          "specify-runtime artifact",
		Role:           "canonical",
		Schema:         "markdown/plan",
		Operations:     []string{"prepare", "submit", "patch", "show", "list"},
		SummaryAdapter: "markdown-headings",
	}),
	newFeatureArtifactPattern("tasks.md", ArtifactTypeMetadata{
		TypeID:         "feature-tasks",
		Owner:          "specify-runtime tasks",
		Role:           "derived",
		Schema:         "markdown/tasks",
		Operations:     []string{"show", "list"},
		SummaryAdapter: "markdown-headings",
	}),
	newFeatureArtifactPattern("task-index.json", ArtifactTypeMetadata{
		TypeID:         "feature-task-index",
		Owner:          "specify-runtime tasks",
		Role:           "canonical",
		Schema:         "json/task-index",
		Operations:     []string{"show", "list"},
		SummaryAdapter: "json-top-level-keys",
	}),
	newFeatureArtifactPattern("implementation-handoff.json", ArtifactTypeMetadata{
		TypeID:         "feature-implementation-handoff",
		Owner:          "specify-runtime implement closeout",
		Role:           "derived",
		Schema:         "json/implementation-handoff",
		Operations:     []string{"show", "list"},
		SummaryAdapter: "json-top-level-keys",
	}),
	newFeatureArtifactPattern("review-state.json", ArtifactTypeMetadata{
		TypeID:         "feature-review-state",
		Owner:          "specify-runtime review",
		Role:           "canonical",
		Schema:         "json/review-state",
		Operations:     []string{"prepare", "patch", "show", "list"},
		SummaryAdapter: "json-top-level-keys",
	}),
	newFeatureArtifactPattern("human-acceptance.json", ArtifactTypeMetadata{
		TypeID:         "feature-human-acceptance",
		Owner:          "specify-runtime accept",
		Role:           "canonical",
		Schema:         "json/human-acceptance",
		Operations:     []string{"prepare", "patch", "show", "list"},
		SummaryAdapter: "json-top-level-keys",
	}),
	{
		metadata: ArtifactTypeMetadata{
			TypeID:         "quick-status",
			Owner:          "specify-runtime artifact scaffold / artifact patch",
			Role:           "canonical",
			Schema:         "markdown/quick-status",
			Operations:     []string{"prepare", "patch", "show", "list"},
			SummaryAdapter: "markdown-headings",
		},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".planning/quick/") && strings.HasSuffix(path, "/STATUS.md")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "quick-summary", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "markdown/quick-summary", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".planning/quick/") && strings.HasSuffix(path, "/SUMMARY.md")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "quick-plan", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "markdown/quick-plan", Operations: []string{"prepare", "patch", "show", "list", "delete"}, SummaryAdapter: "markdown-headings"},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".planning/quick/") && strings.HasSuffix(path, "/PLAN.md")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "quick-support", Owner: "specify-runtime artifact", Role: "canonical", Schema: "markdown/quick-support", Operations: []string{"prepare", "submit", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"},
		match: func(path string) bool {
			if !strings.HasPrefix(path, ".planning/quick/") {
				return false
			}
			return strings.HasSuffix(path, "/RESEARCH.md") || strings.HasSuffix(path, "/DISCUSSION.md")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "quick-worker-result", Owner: "specify-runtime result submit", Role: "canonical", Schema: "json/worker-result", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".planning/quick/") && strings.Contains(path, "/worker-results/") && strings.HasSuffix(path, ".json")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "quick-index", Owner: "specify-runtime quick", Role: "derived", Schema: "json/quick-index", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"},
		match: func(path string) bool {
			return path == ".planning/quick/index.json"
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "debug-research", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "markdown/research", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".planning/debug/") && strings.HasSuffix(path, ".research.md") && !strings.Contains(strings.TrimPrefix(path, ".planning/debug/"), "/")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "debug-session", Owner: "specify-runtime artifact scaffold / artifact patch / artifact delete", Role: "canonical", Schema: "markdown/debug-session", Operations: []string{"prepare", "patch", "show", "list", "delete"}, SummaryAdapter: "markdown-headings"},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".planning/debug/") && strings.HasSuffix(path, ".md") && !strings.Contains(strings.TrimPrefix(path, ".planning/debug/"), "/")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "debug-worker-result", Owner: "specify-runtime result submit", Role: "canonical", Schema: "json/worker-result", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".planning/debug/results/") && strings.HasSuffix(path, ".json")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "shared-worker-result", Owner: "specify-runtime result submit", Role: "canonical", Schema: "json/worker-result", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".specify/worker-results/") && strings.HasSuffix(path, ".json")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "project-constitution", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "markdown/constitution", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"},
		match: func(path string) bool {
			return path == ".specify/memory/constitution.md"
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "design-review", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "markdown/design-review", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"},
		match: func(path string) bool {
			return path == ".specify/design/review.md"
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "design-brief", Owner: "specify-runtime artifact scaffold / artifact patch", Role: "canonical", Schema: "markdown/design-brief", Operations: []string{"prepare", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"},
		match: func(path string) bool {
			return path == ".specify/design/design-brief.md"
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "design-working-document", Owner: "specify-runtime artifact", Role: "canonical", Schema: "markdown/design-working-document", Operations: []string{"prepare", "submit", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"},
		match: func(path string) bool {
			switch path {
			case ".specify/design/options.md", ".specify/design/references.md":
				return true
			default:
				return false
			}
		},
	},
	{
		metadata: ArtifactTypeMetadata{
			TypeID:         "design-state",
			Owner:          "specify-runtime design",
			Role:           "derived",
			Schema:         "markdown/design-state",
			Operations:     []string{"show", "list"},
			SummaryAdapter: "markdown-headings",
		},
		match: func(path string) bool {
			return path == ".specify/design/design-state.md"
		},
	},
	{
		metadata: ArtifactTypeMetadata{
			TypeID:         "design-preview-manifest",
			Owner:          "specify-runtime design preview-manifest / specify-runtime artifact patch",
			Role:           "canonical",
			Schema:         "json/design-preview-manifest",
			Operations:     []string{"prepare", "patch", "show", "list"},
			SummaryAdapter: "json-top-level-keys",
		},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".specify/design/previews/") && strings.HasSuffix(path, ".manifest.json")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "prd-worker-result", Owner: "specify-runtime result submit", Role: "canonical", Schema: "json/worker-result", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".specify/prd-runs/") && strings.Contains(path, "/worker-results/") && strings.HasSuffix(path, ".json")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "prd-scan-records", Owner: "specify-runtime prd-scan record-upsert|record-remove|record-show|record-list", Role: "canonical", Schema: "json/prd-scan-records", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"},
		match: func(path string) bool {
			if !strings.HasPrefix(path, ".specify/prd-runs/") {
				return false
			}
			base := filepath.Base(path)
			for _, surface := range prdRecordSurfaceCatalog {
				if base == surface.Path {
					return true
				}
			}
			return false
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "prd-run-json", Owner: "specify-runtime artifact", Role: "canonical", Schema: "json/prd-run", Operations: []string{"prepare", "submit", "patch", "show", "list"}, SummaryAdapter: "json-top-level-keys"},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".specify/prd-runs/") && strings.HasSuffix(path, ".json")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "prd-build-document", Owner: "specify-runtime prd-build scaffold + specify-runtime artifact patch", Role: "canonical", Schema: "markdown/prd-build-document", Operations: []string{"patch", "show", "list"}, SummaryAdapter: "markdown-headings"},
		match: func(path string) bool {
			return isPRDBuildDocumentPath(path)
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "prd-run-markdown", Owner: "specify-runtime artifact", Role: "canonical", Schema: "markdown/prd-run", Operations: []string{"prepare", "submit", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".specify/prd-runs/") && strings.HasSuffix(path, ".md") && !strings.HasSuffix(path, "/workflow-state.md")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "discussion-log", Owner: "specify-runtime discussion checkpoint", Role: "canonical", Schema: "jsonl/discussion-log", Operations: []string{"show", "list"}, SummaryAdapter: "text-lines"},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".specify/discussions/") && strings.HasSuffix(path, "/discussion-log.jsonl")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "discussion-handoff", Owner: "specify-runtime discussion write-handoff", Role: "canonical", Schema: "json/discussion-handoff", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".specify/discussions/") && strings.HasSuffix(path, "/handoff-to-specify.json")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "discussion-view", Owner: "specify-runtime artifact", Role: "canonical", Schema: "markdown/discussion-view", Operations: []string{"prepare", "submit", "patch", "show", "list"}, SummaryAdapter: "markdown-headings"},
		match: func(path string) bool {
			if !strings.HasPrefix(path, ".specify/discussions/") {
				return false
			}
			for _, suffix := range []string{"/requirements.md", "/technical-options.md", "/project-context.md", "/open-questions.md"} {
				if strings.HasSuffix(path, suffix) {
					return true
				}
			}
			return false
		},
	},
	{
		metadata: ArtifactTypeMetadata{
			TypeID:         "discussion-state-json",
			Owner:          "specify-runtime discussion",
			Role:           "canonical",
			Schema:         "json/discussion-state",
			Operations:     []string{"show", "list"},
			SummaryAdapter: "json-top-level-keys",
		},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".specify/discussions/") && strings.HasSuffix(path, "/discussion-state.json")
		},
	},
	{
		metadata: ArtifactTypeMetadata{
			TypeID:         "discussion-state-markdown",
			Owner:          "specify-runtime discussion",
			Role:           "derived",
			Schema:         "markdown/discussion-state",
			Operations:     []string{"show", "list"},
			SummaryAdapter: "markdown-headings",
		},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".specify/discussions/") && strings.HasSuffix(path, "/discussion-state.md")
		},
	},
	{
		metadata: ArtifactTypeMetadata{
			TypeID:         "design-markdown",
			Owner:          "specify-runtime design",
			Role:           "derived",
			Schema:         "markdown/design-preview",
			Operations:     []string{"show", "list"},
			SummaryAdapter: "markdown-headings",
		},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".specify/design/") && strings.HasSuffix(path, ".md")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "design-json", Owner: "specify-runtime design", Role: "derived", Schema: "json/design-artifact", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".specify/design/") && strings.HasSuffix(path, ".json")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "design-html", Owner: "specify-runtime design", Role: "derived", Schema: "html/design-preview", Operations: []string{"show", "list"}, SummaryAdapter: "text-lines"},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".specify/design/") && strings.HasSuffix(path, ".html")
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "discussion-index", Owner: "specify-runtime discussion list", Role: "derived", Schema: "json/discussion-index", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"},
		match: func(path string) bool {
			return path == ".specify/discussions/index.json"
		},
	},
	{
		metadata: ArtifactTypeMetadata{TypeID: "teams-runtime-state", Owner: "specify-runtime sp-teams", Role: "derived", Schema: "json/teams-state", Operations: []string{"show", "list"}, SummaryAdapter: "json-top-level-keys"},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".specify/teams/") && strings.HasSuffix(path, ".json")
		},
	},
	{
		metadata: ArtifactTypeMetadata{
			TypeID:         "prd-status",
			Owner:          "specify-runtime",
			Role:           "derived",
			Schema:         "json/prd-status",
			Operations:     []string{"show", "list"},
			SummaryAdapter: "json-top-level-keys",
		},
		match: func(path string) bool {
			return path == ".specify/prd/status.json"
		},
	},
	{
		metadata: ArtifactTypeMetadata{
			TypeID:         "prd-run-workflow-state",
			Owner:          "specify-runtime artifact (initialized by specify-runtime prd-scan)",
			Role:           "canonical",
			Schema:         "markdown/prd-run-workflow-state",
			Operations:     []string{"prepare", "patch", "show", "list"},
			SummaryAdapter: "markdown-headings",
		},
		match: func(path string) bool {
			return strings.HasPrefix(path, ".specify/prd-runs/") && strings.HasSuffix(path, "/workflow-state.md")
		},
	},
	{
		metadata: ArtifactTypeMetadata{
			TypeID:         "specs-markdown",
			Owner:          "specify-runtime artifact",
			Role:           "canonical",
			Schema:         "markdown/spec",
			Operations:     []string{"prepare", "submit", "patch", "show", "list"},
			SummaryAdapter: "markdown-headings",
		},
		match: func(path string) bool {
			return strings.HasPrefix(path, "specs/") && strings.HasSuffix(path, ".md")
		},
	},
	{
		metadata: ArtifactTypeMetadata{
			TypeID:         "specs-spec-contract",
			Owner:          "specify-runtime artifact scaffold / artifact patch",
			Role:           "canonical",
			Schema:         "json/spec-contract",
			Operations:     []string{"prepare", "patch", "show", "list"},
			SummaryAdapter: "json-top-level-keys",
		},
		match: func(path string) bool {
			return strings.HasPrefix(path, "specs/") && strings.HasSuffix(path, "/spec-contract.json")
		},
	},
}

func newFeatureArtifactPattern(suffix string, metadata ArtifactTypeMetadata) artifactTypePattern {
	return artifactTypePattern{
		metadata: metadata,
		match: func(path string) bool {
			return strings.HasPrefix(path, ".specify/features/") && matchesFeatureArtifactSuffix(path, suffix)
		},
	}
}

func newFeatureWorkspacePattern(suffix string, metadata ArtifactTypeMetadata) artifactTypePattern {
	return artifactTypePattern{metadata: metadata, match: func(path string) bool {
		return featureWorkspaceRelative(path) == suffix
	}}
}

func newFeatureWorkspaceNestedPattern(prefix, suffix string, metadata ArtifactTypeMetadata) artifactTypePattern {
	return artifactTypePattern{metadata: metadata, match: func(path string) bool {
		relative := featureWorkspaceRelative(path)
		return strings.HasPrefix(relative, prefix) && len(relative) > len(prefix) && strings.HasSuffix(relative, suffix)
	}}
}

func newFeatureWorkspaceTreePattern(prefix string, metadata ArtifactTypeMetadata) artifactTypePattern {
	return artifactTypePattern{metadata: metadata, match: func(path string) bool {
		relative := featureWorkspaceRelative(path)
		return strings.HasPrefix(relative, prefix) && len(relative) > len(prefix)
	}}
}

func isWorkflowLocalNamedArtifact(path, basename string) bool {
	if filepath.Base(path) != basename {
		return false
	}
	for _, root := range []string{
		".planning/debug/",
		".planning/quick/",
		".specify/design/",
		".specify/discussions/",
		".specify/features/",
		".specify/prd-runs/",
		"specs/",
	} {
		if strings.HasPrefix(path, root) {
			return true
		}
	}
	return false
}

func featureWorkspaceRelative(path string) string {
	for _, root := range []string{".specify/features/", "specs/"} {
		if !strings.HasPrefix(path, root) {
			continue
		}
		rest := strings.TrimPrefix(path, root)
		parts := strings.SplitN(rest, "/", 2)
		if len(parts) == 2 && parts[0] != "" {
			return parts[1]
		}
	}
	return ""
}

func matchesFeatureArtifactSuffix(path, suffix string) bool {
	if !strings.HasSuffix(path, "/"+suffix) {
		return false
	}
	trimmed := strings.TrimPrefix(path, ".specify/features/")
	parts := strings.Split(trimmed, "/")
	return len(parts) == 2 && parts[0] != "" && parts[1] == suffix
}

func LookupArtifactType(canonicalPath string) (ArtifactTypeMetadata, bool) {
	normalized := filepath.ToSlash(filepath.Clean(filepath.FromSlash(strings.TrimSpace(canonicalPath))))
	for _, pattern := range artifactTypePatterns {
		if pattern.match(normalized) {
			return artifactMetadataWithGenericDelete(pattern.metadata), true
		}
	}
	return ArtifactTypeMetadata{}, false
}

func artifactMetadataWithGenericDelete(metadata ArtifactTypeMetadata) ArtifactTypeMetadata {
	if metadata.Owner != "specify-runtime artifact" || metadata.Role != "canonical" || artifactTypeAllows(metadata, "delete") {
		return metadata
	}
	operations := append([]string(nil), metadata.Operations...)
	operations = append(operations, "delete")
	metadata.Operations = operations
	return metadata
}

func artifactTypeAllows(metadata ArtifactTypeMetadata, operation string) bool {
	for _, allowed := range metadata.Operations {
		if allowed == operation {
			return true
		}
	}
	return false
}

func ArtifactTypeCatalog() Envelope {
	byID := map[string]ArtifactTypeMetadata{}
	for _, pattern := range artifactTypePatterns {
		byID[pattern.metadata.TypeID] = artifactMetadataWithGenericDelete(pattern.metadata)
	}
	ids := make([]string, 0, len(byID))
	for typeID := range byID {
		ids = append(ids, typeID)
	}
	sort.Strings(ids)
	env := NewEnvelope("ok", "artifact type registry")
	for _, typeID := range ids {
		env.Items = append(env.Items, byID[typeID])
	}
	env.Data["count"] = len(ids)
	return env
}

func (service *ArtifactService) ListArtifacts(request ArtifactListRequest) Envelope {
	limit := request.Limit
	if limit <= 0 {
		limit = 50
	}
	if limit > 200 {
		limit = 200
	}
	var roots []string
	prefix := strings.TrimSpace(request.PathPrefix)
	if prefix != "" {
		normalizedPrefix, err := normalizeArtifactPrefix(prefix)
		if err != nil {
			env := NewEnvelope("invalid", "artifact list request is invalid")
			env.Blockers = append(env.Blockers, err.Error())
			return env
		}
		roots = []string{normalizedPrefix}
	} else {
		roots = append([]string(nil), registeredArtifactRoots...)
		if registeredRootArtifacts["DESIGN.md"] {
			roots = append(roots, "DESIGN.md")
		}
	}

	items := []map[string]any{}
	seen := map[string]bool{}
	for _, root := range roots {
		if len(items) >= limit {
			break
		}
		discovered, err := service.discoverArtifactsUnder(root, request, limit-len(items), seen)
		if err != nil {
			env := NewEnvelope("blocked", "artifact instances cannot be listed")
			env.Blockers = append(env.Blockers, err.Error())
			return env
		}
		items = append(items, discovered...)
	}
	sort.Slice(items, func(i, j int) bool {
		return items[i]["canonical_path"].(string) < items[j]["canonical_path"].(string)
	})
	env := NewEnvelope("ok", "artifact instances listed")
	env.Data["items"] = items
	env.Data["count"] = len(items)
	env.Data["limit"] = limit
	return env
}

func normalizeArtifactPrefix(prefix string) (string, error) {
	trimmed := strings.TrimSpace(prefix)
	if trimmed == "" {
		return "", fmt.Errorf("artifact path prefix must not be empty")
	}
	normalized := filepath.ToSlash(filepath.Clean(filepath.FromSlash(trimmed)))
	if normalized == "." || normalized == ".." || strings.HasPrefix(normalized, "../") {
		return "", fmt.Errorf("artifact path prefix must stay inside the project")
	}
	if registeredRootArtifacts[normalized] {
		return normalized, nil
	}
	for _, root := range registeredArtifactRoots {
		if strings.HasPrefix(normalized, root) {
			if strings.HasSuffix(trimmed, "/") && !strings.HasSuffix(normalized, "/") {
				normalized += "/"
			}
			return normalized, nil
		}
	}
	return "", fmt.Errorf("artifact path prefix %q is outside registered workflow roots", prefix)
}

func (service *ArtifactService) discoverArtifactsUnder(root string, request ArtifactListRequest, limit int, seen map[string]bool) ([]map[string]any, error) {
	if limit <= 0 {
		return nil, nil
	}
	if registeredRootArtifacts[root] {
		target, err := secureProjectPath(service.projectRoot, root)
		if err != nil {
			return nil, err
		}
		item, ok, err := service.describeArtifactFile(root, target, request, seen)
		if err != nil || !ok {
			return nil, err
		}
		return []map[string]any{item}, nil
	}
	targetRoot := strings.TrimSuffix(root, "/")
	targetPath, err := secureProjectPath(service.projectRoot, targetRoot)
	if err != nil {
		return nil, err
	}
	info, err := os.Stat(targetPath)
	if os.IsNotExist(err) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	if !info.IsDir() {
		item, ok, err := service.describeArtifactFile(targetRoot, targetPath, request, seen)
		if err != nil || !ok {
			return nil, err
		}
		return []map[string]any{item}, nil
	}
	items := []map[string]any{}
	err = filepath.WalkDir(targetPath, func(path string, entry fs.DirEntry, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if len(items) >= limit {
			return fs.SkipAll
		}
		if entry.IsDir() {
			if strings.HasPrefix(entry.Name(), ".") && entry.Name() != ".specify" && entry.Name() != ".planning" {
				return fs.SkipDir
			}
			return nil
		}
		relative, err := filepath.Rel(service.projectRoot, path)
		if err != nil {
			return err
		}
		canonical := filepath.ToSlash(relative)
		item, ok, err := service.describeArtifactFile(canonical, path, request, seen)
		if err != nil {
			return err
		}
		if ok {
			items = append(items, item)
		}
		return nil
	})
	if err != nil && err != fs.SkipAll {
		return nil, err
	}
	return items, nil
}

func (service *ArtifactService) describeArtifactFile(canonicalPath, absolutePath string, request ArtifactListRequest, seen map[string]bool) (map[string]any, bool, error) {
	canonicalPath, err := registeredArtifactPath(canonicalPath)
	if err != nil {
		return nil, false, nil
	}
	if seen[canonicalPath] {
		return nil, false, nil
	}
	metadata, ok := LookupArtifactType(canonicalPath)
	if !ok {
		return nil, false, nil
	}
	if request.TypeID != "" && request.TypeID != metadata.TypeID {
		return nil, false, nil
	}
	if request.Owner != "" && request.Owner != metadata.Owner {
		return nil, false, nil
	}
	info, err := os.Stat(absolutePath)
	if os.IsNotExist(err) {
		return nil, false, nil
	}
	if err != nil {
		return nil, false, err
	}
	raw, err := os.ReadFile(absolutePath)
	if err != nil {
		return nil, false, err
	}
	digest := sha256.Sum256(raw)
	item := map[string]any{
		"canonical_path": canonicalPath,
		"type_id":        metadata.TypeID,
		"owner":          metadata.Owner,
		"role":           metadata.Role,
		"schema":         metadata.Schema,
		"bytes":          info.Size(),
		"sha256":         hex.EncodeToString(digest[:]),
	}
	seen[canonicalPath] = true
	addArtifactSummary(item, canonicalPath, raw)
	return item, true, nil
}
