var learningFacetKeys = []string{"components", "operation_owners", "consumer_owners", "outcomes", "states", "entrypoints", "validation_surfaces"}
var mapWorkflowCommands = []string{"sp-map-scan", "sp-map-build", "sp-map-update", "sp-map-rebuild"}
var knownLearningCommands = []string{
	"sp-accept", "sp-analyze", "sp-ask", "sp-auto", "sp-checklist", "sp-constitution",
	"sp-debug", "sp-deep-research", "sp-design", "sp-discussion", "sp-explain", "sp-fast", "sp-implement",
	"sp-implement-teams", "sp-map-scan", "sp-map-build", "sp-map-update", "sp-map-rebuild",
	"sp-plan", "sp-prd-build", "sp-prd-scan", "sp-quick", "sp-specify", "sp-tasks", "sp-taskstoissues", "sp-team", "sp-test-design",
}

var workflowStateAutoCaptureCommands = map[string]bool{
	"sp-constitution": true, "sp-specify": true, "sp-deep-research": true,
	"sp-plan": true, "sp-checklist": true, "sp-tasks": true, "sp-analyze": true, "sp-accept": true,
	"sp-prd-scan": true, "sp-prd-build": true, "sp-map-scan": true, "sp-map-build": true,
	"sp-map-update": true, "sp-map-rebuild": true,
}
