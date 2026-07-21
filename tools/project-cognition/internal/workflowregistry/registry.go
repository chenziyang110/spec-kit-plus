package workflowregistry

import (
	"fmt"
	"strings"
)

const SchemaVersion = 1

type Mode string

const (
	ModeMutationCloseout    Mode = "mutation_closeout"
	ModeMapMaintenance      Mode = "map_maintenance"
	ModeBaselineMaintenance Mode = "baseline_maintenance"
	ModeNoCloseout          Mode = "no_closeout"
)

type Policy struct {
	Mode              Mode   `json:"mode"`
	CanonicalWorkflow string `json:"canonical_workflow"`
	Reason            string `json:"reason"`
}

var policies = map[string]Policy{
	"accept":          {Mode: ModeNoCloseout, Reason: "Human acceptance records product judgment but does not own repository mutation."},
	"analyze":         {Mode: ModeNoCloseout, Reason: "Analysis is read-only."},
	"ask":             {Mode: ModeNoCloseout, Reason: "Ask is read-only."},
	"auto":            {Mode: ModeNoCloseout, Reason: "The selected owning workflow performs any required closeout."},
	"checklist":       {Mode: ModeNoCloseout, Reason: "Checklist artifacts are planning-only."},
	"clarify":         {Mode: ModeNoCloseout, Reason: "Clarification changes specification artifacts only."},
	"constitution":    {Mode: ModeNoCloseout, Reason: "Constitution changes are governance artifacts and do not update the code map."},
	"debug":           {Mode: ModeMutationCloseout, CanonicalWorkflow: "sp-debug", Reason: "Debug may repair repository behavior."},
	"deep-research":   {Mode: ModeNoCloseout, Reason: "Research findings and isolated spikes are planning inputs."},
	"design":          {Mode: ModeNoCloseout, Reason: "Design writes design artifacts, not implementation."},
	"discussion":      {Mode: ModeNoCloseout, Reason: "Discussion writes planning state only."},
	"explain":         {Mode: ModeNoCloseout, Reason: "Explain is read-only."},
	"fast":            {Mode: ModeMutationCloseout, CanonicalWorkflow: "sp-fast", Reason: "Fast performs a bounded repository change."},
	"implement":       {Mode: ModeMutationCloseout, CanonicalWorkflow: "sp-implement", Reason: "Implement owns repository changes."},
	"implement-teams": {Mode: ModeMutationCloseout, CanonicalWorkflow: "sp-implement", Reason: "Implement Teams changes orchestration only; closeout remains owned by sp-implement."},
	"integrate":       {Mode: ModeMutationCloseout, CanonicalWorkflow: "sp-integrate", Reason: "Integrate owns verified integrated-tree changes and repairs."},
	"map-build":       {Mode: ModeBaselineMaintenance, Reason: "Map Build publishes a baseline through its dedicated validation contract."},
	"map-scan":        {Mode: ModeBaselineMaintenance, Reason: "Map Scan produces baseline evidence through its dedicated acceptance contract."},
	"map-update":      {Mode: ModeMapMaintenance, CanonicalWorkflow: "sp-map-update", Reason: "Map Update is the explicit incremental maintenance entrypoint."},
	"plan":            {Mode: ModeNoCloseout, Reason: "Plan artifacts are planning-only."},
	"prd":             {Mode: ModeNoCloseout, Reason: "PRD artifacts are planning-only."},
	"prd-build":       {Mode: ModeNoCloseout, Reason: "PRD reconstruction writes planning artifacts only."},
	"prd-scan":        {Mode: ModeNoCloseout, Reason: "PRD scanning records planning evidence only."},
	"quick":           {Mode: ModeMutationCloseout, CanonicalWorkflow: "sp-quick", Reason: "Quick performs a tracked repository change."},
	"research":        {Mode: ModeNoCloseout, Reason: "Research routes to planning research artifacts."},
	"review":          {Mode: ModeMutationCloseout, CanonicalWorkflow: "sp-review", Reason: "Review may repair integrated repository behavior."},
	"specify":         {Mode: ModeNoCloseout, Reason: "Specification artifacts are planning-only."},
	"tasks":           {Mode: ModeNoCloseout, Reason: "Task artifacts are planning-only."},
	"taskstoissues":   {Mode: ModeNoCloseout, Reason: "Issue export does not own repository source mutation."},
	"team":            {Mode: ModeNoCloseout, Reason: "Team runtime operations defer mutation closeout to the owning workflow."},
}

func Policies() map[string]Policy {
	out := make(map[string]Policy, len(policies))
	for name, policy := range policies {
		out[name] = policy
	}
	return out
}

func CanonicalCloseoutWorkflow(value string) (string, error) {
	name := strings.ToLower(strings.TrimSpace(value))
	name = strings.TrimPrefix(name, "/")
	name = strings.ReplaceAll(name, ".", "-")
	name = strings.ReplaceAll(name, "_", "-")
	name = strings.TrimPrefix(name, "sp-")
	policy, ok := policies[name]
	if !ok || (policy.Mode != ModeMutationCloseout && policy.Mode != ModeMapMaintenance) {
		return "", fmt.Errorf("workflow %q does not own project cognition closeout", value)
	}
	return policy.CanonicalWorkflow, nil
}
