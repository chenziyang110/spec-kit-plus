package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/url"
	"os"
	"path/filepath"
	"reflect"
	"regexp"
	"runtime"
	"sort"
	"strconv"
	"strings"
)

const (
	designPreviewSchema            = "spec-kit-design-preview-v1"
	designPreviewManifestSchema    = "spec-kit-design-preview-manifest-v1"
	designPreviewApprovalSchema    = "spec-kit-design-preview-approval-v1"
	designHandoffSchema            = "spec-kit-design-handoff-v1"
	designCapabilityProfilesSchema = "spec-kit-design-capability-profiles-v1"
	designCapabilityModelSchema    = "spec-kit-design-capability-model-v1"
	designPreviewManifestID        = "design-preview-manifest"
	uiTargetSchema                 = "spec-kit-ui-target-v1"
	uiTargetManifestSchema         = "spec-kit-ui-target-manifest-v1"
	uiTargetManifestID             = "ui-target-manifest"
)

var (
	frontMatterRE           = regexp.MustCompile(`(?s)\A---\s*\r?\n(.*?)\r?\n---\s*\r?\n?(.*)\z`)
	tokenNameRE             = regexp.MustCompile(`^[a-z][a-z0-9]*(?:\.[a-z0-9]+)*$`)
	tokenRefRE              = regexp.MustCompile(`^\{([a-z][a-z0-9]*)\.([a-z][a-z0-9]*(?:\.[a-z0-9]+)*)\}$`)
	headingRECache          = map[string]*regexp.Regexp{}
	previewDirectionIDRE    = regexp.MustCompile(`^direction-[a-z0-9][a-z0-9-]*$`)
	designSpecimenIDRE      = regexp.MustCompile(`^SP-[A-Z0-9]+(?:-[A-Z0-9]+)+$`)
	previewPlaceholderRE    = regexp.MustCompile(`__[A-Z0-9_]+__`)
	remoteReferenceRE       = regexp.MustCompile(`(?i)(?:https?:)?//|@import\b`)
	cssURLReferenceRE       = regexp.MustCompile(`(?is)url\s*\(\s*["']?([^"')\s]+)`)
	networkRuntimeRE        = regexp.MustCompile(`(?i)\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(`)
	uiPersistenceRuntimeRE  = regexp.MustCompile(`(?i)\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(|\b(?:localStorage|sessionStorage|indexedDB|document\.cookie)\b`)
	hexDigestRE             = regexp.MustCompile(`^[0-9a-f]{64}$`)
	canonicalDecisionIDRE   = regexp.MustCompile(`^DS-[A-Z0-9]+(?:-[A-Z0-9]+)+$`)
	uiCanonicalDecisionIDRE = regexp.MustCompile(`^DS-[A-Z]+-\d{3}$`)
	canonicalHandoffIDRE    = regexp.MustCompile(`^DH-[A-Z0-9]+(?:-[A-Z0-9]+)+$`)
)

type designDiagnostic struct {
	Code    string `json:"code"`
	Message string `json:"message"`
	Path    string `json:"path"`
	Level   string `json:"level"`
}

type designDocument struct {
	Source       string
	FrontMatter  map[string]any
	DesignSystem map[string]any
	Body         string
}

type htmlParseSummary struct {
	HTMLLang            string
	PreviewAttrs        map[string]string
	TargetAttrs         map[string]string
	DirectionIDs        []string
	DirectionAnchorIDs  []string
	Sections            map[string]bool
	ExternalDeps        []string
	InlineEventHandlers []string
	Widths              map[string]bool
	States              map[string]bool
	StyleText           string
	ScriptText          string
	PreviewManifestText string
	UITargetManifest    string
}

func runDesign(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeDesignError(stdout, "usage-error", "missing design subcommand")
	}
	switch args[0] {
	case "lint":
		return runDesignLint(args[1:], stdout)
	case "preview":
		return runDesignPreview(args[1:], stdout)
	case "preview-manifest":
		return runDesignPreviewManifest(args[1:], stdout)
	case "preview-lint":
		return runDesignPreviewLint(args[1:], stdout)
	case "profiles":
		return runDesignProfiles(stdout)
	case "ui-target":
		return runDesignUITarget(args[1:], stdout)
	case "ui-target-lint":
		return runDesignUITargetLint(args[1:], stdout)
	case "approve":
		return runDesignApprove(args[1:], stdout)
	case "export":
		return runDesignExport(args[1:], stdout)
	case "import":
		return runDesignImport(args[1:], stdout)
	default:
		return writeDesignError(stdout, "usage-error", fmt.Sprintf("unknown design subcommand %q", args[0]))
	}
}

func runDesignLint(args []string, stdout io.Writer) int {
	level := strings.ToLower(optionValue(args, "--level", "structural"))
	if !supportedDesignLintLevel(level) {
		return writeDesignError(stdout, "usage-error", "unsupported design lint level: "+level)
	}
	path := firstPositional(args, "DESIGN.md")
	target, env, ok := designContainedPath(path, false)
	if !ok {
		return writeEnvelope(stdout, env)
	}
	diagnostics := lintDesignFile(target, level)
	return writeDesignDiagnostics(stdout, diagnostics, fmt.Sprintf("%s is valid at %s level", filepath.ToSlash(path), level))
}

func runDesignPreview(args []string, stdout io.Writer) int {
	out := optionValue(args, "--out", ".specify/design/previews/round-01.html")
	target, env, ok := designContainedPath(out, true)
	if !ok {
		return writeEnvelope(stdout, env)
	}
	var written string
	var err error
	if manifestArg := strings.TrimSpace(optionValue(args, "--manifest", "")); manifestArg != "" {
		manifestPath, manifestEnv, manifestOK := designContainedPath(manifestArg, false)
		if !manifestOK {
			return writeEnvelope(stdout, manifestEnv)
		}
		written, err = renderDesignPreview(manifestPath, target, hasFlag(args, "--force"))
	} else {
		written, err = scaffoldDesignPreview(target, hasFlag(args, "--force"))
	}
	if err != nil {
		return writeDesignError(stdout, "blocked", err.Error())
	}
	env = NewEnvelope("ok", "design preview scaffold written")
	env.Data["path"] = written
	env.NextArgv = []string{"specify-runtime", "design", "preview-lint", written, "--level", "ready"}
	return writeEnvelope(stdout, env)
}

func runDesignPreviewManifest(args []string, stdout io.Writer) int {
	out := optionValue(args, "--out", ".specify/design/previews/round-01.manifest.json")
	target, env, ok := designContainedPath(out, true)
	if !ok {
		return writeEnvelope(stdout, env)
	}
	profileIDs, err := parseDesignCapabilityProfileIDs(optionValue(args, "--profiles", "web"))
	if err != nil {
		return writeDesignError(stdout, "usage-error", err.Error())
	}
	written, err := scaffoldDesignPreviewManifest(target, hasFlag(args, "--force"), profileIDs)
	if err != nil {
		return writeDesignError(stdout, "blocked", err.Error())
	}
	preview := strings.TrimSuffix(written, ".manifest.json") + ".html"
	env = NewEnvelope("ok", "design preview manifest scaffold written")
	env.Data["path"] = written
	env.NextArgv = []string{"specify-runtime", "design", "preview", "--manifest", written, "--out", preview}
	return writeEnvelope(stdout, env)
}

func runDesignProfiles(stdout io.Writer) int {
	registry, err := loadDesignCapabilityRegistry()
	if err != nil {
		return writeDesignError(stdout, "blocked", err.Error())
	}
	env := NewEnvelope("ok", "design capability profiles listed")
	env.Data["schema"] = designCapabilityProfilesSchema
	env.Data["profiles"] = registry["profiles"]
	return writeEnvelope(stdout, env)
}

func runDesignPreviewLint(args []string, stdout io.Writer) int {
	if len(args) == 0 || strings.HasPrefix(args[0], "-") {
		return writeDesignError(stdout, "usage-error", "design preview-lint requires a path")
	}
	level := strings.ToLower(optionValue(args, "--level", "structural"))
	if !supportedDesignLintLevel(level) {
		return writeDesignError(stdout, "usage-error", "unsupported design preview lint level: "+level)
	}
	target, env, ok := designContainedPath(args[0], false)
	if !ok {
		return writeEnvelope(stdout, env)
	}
	diagnostics := lintDesignPreviewFile(target, level)
	return writeDesignDiagnostics(stdout, diagnostics, fmt.Sprintf("%s is valid at %s level", filepath.ToSlash(args[0]), level))
}

func runDesignUITarget(args []string, stdout io.Writer) int {
	out := optionValue(args, "--out", "ui-target.html")
	target, env, ok := designContainedPath(out, true)
	if !ok {
		return writeEnvelope(stdout, env)
	}
	written, err := scaffoldUITarget(target, hasFlag(args, "--force"))
	if err != nil {
		return writeDesignError(stdout, "blocked", err.Error())
	}
	env = NewEnvelope("ok", "UI target scaffold written")
	env.Data["path"] = written
	env.NextArgv = []string{"specify-runtime", "design", "ui-target-lint", written, "--level", "ready"}
	return writeEnvelope(stdout, env)
}

func runDesignUITargetLint(args []string, stdout io.Writer) int {
	if len(args) == 0 || strings.HasPrefix(args[0], "-") {
		return writeDesignError(stdout, "usage-error", "design ui-target-lint requires a path")
	}
	level := strings.ToLower(optionValue(args, "--level", "structural"))
	if !supportedDesignLintLevel(level) {
		return writeDesignError(stdout, "usage-error", "unsupported UI target lint level: "+level)
	}
	target, env, ok := designContainedPath(args[0], false)
	if !ok {
		return writeEnvelope(stdout, env)
	}
	diagnostics := lintUITargetFile(target, level)
	return writeDesignDiagnostics(stdout, diagnostics, fmt.Sprintf("%s is valid at %s level", filepath.ToSlash(args[0]), level))
}

func runDesignApprove(args []string, stdout io.Writer) int {
	if len(args) == 0 || strings.HasPrefix(args[0], "-") {
		return writeDesignError(stdout, "usage-error", "design approve requires a preview path")
	}
	direction := strings.TrimSpace(optionValue(args, "--direction", ""))
	if direction == "" {
		return writeDesignError(stdout, "usage-error", "design approve requires --direction")
	}
	target, env, ok := designContainedPath(args[0], false)
	if !ok {
		return writeEnvelope(stdout, env)
	}
	payload, err := approveDesignPreview(target, direction)
	if err != nil {
		env := NewEnvelope("blocked", "design preview approval blocked")
		env.Blockers = append(env.Blockers, err.Error())
		env.Data["ok"] = false
		env.Data["error"] = err.Error()
		return writeEnvelope(stdout, env)
	}
	env = NewEnvelope("ok", "design preview approved")
	env.Data["ok"] = true
	env.Data["approval"] = payload
	env.Data["approval_path"] = strings.TrimSuffix(target, filepath.Ext(target)) + ".approval.json"
	env.Data["handoff_path"] = strings.TrimSuffix(target, filepath.Ext(target)) + ".handoff.json"
	return writeEnvelope(stdout, env)
}

func runDesignExport(args []string, stdout io.Writer) int {
	format := strings.ToLower(optionValue(args, "--format", "json"))
	if format != "json" && format != "tailwind" {
		return writeDesignError(stdout, "usage-error", "--format must be json or tailwind")
	}
	path := firstPositional(args, "DESIGN.md")
	target, env, ok := designContainedPath(path, false)
	if !ok {
		return writeEnvelope(stdout, env)
	}
	rendered, err := exportDesignSystem(target, format, !hasFlag(args, "--allow-unapproved"))
	if err != nil {
		return writeDesignError(stdout, "blocked", err.Error())
	}
	if out := strings.TrimSpace(optionValue(args, "--out", "")); out != "" {
		outPath, env, ok := designContainedPath(out, true)
		if !ok {
			return writeEnvelope(stdout, env)
		}
		if err := writeTextAtomic(outPath, rendered); err != nil {
			return writeDesignError(stdout, "error", "write design export: "+err.Error())
		}
		env = NewEnvelope("ok", "design export written")
		env.Data["path"] = outPath
		env.Data["format"] = format
		return writeEnvelope(stdout, env)
	}
	env = NewEnvelope("ok", "design export rendered")
	env.Data["format"] = format
	var payload any
	if err := json.Unmarshal([]byte(rendered), &payload); err != nil {
		env.Data["content"] = rendered
	} else {
		env.Data["content"] = payload
	}
	return writeEnvelope(stdout, env)
}

func runDesignImport(args []string, stdout io.Writer) int {
	if len(args) == 0 || strings.HasPrefix(args[0], "-") {
		return writeDesignError(stdout, "usage-error", "design import requires a source")
	}
	outDir := optionValue(args, "--out-dir", ".specify/design")
	root, err := os.Getwd()
	if err != nil {
		return writeDesignError(stdout, "error", "resolve project root: "+err.Error())
	}
	outPath, err := resolveProjectContainedPath(root, filepath.Join(outDir, "references.md"))
	if err != nil {
		return writeDesignError(stdout, "usage-error", "design import path is invalid: "+err.Error())
	}
	content := designReferenceContent(args[0], optionValue(args, "--notes", ""))
	if err := writeTextAtomic(outPath, content); err != nil {
		return writeDesignError(stdout, "error", "write design reference: "+err.Error())
	}
	env := NewEnvelope("ok", "design reference imported")
	env.Data["path"] = outPath
	return writeEnvelope(stdout, env)
}

func lintDesignFile(path, level string) []designDiagnostic {
	info, err := os.Stat(path)
	if err != nil {
		return []designDiagnostic{{Code: "missing-file", Message: fmt.Sprintf("%s does not exist", path), Path: path, Level: "error"}}
	}
	if !info.Mode().IsRegular() {
		return []designDiagnostic{{Code: "read-error", Message: fmt.Sprintf("%s is not a file", path), Path: path, Level: "error"}}
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return []designDiagnostic{{Code: "read-error", Message: fmt.Sprintf("cannot read %s: %v", path, err), Path: path, Level: "error"}}
	}
	doc, err := parseDesignMarkdown(string(raw), path)
	if err != nil {
		return []designDiagnostic{{Code: "parse-error", Message: err.Error(), Path: path, Level: "error"}}
	}
	var diagnostics []designDiagnostic
	validateDesignSystem(doc, &diagnostics)
	validateMarkdownSections(doc, &diagnostics)
	validateTokenReferences(doc, &diagnostics)
	if level == "ready" {
		validateDesignReadiness(doc, &diagnostics)
	}
	return diagnostics
}

func exportDesignSystem(path, format string, requireReady bool) (string, error) {
	level := "structural"
	if requireReady {
		level = "ready"
	}
	if diagnostics := lintDesignFile(path, level); len(diagnostics) > 0 {
		return "", errors.New(joinDiagnostics(diagnostics))
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return "", err
	}
	doc, err := parseDesignMarkdown(string(raw), path)
	if err != nil {
		return "", err
	}
	if format == "tailwind" {
		return marshalPretty(toTailwindTheme(doc.DesignSystem))
	}
	keys := []string{"schema", "name", "version", "status", "approval", "product_context", "direction_contract", "platforms", "capability_profiles", "specimens", "tokens", "color_modes", "components", "responsive", "content", "decisions", "verification", "accessibility"}
	payload := map[string]any{}
	for _, key := range keys {
		if value, ok := doc.DesignSystem[key]; ok {
			payload[key] = value
		} else if key == "platforms" || key == "decisions" {
			payload[key] = []any{}
		} else {
			payload[key] = map[string]any{}
		}
	}
	return marshalPretty(payload)
}

func approveDesignPreview(path, directionID string) (map[string]any, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("design preview does not exist: %s", path)
	}
	content := string(raw)
	parsed := parseHTMLSummary(content)
	status := strings.ToLower(strings.TrimSpace(parsed.PreviewAttrs["data-preview-status"]))
	if status == "approved" {
		return nil, fmt.Errorf("design preview is already approved and immutable: %s", path)
	}
	if status != "candidate" {
		return nil, fmt.Errorf("design preview must be a configured candidate before approval")
	}
	if !stringInSlice(directionID, parsed.DirectionIDs) {
		return nil, fmt.Errorf("unknown design direction %s; choose one of %s", directionID, strings.Join(parsed.DirectionIDs, ", "))
	}
	if diagnostics := lintDesignPreviewFile(path, "ready"); len(diagnostics) > 0 {
		return nil, fmt.Errorf("design preview is not ready for approval: %s", joinDiagnostics(diagnostics))
	}
	manifest, err := parseJSONObject(parsed.PreviewManifestText)
	if err != nil {
		return nil, err
	}
	review, _ := manifest["review"].(map[string]any)
	if review == nil {
		review = map[string]any{}
		manifest["review"] = review
	}
	review["status"] = "approved"
	review["approved_direction"] = directionID
	updated, err := replaceEmbeddedJSON(content, designPreviewManifestID, manifest)
	if err != nil {
		return nil, err
	}
	for _, pair := range [][2]string{{"data-preview-status", "approved"}, {"data-approved-direction", directionID}, {"data-active-direction", directionID}} {
		updated, err = replaceHTMLAttribute(updated, pair[0], pair[1])
		if err != nil {
			return nil, err
		}
	}
	decisionIDs := manifestDecisionIDs(manifest)
	if len(decisionIDs) == 0 {
		return nil, fmt.Errorf("design preview manifest must define stable decisions before approval")
	}
	handoffPayload, err := buildDesignHandoffPayload(path, updated, directionID, manifest)
	if err != nil {
		return nil, err
	}
	handoffText, err := marshalPretty(handoffPayload)
	if err != nil {
		return nil, fmt.Errorf("cannot render design handoff: %v", err)
	}
	handoffPath := strings.TrimSuffix(path, filepath.Ext(path)) + ".handoff.json"
	handoffIDs := manifestHandoffContractIDs(manifest)
	payload := map[string]any{
		"schema":                 designPreviewApprovalSchema,
		"preview_file":           filepath.Base(path),
		"direction_id":           directionID,
		"preview_ref":            filepath.Base(path) + "#" + directionID,
		"review_round":           strings.TrimSpace(fmt.Sprint(review["round"])),
		"html_sha256":            sha256String(updated),
		"manifest_sha256":        canonicalJSONSHA256(manifest),
		"decision_ids":           decisionIDs,
		"handoff_file":           filepath.Base(handoffPath),
		"handoff_ref":            filepath.Base(handoffPath),
		"handoff_sha256":         sha256String(handoffText),
		"handoff_contract_ids":   handoffIDs,
		"capability_profile_ids": manifestCapabilityProfileIDs(manifest),
		"specimen_ids":           manifestSpecimenIDs(manifest),
	}
	approvalText, err := marshalPretty(payload)
	if err != nil {
		return nil, fmt.Errorf("cannot render design approval: %v", err)
	}
	if err := validateDesignApprovalBundle(path, updated, handoffText, approvalText); err != nil {
		return nil, err
	}
	sidecar := strings.TrimSuffix(path, filepath.Ext(path)) + ".approval.json"
	projectRoot, err := os.Getwd()
	if err != nil {
		return nil, err
	}
	if _, err := applyFileTransaction(projectRoot, "design.approve", []fileTransactionUpdate{
		{Path: path, Content: []byte(updated), Perm: 0o644},
		{Path: handoffPath, Content: []byte(handoffText), Perm: 0o644},
		{Path: sidecar, Content: []byte(approvalText), Perm: 0o644},
	}); err != nil {
		return nil, fmt.Errorf("cannot commit design approval: %w", err)
	}
	return payload, nil
}

func validateDesignApprovalBundle(path, previewText, handoffText, approvalText string) error {
	validationRoot, err := os.MkdirTemp(filepath.Dir(path), ".design-approval-validation-*")
	if err != nil {
		return err
	}
	defer os.RemoveAll(validationRoot)

	previewPath := filepath.Join(validationRoot, filepath.Base(path))
	handoffPath := strings.TrimSuffix(previewPath, filepath.Ext(previewPath)) + ".handoff.json"
	approvalPath := strings.TrimSuffix(previewPath, filepath.Ext(previewPath)) + ".approval.json"
	for _, item := range []struct {
		path    string
		content string
	}{
		{path: previewPath, content: previewText},
		{path: handoffPath, content: handoffText},
		{path: approvalPath, content: approvalText},
	} {
		if err := writeTextAtomic(item.path, item.content); err != nil {
			return err
		}
	}
	if diagnostics := lintDesignPreviewFile(previewPath, "ready"); len(diagnostics) > 0 {
		return fmt.Errorf("approved design preview failed deterministic validation: %s", joinDiagnostics(diagnostics))
	}
	return nil
}

func lintDesignPreviewFile(path, level string) []designDiagnostic {
	raw, err := os.ReadFile(path)
	if err != nil {
		return []designDiagnostic{{Code: "preview-missing-file", Message: fmt.Sprintf("%s does not exist", path), Path: path, Level: "error"}}
	}
	content := string(raw)
	parsed := parseHTMLSummary(content)
	var diagnostics []designDiagnostic
	if !regexp.MustCompile(`(?i)<!doctype\s+html\s*>`).MatchString(content) {
		addDesignDiagnostic(&diagnostics, "preview-missing-doctype", "design preview must declare <!doctype html>", "html")
	}
	if parsed.HTMLLang == "" {
		addDesignDiagnostic(&diagnostics, "preview-missing-language", "design preview must declare a document language", "html.lang")
	}
	if parsed.PreviewAttrs["data-design-preview-schema"] != designPreviewSchema {
		addDesignDiagnostic(&diagnostics, "preview-invalid-schema", "data-design-preview-schema must equal "+designPreviewSchema, "data-design-preview-schema")
	}
	if len(parsed.DirectionIDs) != 3 {
		addDesignDiagnostic(&diagnostics, "preview-direction-count", "design preview must contain exactly three comparable directions", "data-direction-id")
	}
	if hasDuplicates(parsed.DirectionIDs) {
		addDesignDiagnostic(&diagnostics, "preview-duplicate-direction", "design direction IDs must be unique", "data-direction-id")
	}
	if !reflect.DeepEqual(parsed.DirectionIDs, parsed.DirectionAnchorIDs) {
		addDesignDiagnostic(&diagnostics, "preview-direction-anchor-mismatch", "every direction control must expose an id equal to its data-direction-id", "data-direction-id.id")
	}
	for _, section := range []string{"foundations", "components", "states", "motion", "responsive", "handoff"} {
		if !parsed.Sections[section] {
			addDesignDiagnostic(&diagnostics, "preview-missing-section", "design preview is missing required section: "+section, "data-preview-section."+section)
		}
	}
	manifest, err := parseJSONObject(parsed.PreviewManifestText)
	if err != nil {
		addDesignDiagnostic(&diagnostics, "preview-invalid-manifest", err.Error(), "script#"+designPreviewManifestID)
	} else {
		diagnostics = append(diagnostics, previewManifestDiagnostics(manifest, parsed.DirectionIDs, level == "ready")...)
	}
	for _, token := range []string{"--motion-duration-fast", "--motion-duration-base", "--motion-easing-standard", "--motion-easing-emphasized"} {
		if !strings.Contains(parsed.StyleText, token) {
			addDesignDiagnostic(&diagnostics, "preview-missing-motion-token", "design preview must define "+token, "style."+token)
		}
	}
	if !strings.Contains(parsed.StyleText, "prefers-reduced-motion: reduce") {
		addDesignDiagnostic(&diagnostics, "preview-missing-reduced-motion", "design preview must provide a prefers-reduced-motion fallback", "style.prefers-reduced-motion")
	}
	for _, signal := range []string{"location.hash", "hashchange"} {
		if !strings.Contains(parsed.ScriptText, signal) {
			addDesignDiagnostic(&diagnostics, "preview-missing-direction-routing", "design preview must open and track the selected direction from the URL fragment", "script."+signal)
		}
	}
	if len(parsed.ExternalDeps) > 0 || remoteReferenceRE.MatchString(content) || hasNonDataCSSURL(parsed.StyleText) || networkRuntimeRE.MatchString(parsed.ScriptText) {
		addDesignDiagnostic(&diagnostics, "preview-remote-dependency", "design preview must be a self-contained HTML file without external or network runtime dependencies", "html.dependencies")
	}
	if level == "ready" {
		status := strings.ToLower(strings.TrimSpace(parsed.PreviewAttrs["data-preview-status"]))
		if status != "candidate" && status != "approved" {
			addDesignDiagnostic(&diagnostics, "preview-not-candidate", "ready preview status must be candidate or approved", "data-preview-status")
		}
		if previewPlaceholderRE.MatchString(content) {
			addDesignDiagnostic(&diagnostics, "preview-unresolved-placeholder", "ready preview must not contain unresolved __PLACEHOLDER__ values", "html")
		}
		review, _ := manifest["review"].(map[string]any)
		if status == "candidate" && (review == nil || strings.ToLower(strings.TrimSpace(fmt.Sprint(review["status"]))) != "candidate" || nonEmpty(review["approved_direction"])) {
			addDesignDiagnostic(&diagnostics, "preview-manifest-candidate-mismatch", "candidate preview manifest must record candidate status without an approved direction", "manifest.review")
		}
		if status == "approved" {
			approved := strings.TrimSpace(parsed.PreviewAttrs["data-approved-direction"])
			if !stringInSlice(approved, parsed.DirectionIDs) {
				addDesignDiagnostic(&diagnostics, "preview-invalid-approval", "approved preview must name one existing data-direction-id", "data-approved-direction")
			}
			if review == nil || strings.ToLower(strings.TrimSpace(fmt.Sprint(review["status"]))) != "approved" || strings.TrimSpace(fmt.Sprint(review["approved_direction"])) != approved {
				addDesignDiagnostic(&diagnostics, "preview-manifest-approval-mismatch", "approved preview manifest must record the same approved direction", "manifest.review")
			}
			diagnostics = append(diagnostics, validatePreviewApprovalSidecar(path, content, approved, manifest)...)
		}
	}
	return diagnostics
}

func lintUITargetFile(path, level string) []designDiagnostic {
	raw, err := os.ReadFile(path)
	if err != nil {
		return []designDiagnostic{{Code: "ui-target-missing-file", Message: fmt.Sprintf("%s does not exist", path), Path: path, Level: "error"}}
	}
	content := string(raw)
	parsed := parseHTMLSummary(content)
	var diagnostics []designDiagnostic
	if !regexp.MustCompile(`(?i)<!doctype\s+html\s*>`).MatchString(content) {
		addDesignDiagnostic(&diagnostics, "ui-target-missing-doctype", "UI target must declare <!doctype html>", "html")
	}
	if parsed.HTMLLang == "" {
		addDesignDiagnostic(&diagnostics, "ui-target-missing-language", "UI target must declare a document language", "html.lang")
	}
	if parsed.TargetAttrs["data-ui-target-schema"] != uiTargetSchema {
		addDesignDiagnostic(&diagnostics, "ui-target-invalid-schema", "data-ui-target-schema must equal "+uiTargetSchema, "data-ui-target-schema")
	}
	manifest, err := parseJSONObject(parsed.UITargetManifest)
	if err != nil {
		addDesignDiagnostic(&diagnostics, "ui-target-invalid-manifest", err.Error(), "script#"+uiTargetManifestID)
		manifest = map[string]any{}
	} else if manifest["schema"] != uiTargetManifestSchema {
		addDesignDiagnostic(&diagnostics, "ui-target-invalid-manifest-schema", "UI target manifest schema must equal "+uiTargetManifestSchema, "manifest.schema")
	}
	if len(parsed.InlineEventHandlers) > 0 {
		addDesignDiagnostic(&diagnostics, "ui-target-inline-event-handler", "UI target must use bounded event listeners, not inline event-handler attributes", "html.events")
	}
	if len(parsed.ExternalDeps) > 0 || remoteReferenceRE.MatchString(content) || hasNonDataCSSURL(parsed.StyleText) || uiPersistenceRuntimeRE.MatchString(content) {
		addDesignDiagnostic(&diagnostics, "ui-target-forbidden-runtime", "UI target must be self-contained and must not load remote assets, call a network, or persist data", "html.dependencies")
	}
	for _, css := range []string{"@container", "prefers-reduced-motion: reduce", "--target-width"} {
		if !strings.Contains(parsed.StyleText, css) {
			addDesignDiagnostic(&diagnostics, "ui-target-missing-responsive-contract", "UI target must include "+css, "style."+css)
		}
	}
	for _, js := range []string{"URLSearchParams", "location.hash", "hashchange", "addEventListener"} {
		if !strings.Contains(parsed.ScriptText, js) {
			addDesignDiagnostic(&diagnostics, "ui-target-missing-review-control", "UI target review runtime must include "+js, "script."+js)
		}
	}
	if !stringSetEqual(listToStringSet(manifest["viewports"]), parsed.Widths) || len(parsed.Widths) < 2 {
		addDesignDiagnostic(&diagnostics, "ui-target-viewport-mismatch", "manifest viewports must match at least two rendered viewport controls", "manifest.viewports")
	}
	states := listToStringSet(manifest["required_states"])
	if !stringSetContainsAll(states, []string{"default", "loading", "empty", "error"}) || !stringSetEqual(states, parsed.States) {
		addDesignDiagnostic(&diagnostics, "ui-target-state-mismatch", "manifest required_states must match rendered controls and include default/loading/empty/error", "manifest.required_states")
	}
	if level == "ready" {
		if manifest["configured"] != true {
			addDesignDiagnostic(&diagnostics, "ui-target-not-configured", "ready UI target manifest must set configured to true", "manifest.configured")
		}
		if previewPlaceholderRE.MatchString(content) {
			addDesignDiagnostic(&diagnostics, "ui-target-unresolved-placeholder", "ready UI target must not contain unresolved __PLACEHOLDER__ values", "html")
		}
		status := strings.ToLower(strings.TrimSpace(parsed.TargetAttrs["data-status"]))
		if status != "candidate" && status != "locked" {
			addDesignDiagnostic(&diagnostics, "ui-target-invalid-status", "ready UI target status must be candidate or locked", "data-status")
		}
		fidelity := strings.ToLower(strings.TrimSpace(parsed.TargetAttrs["data-fidelity"]))
		if fidelity != "approximate" && fidelity != "high" && fidelity != "inspiration" {
			addDesignDiagnostic(&diagnostics, "ui-target-invalid-fidelity", "ready UI target must name approximate, high, or inspiration fidelity", "data-fidelity")
		}
		validateUITargetReadyManifest(manifest, &diagnostics)
	}
	return diagnostics
}

func parseDesignCapabilityProfileIDs(value string) ([]string, error) {
	parts := strings.Split(value, ",")
	var profileIDs []string
	seen := map[string]bool{}
	for _, part := range parts {
		profileID := strings.ToLower(strings.TrimSpace(part))
		if profileID == "" {
			continue
		}
		if seen[profileID] {
			return nil, fmt.Errorf("design capability profiles must be unique")
		}
		seen[profileID] = true
		profileIDs = append(profileIDs, profileID)
	}
	if len(profileIDs) == 0 {
		return nil, fmt.Errorf("at least one design capability profile is required")
	}
	return profileIDs, nil
}

func loadDesignCapabilityRegistry() (map[string]any, error) {
	source, err := locateTemplate("design-capability-profiles.json")
	if err != nil {
		return nil, err
	}
	raw, err := os.ReadFile(source)
	if err != nil {
		return nil, err
	}
	registry := map[string]any{}
	if err := json.Unmarshal(raw, &registry); err != nil {
		return nil, fmt.Errorf("cannot read design capability profiles: %v", err)
	}
	if strings.TrimSpace(fmt.Sprint(registry["schema"])) != designCapabilityProfilesSchema {
		return nil, fmt.Errorf("design capability profile registry has an invalid schema")
	}
	profiles, ok := registry["profiles"].([]any)
	if !ok || len(profiles) == 0 {
		return nil, fmt.Errorf("design capability profile registry has no profiles")
	}
	return registry, nil
}

func designAnyStringList(values []string) []any {
	result := make([]any, 0, len(values))
	for _, value := range values {
		result = append(result, value)
	}
	return result
}

func appendUniqueStrings(target []string, seen map[string]bool, raw any) []string {
	for _, value := range stringList(raw) {
		if !seen[value] {
			target = append(target, value)
			seen[value] = true
		}
	}
	return target
}

func selectDesignCapabilityProfiles(profileIDs []string) ([]map[string]any, error) {
	registry, err := loadDesignCapabilityRegistry()
	if err != nil {
		return nil, err
	}
	profilesByID := map[string]map[string]any{}
	var available []string
	for _, raw := range registry["profiles"].([]any) {
		profile, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		profileID := strings.TrimSpace(fmt.Sprint(profile["id"]))
		profilesByID[profileID] = profile
		available = append(available, profileID)
	}
	selected := make([]map[string]any, 0, len(profileIDs))
	for _, profileID := range profileIDs {
		profile := profilesByID[profileID]
		if profile == nil {
			return nil, fmt.Errorf("unknown design capability profile %s; choose from %s", profileID, strings.Join(available, ", "))
		}
		selected = append(selected, profile)
	}
	for _, profile := range selected {
		if profile["preview_required"] != true {
			if len(selected) > 1 {
				return nil, fmt.Errorf("no-ui cannot be combined with visual design capability profiles")
			}
			return nil, fmt.Errorf("profile no-ui has no visual design surface; %s", strings.TrimSpace(fmt.Sprint(profile["exit_contract"])))
		}
	}
	return selected, nil
}

func applyDesignCapabilityProfiles(manifest map[string]any, profileIDs []string) error {
	profiles, err := selectDesignCapabilityProfiles(profileIDs)
	if err != nil {
		return err
	}
	var specimens []any
	var capabilityIDs, inputModes, measurementUnits []string
	capabilitySeen := map[string]bool{}
	inputSeen := map[string]bool{}
	unitSeen := map[string]bool{}
	var profileContracts []any
	for _, profile := range profiles {
		profileID := strings.TrimSpace(fmt.Sprint(profile["id"]))
		profileContracts = append(profileContracts, map[string]any{
			"id":                profileID,
			"label":             profile["label"],
			"summary":           profile["summary"],
			"input_modes":       cloneJSONValue(profile["input_modes"]),
			"measurement_units": cloneJSONValue(profile["measurement_units"]),
		})
		capabilityIDs = appendUniqueStrings(capabilityIDs, capabilitySeen, profile["capability_ids"])
		inputModes = appendUniqueStrings(inputModes, inputSeen, profile["input_modes"])
		measurementUnits = appendUniqueStrings(measurementUnits, unitSeen, profile["measurement_units"])
		for _, raw := range profile["specimens"].([]any) {
			specimen, ok := raw.(map[string]any)
			if !ok {
				continue
			}
			cloned := cloneJSONMap(specimen)
			cloned["profile_id"] = profileID
			specimens = append(specimens, cloned)
		}
	}
	manifest["capability_model"] = map[string]any{
		"schema":            designCapabilityModelSchema,
		"profile_ids":       designAnyStringList(profileIDs),
		"profiles":          profileContracts,
		"capability_ids":    designAnyStringList(capabilityIDs),
		"input_modes":       designAnyStringList(inputModes),
		"measurement_units": designAnyStringList(measurementUnits),
		"specimens":         specimens,
	}
	if project, ok := manifest["project"].(map[string]any); ok {
		project["platforms"] = designAnyStringList(profileIDs)
	}
	var specimenIDs []string
	for _, raw := range specimens {
		specimen, _ := raw.(map[string]any)
		specimenIDs = append(specimenIDs, strings.TrimSpace(fmt.Sprint(specimen["id"])))
	}
	for _, raw := range manifest["directions"].([]any) {
		if direction, ok := raw.(map[string]any); ok {
			direction["specimen_ids"] = designAnyStringList(specimenIDs)
		}
	}
	decisionIDs := manifestDecisionIDs(manifest)
	handoff, ok := manifest["handoff"].(map[string]any)
	if !ok {
		handoff = map[string]any{}
		manifest["handoff"] = handoff
	}
	if len(profileIDs) == 1 && profileIDs[0] == "web" {
		handoff["reproduction_mode"] = "exact"
	} else {
		handoff["reproduction_mode"] = "platform-adapted"
	}
	var components, responsive, acceptance []any
	for _, profile := range profiles {
		profileID := strings.TrimSpace(fmt.Sprint(profile["id"]))
		var profileSpecimenIDs, requiredStates []string
		stateSeen := map[string]bool{}
		for _, raw := range specimens {
			specimen, ok := raw.(map[string]any)
			if !ok || strings.TrimSpace(fmt.Sprint(specimen["profile_id"])) != profileID {
				continue
			}
			profileSpecimenIDs = append(profileSpecimenIDs, strings.TrimSpace(fmt.Sprint(specimen["id"])))
			requiredStates = appendUniqueStrings(requiredStates, stateSeen, specimen["required_states"])
		}
		if rawContract, ok := profile["component_contract"].(map[string]any); ok {
			contract := cloneJSONMap(rawContract)
			contract["required_states"] = designAnyStringList(requiredStates)
			contract["decision_ids"] = designAnyStringList(decisionIDs)
			components = append(components, contract)
		}
		for _, raw := range profile["targets"].([]any) {
			target, ok := raw.(map[string]any)
			if !ok {
				continue
			}
			targetID := strings.TrimSpace(fmt.Sprint(target["id"]))
			responsive = append(responsive, map[string]any{
				"id":              targetID,
				"profile_id":      profileID,
				"label":           target["label"],
				"target":          cloneJSONValue(target["target"]),
				"review_width_px": target["review_width_px"],
				"state":           "default",
				"adaptation":      target["adaptation"],
				"decision_ids":    designAnyStringList(decisionIDs),
			})
			acceptance = append(acceptance, map[string]any{
				"id":           target["acceptance_id"],
				"target_id":    targetID,
				"specimen_ids": designAnyStringList(profileSpecimenIDs),
				"states":       designAnyStringList(requiredStates),
				"color_modes":  cloneJSONValue(profile["color_modes"]),
				"motion_modes": cloneJSONValue(profile["motion_modes"]),
				"decision_ids": designAnyStringList(decisionIDs),
				"must_match": designAnyStringList([]string{
					"structure", "geometry", "tokens", "content", "state", "motion",
				}),
				"evidence": designAnyStringList([]string{
					"structure_snapshot", "visual_capture", "runtime_diagnostics", "visual_comparison_or_human_review",
				}),
			})
		}
	}
	handoff["component_contracts"] = components
	handoff["responsive_matrix"] = responsive
	handoff["visual_acceptance_matrix"] = acceptance
	return nil
}

func scaffoldDesignPreviewManifest(outPath string, force bool, profileIDs []string) (string, error) {
	if _, err := os.Stat(outPath); err == nil && !force {
		return "", fmt.Errorf("design preview manifest already exists: %s", outPath)
	}
	if strings.HasSuffix(strings.ToLower(outPath), ".manifest.json") {
		previewPath := strings.TrimSuffix(outPath, ".manifest.json") + ".html"
		if raw, err := os.ReadFile(previewPath); err == nil {
			status := strings.ToLower(strings.TrimSpace(parseHTMLSummary(string(raw)).PreviewAttrs["data-preview-status"]))
			if status == "approved" {
				return "", fmt.Errorf("approved design preview cannot be overwritten: %s", previewPath)
			}
		}
	}
	source, err := locateTemplate("design-preview-template.html")
	if err != nil {
		return "", err
	}
	raw, err := os.ReadFile(source)
	if err != nil {
		return "", err
	}
	manifest, err := parseJSONObject(parseHTMLSummary(string(raw)).PreviewManifestText)
	if err != nil {
		return "", fmt.Errorf("design preview template has no %s: %v", designPreviewManifestID, err)
	}
	if err := applyDesignCapabilityProfiles(manifest, profileIDs); err != nil {
		return "", err
	}
	review, _ := manifest["review"].(map[string]any)
	if review == nil {
		review = map[string]any{}
		manifest["review"] = review
	}
	base := strings.TrimSuffix(filepath.Base(outPath), filepath.Ext(outPath))
	if match := regexp.MustCompile(`(?i)^round-(\d+)\.manifest$`).FindStringSubmatch(base); match != nil {
		if number, parseErr := strconv.Atoi(match[1]); parseErr == nil {
			review["round"] = strconv.Itoa(number)
		}
	}
	review["status"] = "scaffold"
	review["approved_direction"] = nil
	manifest["configured"] = false
	return outPath, writeJSONAtomic(outPath, manifest)
}

func renderDesignPreview(manifestPath, outPath string, force bool) (string, error) {
	if raw, err := os.ReadFile(outPath); err == nil {
		status := strings.ToLower(strings.TrimSpace(parseHTMLSummary(string(raw)).PreviewAttrs["data-preview-status"]))
		if status == "approved" {
			return "", fmt.Errorf("approved design preview cannot be overwritten: %s", outPath)
		}
		if !force {
			return "", fmt.Errorf("design preview already exists: %s", outPath)
		}
	}
	rawManifest, err := os.ReadFile(manifestPath)
	if err != nil {
		return "", fmt.Errorf("design preview manifest does not exist: %s", manifestPath)
	}
	manifest := map[string]any{}
	if err := json.Unmarshal(rawManifest, &manifest); err != nil {
		return "", fmt.Errorf("cannot read design preview manifest %s: %v", manifestPath, err)
	}
	review, _ := manifest["review"].(map[string]any)
	if review == nil {
		review = map[string]any{}
		manifest["review"] = review
	}
	round := previewRoundFromPath(outPath)
	if round == "" {
		round = strings.TrimSpace(fmt.Sprint(review["round"]))
	}
	if round == "" || round == "<nil>" {
		return "", fmt.Errorf("design preview review.round is required when --out is not round-NN.html")
	}
	manifest["configured"] = true
	review["round"] = round
	review["status"] = "candidate"
	review["approved_direction"] = nil
	directionIDs := manifestDirectionIDs(manifest)
	if diagnostics := previewManifestDiagnostics(manifest, directionIDs, true); len(diagnostics) > 0 {
		return "", fmt.Errorf("design preview manifest is not ready: %s", joinDiagnostics(diagnostics))
	}
	source, err := locateTemplate("design-preview-template.html")
	if err != nil {
		return "", err
	}
	rawTemplate, err := os.ReadFile(source)
	if err != nil {
		return "", err
	}
	content := renderPreviewDirectionIDs(string(rawTemplate), directionIDs)
	content, err = replaceEmbeddedJSON(content, designPreviewManifestID, manifest)
	if err != nil {
		return "", err
	}
	for _, pair := range [][2]string{
		{"data-preview-status", "candidate"},
		{"data-review-round", round},
		{"data-approved-direction", ""},
		{"data-active-direction", directionIDs[0]},
	} {
		content, err = replaceHTMLAttribute(content, pair[0], pair[1])
		if err != nil {
			return "", err
		}
	}
	if err := os.MkdirAll(filepath.Dir(outPath), 0o755); err != nil {
		return "", err
	}
	temp, err := os.CreateTemp(filepath.Dir(outPath), "."+filepath.Base(outPath)+"-render-check-*.html")
	if err != nil {
		return "", err
	}
	tempPath := temp.Name()
	defer os.Remove(tempPath)
	if _, err := temp.WriteString(content); err != nil {
		_ = temp.Close()
		return "", err
	}
	if err := temp.Close(); err != nil {
		return "", err
	}
	if diagnostics := lintDesignPreviewFile(tempPath, "ready"); len(diagnostics) > 0 {
		return "", fmt.Errorf("rendered design preview is not ready: %s", joinDiagnostics(diagnostics))
	}
	return outPath, writeTextAtomic(outPath, content)
}

func renderPreviewDirectionIDs(content string, directionIDs []string) string {
	sourceIDs := []string{"direction-a", "direction-b", "direction-c"}
	sentinels := []string{"__SPECIFY_DIRECTION_SLOT_A__", "__SPECIFY_DIRECTION_SLOT_B__", "__SPECIFY_DIRECTION_SLOT_C__"}
	for index, sourceID := range sourceIDs {
		content = strings.ReplaceAll(content, sourceID, sentinels[index])
	}
	for index, sentinel := range sentinels {
		content = strings.ReplaceAll(content, sentinel, directionIDs[index])
	}
	return content
}

func scaffoldDesignPreview(outPath string, force bool) (string, error) {
	if _, err := os.Stat(outPath); err == nil {
		if !force {
			return "", fmt.Errorf("design preview already exists: %s", outPath)
		}
		raw, readErr := os.ReadFile(outPath)
		if readErr != nil {
			return "", fmt.Errorf("cannot inspect existing design preview %s: %v", outPath, readErr)
		}
		if strings.ToLower(parseHTMLSummary(string(raw)).PreviewAttrs["data-preview-status"]) == "approved" {
			return "", fmt.Errorf("approved design preview cannot be overwritten: %s", outPath)
		}
	}
	source, err := locateTemplate("design-preview-template.html")
	if err != nil {
		return "", err
	}
	if diagnostics := lintDesignPreviewFile(source, "structural"); len(diagnostics) > 0 {
		return "", fmt.Errorf("bundled design preview template is invalid: %s", joinDiagnostics(diagnostics))
	}
	raw, err := os.ReadFile(source)
	if err != nil {
		return "", err
	}
	content := string(raw)
	if round := previewRoundFromPath(outPath); round != "" {
		content = strings.ReplaceAll(content, "__ROUND_NUMBER__", round)
		content = regexp.MustCompile(`(data-review-round=")[^"]*(")`).ReplaceAllString(content, `${1}`+round+`${2}`)
	}
	return outPath, writeTextAtomic(outPath, content)
}

func scaffoldUITarget(outPath string, force bool) (string, error) {
	if _, err := os.Stat(outPath); err == nil && !force {
		return "", fmt.Errorf("UI target already exists: %s", outPath)
	}
	source, err := locateTemplate("ui-target-template.html")
	if err != nil {
		return "", err
	}
	if diagnostics := lintUITargetFile(source, "structural"); len(diagnostics) > 0 {
		return "", fmt.Errorf("bundled UI target template is invalid: %s", joinDiagnostics(diagnostics))
	}
	raw, err := os.ReadFile(source)
	if err != nil {
		return "", err
	}
	return outPath, writeTextAtomic(outPath, string(raw))
}

func parseDesignMarkdown(text, source string) (designDocument, error) {
	match := frontMatterRE.FindStringSubmatch(text)
	if match == nil {
		return designDocument{}, fmt.Errorf("%s: missing YAML front matter", source)
	}
	frontMatter, err := parseDesignYAML(match[1])
	if err != nil {
		return designDocument{}, fmt.Errorf("%s: invalid YAML front matter: %v", source, err)
	}
	ds, ok := frontMatter["design_system"].(map[string]any)
	if !ok {
		return designDocument{}, fmt.Errorf("%s: missing design_system mapping", source)
	}
	return designDocument{Source: source, FrontMatter: frontMatter, DesignSystem: ds, Body: match[2]}, nil
}

func parseDesignYAML(text string) (map[string]any, error) {
	root := map[string]any{}
	type frame struct {
		indent int
		value  any
		parent map[string]any
		key    string
	}
	stack := []frame{{indent: -1, value: root}}
	lines := strings.Split(strings.ReplaceAll(text, "\r\n", "\n"), "\n")
	for lineIndex, raw := range lines {
		if strings.TrimSpace(raw) == "" || strings.HasPrefix(strings.TrimSpace(raw), "#") {
			continue
		}
		indent := len(raw) - len(strings.TrimLeft(raw, " "))
		line := strings.TrimSpace(raw)
		for len(stack) > 1 && indent <= stack[len(stack)-1].indent {
			stack = stack[:len(stack)-1]
		}
		parent := stack[len(stack)-1].value
		if strings.HasPrefix(line, "- ") {
			itemText := strings.TrimSpace(strings.TrimPrefix(line, "- "))
			list, ok := parent.([]any)
			if !ok {
				return nil, fmt.Errorf("list item has no list parent near %q", line)
			}
			item := parseDesignYAMLScalar(itemText)
			if strings.Contains(itemText, ":") && !strings.HasPrefix(itemText, `"`) {
				parts := strings.SplitN(itemText, ":", 2)
				item = map[string]any{strings.TrimSpace(parts[0]): parseDesignYAMLScalar(strings.TrimSpace(parts[1]))}
			}
			list = append(list, item)
			stack[len(stack)-1].value = list
			if stack[len(stack)-1].parent != nil {
				stack[len(stack)-1].parent[stack[len(stack)-1].key] = list
			}
			if m, ok := item.(map[string]any); ok {
				stack = append(stack, frame{indent: indent, value: m})
			}
			continue
		}
		parts := strings.SplitN(line, ":", 2)
		if len(parts) != 2 {
			return nil, fmt.Errorf("unsupported YAML line %q", line)
		}
		key := strings.TrimSpace(parts[0])
		valueText := strings.TrimSpace(parts[1])
		if valueText == "" {
			nextIsList := nextMeaningfulIndentedLineIsList(lines, lineIndex)
			var child any
			if nextIsList {
				child = []any{}
			} else {
				child = map[string]any{}
			}
			parentMap, ok := parent.(map[string]any)
			if !ok {
				return nil, fmt.Errorf("mapping entry has no mapping parent near %q", line)
			}
			parentMap[key] = child
			stack = append(stack, frame{indent: indent, value: child, parent: parentMap, key: key})
			continue
		}
		parentMap, ok := parent.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("mapping entry has no mapping parent near %q", line)
		}
		parentMap[key] = parseDesignYAMLScalar(valueText)
	}
	return root, nil
}

func nextMeaningfulIndentedLineIsList(lines []string, currentIndex int) bool {
	currentRaw := lines[currentIndex]
	currentIndent := len(currentRaw) - len(strings.TrimLeft(currentRaw, " "))
	for _, raw := range lines[currentIndex+1:] {
		if strings.TrimSpace(raw) == "" {
			continue
		}
		indent := len(raw) - len(strings.TrimLeft(raw, " "))
		if indent <= currentIndent {
			return false
		}
		return strings.HasPrefix(strings.TrimSpace(raw), "- ")
	}
	return false
}

func parseDesignYAMLScalar(value string) any {
	value = strings.TrimSpace(value)
	switch value {
	case "[]":
		return []any{}
	case "{}":
		return map[string]any{}
	case "null", "None", "~":
		return nil
	case "true":
		return true
	case "false":
		return false
	}
	if strings.HasPrefix(value, `"`) && strings.HasSuffix(value, `"`) {
		if unquoted, err := strconv.Unquote(value); err == nil {
			return unquoted
		}
	}
	if strings.HasPrefix(value, "'") && strings.HasSuffix(value, "'") {
		return strings.TrimSuffix(strings.TrimPrefix(value, "'"), "'")
	}
	if number, err := strconv.Atoi(value); err == nil {
		return number
	}
	return value
}

func validateDesignSystem(doc designDocument, diagnostics *[]designDiagnostic) {
	ds := doc.DesignSystem
	if ds["schema"] != "spec-kit-design-v1" {
		addDesignDiagnostic(diagnostics, "invalid-schema", "schema must equal spec-kit-design-v1", "design_system.schema")
	}
	if platforms, ok := ds["platforms"].([]any); !ok || len(platforms) == 0 {
		addDesignDiagnostic(diagnostics, "invalid-platforms", "platforms must be a non-empty list", "design_system.platforms")
	}
	tokens, ok := ds["tokens"].(map[string]any)
	if !ok {
		addDesignDiagnostic(diagnostics, "invalid-tokens", "tokens must be a mapping", "design_system.tokens")
		tokens = map[string]any{}
	}
	for _, category := range []string{"color", "spacing", "radius", "typography", "motion"} {
		if _, ok := tokens[category]; !ok {
			addDesignDiagnostic(diagnostics, "missing-token-category", "tokens must include "+category, "design_system.tokens."+category)
		}
	}
	for category, rawEntries := range tokens {
		entries, ok := rawEntries.(map[string]any)
		if !ok {
			addDesignDiagnostic(diagnostics, "invalid-token-category", "token category "+category+" must be a mapping", "design_system.tokens."+category)
			continue
		}
		for name, rawToken := range entries {
			tokenPath := "design_system.tokens." + category + "." + name
			if !tokenNameRE.MatchString(name) {
				addDesignDiagnostic(diagnostics, "invalid-token-name", "invalid token name "+name, tokenPath)
			}
			token, ok := rawToken.(map[string]any)
			if !ok {
				addDesignDiagnostic(diagnostics, "invalid-token", category+"."+name+" must be a mapping", tokenPath)
				continue
			}
			for _, key := range []string{"value", "usage"} {
				if _, ok := token[key]; !ok {
					addDesignDiagnostic(diagnostics, "invalid-token", category+"."+name+" must include "+key, tokenPath)
				}
			}
		}
	}
	components, ok := ds["components"].(map[string]any)
	if !ok {
		addDesignDiagnostic(diagnostics, "invalid-components", "components must be a mapping", "design_system.components")
		components = map[string]any{}
	}
	for name, raw := range components {
		component, ok := raw.(map[string]any)
		if !ok {
			addDesignDiagnostic(diagnostics, "invalid-component", name+" must be a mapping", "design_system.components."+name)
			continue
		}
		if states, ok := component["required_states"].([]any); !ok || len(states) == 0 {
			addDesignDiagnostic(diagnostics, "invalid-component-states", name+" required_states must be a non-empty list", "design_system.components."+name+".required_states")
		}
		if refs, exists := component["decision_refs"]; exists && !isNonEmptyStringList(refs, false) {
			addDesignDiagnostic(diagnostics, "invalid-component-decision-refs", name+" decision_refs must be a string list", "design_system.components."+name+".decision_refs")
		}
	}
	decisions, ok := ds["decisions"].([]any)
	if raw, exists := ds["decisions"]; exists && !ok {
		_ = raw
		addDesignDiagnostic(diagnostics, "invalid-design-decisions", "decisions must be a list", "design_system.decisions")
	}
	seen := map[string]bool{}
	for index, raw := range decisions {
		decision, ok := raw.(map[string]any)
		path := fmt.Sprintf("design_system.decisions[%d]", index)
		if !ok {
			addDesignDiagnostic(diagnostics, "invalid-design-decision", "each design decision must be a mapping", path)
			continue
		}
		id := strings.TrimSpace(fmt.Sprint(decision["id"]))
		if !strings.Contains(id, "{{") && !canonicalDecisionIDRE.MatchString(id) {
			addDesignDiagnostic(diagnostics, "invalid-design-decision-id", "design decision IDs must use a stable DS-<KIND>-<NUMBER> form", path+".id")
		}
		if seen[id] {
			addDesignDiagnostic(diagnostics, "duplicate-design-decision-id", "design decision IDs must be unique", "design_system.decisions")
		}
		seen[id] = true
		for _, field := range []string{"kind", "statement", "source_ref", "verification"} {
			if strings.TrimSpace(fmt.Sprint(decision[field])) == "" || fmt.Sprint(decision[field]) == "<nil>" {
				addDesignDiagnostic(diagnostics, "incomplete-design-decision", "design decision "+id+" must include "+field, path+"."+field)
			}
		}
	}
	accessibility, ok := ds["accessibility"].(map[string]any)
	if !ok {
		addDesignDiagnostic(diagnostics, "invalid-accessibility", "accessibility must be a mapping", "design_system.accessibility")
		accessibility = map[string]any{}
	}
	for _, key := range []string{"contrast_intent", "focus_visible", "keyboard_navigation", "reduced_motion"} {
		if _, ok := accessibility[key]; !ok {
			addDesignDiagnostic(diagnostics, "missing-accessibility-key", "accessibility must include "+key, "design_system.accessibility."+key)
		}
	}
}

func validateMarkdownSections(doc designDocument, diagnostics *[]designDiagnostic) {
	for _, section := range []string{"Product Feel", "Platforms", "Component Rules", "Anti-Patterns", "Design Change Policy", "UI QA Checklist"} {
		re := headingRECache[section]
		if re == nil {
			re = regexp.MustCompile(`(?m)^##+\s+` + regexp.QuoteMeta(section) + `\s*$`)
			headingRECache[section] = re
		}
		if !re.MatchString(doc.Body) {
			addDesignDiagnostic(diagnostics, "missing-section", "missing required Markdown section: "+section, section)
		}
	}
}

func validateTokenReferences(doc designDocument, diagnostics *[]designDiagnostic) {
	tokens, ok := doc.DesignSystem["tokens"].(map[string]any)
	if !ok {
		return
	}
	known := map[string]bool{}
	for category, rawEntries := range tokens {
		if entries, ok := rawEntries.(map[string]any); ok {
			for name := range entries {
				known[category+"."+name] = true
			}
		}
	}
	components, ok := doc.DesignSystem["components"].(map[string]any)
	if !ok {
		return
	}
	for componentName, rawComponent := range components {
		component, ok := rawComponent.(map[string]any)
		if !ok {
			continue
		}
		refs, ok := component["token_refs"].(map[string]any)
		if !ok {
			addDesignDiagnostic(diagnostics, "invalid-token-reference", componentName+" token_refs must be a mapping of string token references", "design_system.components."+componentName+".token_refs")
			continue
		}
		for refName, rawRef := range refs {
			ref, ok := rawRef.(string)
			path := "design_system.components." + componentName + ".token_refs." + refName
			if !ok {
				addDesignDiagnostic(diagnostics, "invalid-token-reference", "token reference must be a string: "+refName, path)
				continue
			}
			match := tokenRefRE.FindStringSubmatch(ref)
			if match == nil {
				addDesignDiagnostic(diagnostics, "invalid-token-reference", "token reference must use {category.token.name} syntax: "+ref, path)
				continue
			}
			if !known[match[1]+"."+match[2]] {
				addDesignDiagnostic(diagnostics, "unknown-token-reference", "unknown token reference {"+match[1]+"."+match[2]+"}", path)
			}
		}
	}
}

func validateDesignReadiness(doc designDocument, diagnostics *[]designDiagnostic) {
	ds := doc.DesignSystem
	if strings.ToLower(strings.TrimSpace(fmt.Sprint(ds["status"]))) != "approved" {
		addDesignDiagnostic(diagnostics, "design-not-approved", "design_system.status must equal approved for downstream UI work", "design_system.status")
	}
	approval, ok := ds["approval"].(map[string]any)
	if !ok {
		addDesignDiagnostic(diagnostics, "missing-design-approval", "design_system.approval must record the approved direction and source references", "design_system.approval")
	} else {
		if strings.ToLower(strings.TrimSpace(fmt.Sprint(approval["status"]))) != "approved" {
			addDesignDiagnostic(diagnostics, "missing-design-approval", "design_system.approval.status must equal approved", "design_system.approval.status")
		}
		if !isNonEmptyStringList(approval["source_refs"], true) {
			addDesignDiagnostic(diagnostics, "missing-design-provenance", "design_system.approval.source_refs must identify product or repository evidence", "design_system.approval.source_refs")
		}
		if !isNonEmptyStringList(approval["visual_refs"], true) {
			addDesignDiagnostic(diagnostics, "missing-approved-visual-reference", "design_system.approval.visual_refs must identify the exact inspectable artifact approved by the user", "design_system.approval.visual_refs")
		}
		for _, field := range []string{"preview_sha256", "manifest_sha256", "handoff_sha256"} {
			if !hexDigestRE.MatchString(strings.TrimSpace(fmt.Sprint(approval[field]))) {
				addDesignDiagnostic(diagnostics, "missing-approved-preview-digest", "design_system.approval."+field+" must be a SHA-256 digest", "design_system.approval."+field)
			}
		}
		handoffRef := strings.TrimSpace(fmt.Sprint(approval["handoff_ref"]))
		if handoffRef == "" || handoffRef == "<nil>" || !strings.HasSuffix(strings.ToLower(handoffRef), ".handoff.json") {
			addDesignDiagnostic(diagnostics, "missing-approved-handoff-reference", "design_system.approval.handoff_ref must identify the immutable design handoff", "design_system.approval.handoff_ref")
		}
		if strings.TrimSpace(fmt.Sprint(approval["review_round"])) == "" || fmt.Sprint(approval["review_round"]) == "<nil>" {
			addDesignDiagnostic(diagnostics, "missing-approved-review-round", "design_system.approval.review_round must identify the approved round", "design_system.approval.review_round")
		}
		if !isNonEmptyStringList(approval["decision_ids"], true) {
			addDesignDiagnostic(diagnostics, "missing-approved-decision-ids", "design_system.approval.decision_ids must freeze the approved DS-* set", "design_system.approval.decision_ids")
		}
		if !isNonEmptyStringList(approval["handoff_contract_ids"], true) {
			addDesignDiagnostic(diagnostics, "missing-approved-handoff-contract-ids", "design_system.approval.handoff_contract_ids must freeze the approved DH-* set", "design_system.approval.handoff_contract_ids")
		}
		if !isNonEmptyStringList(approval["capability_profile_ids"], true) {
			addDesignDiagnostic(diagnostics, "missing-approved-capability-profiles", "design_system.approval.capability_profile_ids must freeze the approved profile set", "design_system.approval.capability_profile_ids")
		}
		specimenIDs := stringList(approval["specimen_ids"])
		if len(specimenIDs) == 0 {
			addDesignDiagnostic(diagnostics, "missing-approved-specimens", "design_system.approval.specimen_ids must freeze the approved specimen set", "design_system.approval.specimen_ids")
		} else {
			for _, specimenID := range specimenIDs {
				if !designSpecimenIDRE.MatchString(specimenID) {
					addDesignDiagnostic(diagnostics, "missing-approved-specimens", "design_system.approval.specimen_ids must contain canonical SP-* IDs", "design_system.approval.specimen_ids")
					break
				}
			}
		}
		if !reflect.DeepEqual(stringList(ds["capability_profiles"]), stringList(approval["capability_profile_ids"])) {
			addDesignDiagnostic(diagnostics, "design-capability-profile-drift", "design_system.capability_profiles must exactly match approval.capability_profile_ids", "design_system.capability_profiles")
		}
		if !reflect.DeepEqual(stringList(ds["specimens"]), specimenIDs) {
			addDesignDiagnostic(diagnostics, "design-specimen-drift", "design_system.specimens must exactly match approval.specimen_ids", "design_system.specimens")
		}
		validateApprovedVisualReference(doc, approval, diagnostics)
	}
	if pc, ok := ds["product_context"].(map[string]any); !ok {
		addDesignDiagnostic(diagnostics, "missing-product-context", "approved design system must define product_context", "design_system.product_context")
	} else {
		for _, field := range []string{"subject", "audience", "single_job"} {
			if strings.TrimSpace(fmt.Sprint(pc[field])) == "" || fmt.Sprint(pc[field]) == "<nil>" {
				addDesignDiagnostic(diagnostics, "incomplete-product-context", "product_context."+field+" must be non-empty", "design_system.product_context."+field)
			}
		}
	}
	name := strings.ToLower(strings.TrimSpace(fmt.Sprint(ds["name"])))
	if name == "" || name == "project-design-system" || name == "bootstrap-design-seed" || strings.Contains(name, "{{") {
		addDesignDiagnostic(diagnostics, "generic-design-name", "design_system.name must be project-specific before downstream UI work", "design_system.name")
	}
}

func validateApprovedVisualReference(doc designDocument, approval map[string]any, diagnostics *[]designDiagnostic) {
	refs, ok := approval["visual_refs"].([]any)
	if !ok {
		return
	}
	for _, raw := range refs {
		ref, ok := raw.(string)
		if !ok || strings.Contains(ref, "://") || !strings.Contains(ref, "#") {
			continue
		}
		previewRef, direction, _ := strings.Cut(ref, "#")
		if !strings.HasSuffix(strings.ToLower(previewRef), ".html") || direction == "" {
			continue
		}
		previewPath := filepath.Join(filepath.Dir(doc.Source), filepath.FromSlash(previewRef))
		if diagnosticsPreview := lintDesignPreviewFile(previewPath, "ready"); len(diagnosticsPreview) > 0 {
			addDesignDiagnostic(diagnostics, "approved-preview-invalid", "approved visual reference is not a valid immutable preview: "+diagnosticsPreview[0].Code+": "+diagnosticsPreview[0].Message, ref)
			continue
		}
		sidecarPath := strings.TrimSuffix(previewPath, filepath.Ext(previewPath)) + ".approval.json"
		rawSidecar, err := os.ReadFile(sidecarPath)
		if err != nil {
			addDesignDiagnostic(diagnostics, "approved-preview-sidecar-invalid", "cannot read approved preview sidecar: "+err.Error(), sidecarPath)
			continue
		}
		var sidecar map[string]any
		if err := json.Unmarshal(rawSidecar, &sidecar); err != nil {
			addDesignDiagnostic(diagnostics, "approved-preview-sidecar-invalid", "cannot read approved preview sidecar: "+err.Error(), sidecarPath)
			continue
		}
		if strings.TrimSpace(fmt.Sprint(sidecar["direction_id"])) != direction || strings.TrimSpace(fmt.Sprint(approval["direction"])) != direction {
			addDesignDiagnostic(diagnostics, "approved-direction-reference-mismatch", "approval.direction must equal the approved visual reference fragment", "design_system.approval.direction")
		}
		for _, field := range []string{"preview_sha256", "manifest_sha256"} {
			sidecarField := map[string]string{"preview_sha256": "html_sha256", "manifest_sha256": "manifest_sha256"}[field]
			if strings.TrimSpace(fmt.Sprint(approval[field])) != strings.TrimSpace(fmt.Sprint(sidecar[sidecarField])) {
				addDesignDiagnostic(diagnostics, "approved-preview-digest-mismatch", "approval."+field+" must match the immutable preview sidecar", "design_system.approval."+field)
			}
		}
		if !reflect.DeepEqual(approval["decision_ids"], sidecar["decision_ids"]) {
			addDesignDiagnostic(diagnostics, "approved-decision-set-mismatch", "approval.decision_ids must exactly match the approved preview sidecar", "design_system.approval.decision_ids")
		}
		handoffRef := strings.TrimSpace(fmt.Sprint(approval["handoff_ref"]))
		if filepath.Base(filepath.FromSlash(handoffRef)) != strings.TrimSpace(fmt.Sprint(sidecar["handoff_ref"])) {
			addDesignDiagnostic(diagnostics, "approved-handoff-reference-mismatch", "approval.handoff_ref must match the immutable preview sidecar", "design_system.approval.handoff_ref")
		}
		if strings.TrimSpace(fmt.Sprint(approval["handoff_sha256"])) != strings.TrimSpace(fmt.Sprint(sidecar["handoff_sha256"])) {
			addDesignDiagnostic(diagnostics, "approved-handoff-digest-mismatch", "approval.handoff_sha256 must match the immutable preview sidecar", "design_system.approval.handoff_sha256")
		}
		if !stringSetEqual(listToStringSet(approval["handoff_contract_ids"]), listToStringSet(sidecar["handoff_contract_ids"])) {
			addDesignDiagnostic(diagnostics, "approved-handoff-contract-set-mismatch", "approval.handoff_contract_ids must exactly match the immutable preview sidecar", "design_system.approval.handoff_contract_ids")
		}
		for _, field := range []string{"capability_profile_ids", "specimen_ids"} {
			if !reflect.DeepEqual(stringList(approval[field]), stringList(sidecar[field])) {
				addDesignDiagnostic(diagnostics, "approved-capability-set-mismatch", "approval."+field+" must exactly match the immutable preview sidecar", "design_system.approval."+field)
			}
		}
		handoffPath := filepath.Join(filepath.Dir(doc.Source), filepath.FromSlash(handoffRef))
		rawHandoff, handoffErr := os.ReadFile(handoffPath)
		if handoffErr != nil {
			addDesignDiagnostic(diagnostics, "approved-handoff-invalid", "cannot read immutable design handoff: "+handoffErr.Error(), handoffPath)
			return
		}
		if sha256String(string(rawHandoff)) != strings.TrimSpace(fmt.Sprint(approval["handoff_sha256"])) {
			addDesignDiagnostic(diagnostics, "approved-handoff-digest-mismatch", "approval.handoff_sha256 must bind the immutable handoff bytes", "design_system.approval.handoff_sha256")
		}
		var handoff map[string]any
		if err := json.Unmarshal(rawHandoff, &handoff); err != nil || handoff["schema"] != designHandoffSchema {
			addDesignDiagnostic(diagnostics, "approved-handoff-invalid", "approved handoff must contain "+designHandoffSchema, handoffPath)
			return
		}
		handoffApproval, _ := handoff["approval"].(map[string]any)
		if strings.TrimSpace(fmt.Sprint(handoffApproval["direction_id"])) != direction || strings.TrimSpace(fmt.Sprint(handoffApproval["preview_sha256"])) != strings.TrimSpace(fmt.Sprint(approval["preview_sha256"])) || strings.TrimSpace(fmt.Sprint(handoffApproval["manifest_sha256"])) != strings.TrimSpace(fmt.Sprint(approval["manifest_sha256"])) {
			addDesignDiagnostic(diagnostics, "approved-handoff-approval-mismatch", "immutable handoff approval must preserve direction and preview/manifest digests", handoffPath)
		}
		return
	}
	addDesignDiagnostic(diagnostics, "missing-local-approved-preview", "approved UI design requires a local round-NN.html#direction-id reference", "design_system.approval.visual_refs")
}

func parseHTMLSummary(content string) htmlParseSummary {
	summary := htmlParseSummary{
		PreviewAttrs: map[string]string{}, TargetAttrs: map[string]string{}, Sections: map[string]bool{},
		Widths: map[string]bool{}, States: map[string]bool{},
	}
	tagRE := regexp.MustCompile(`(?is)<([a-z0-9-]+)\b([^>]*)>`)
	for _, match := range tagRE.FindAllStringSubmatch(content, -1) {
		tag := strings.ToLower(match[1])
		attrs := parseAttrs(match[2])
		if tag == "html" {
			summary.HTMLLang = strings.TrimSpace(attrs["lang"])
		}
		if _, ok := attrs["data-design-preview-schema"]; ok {
			summary.PreviewAttrs = attrs
		}
		if _, ok := attrs["data-ui-target-schema"]; ok {
			summary.TargetAttrs = attrs
		}
		if id := strings.TrimSpace(attrs["data-direction-id"]); id != "" {
			summary.DirectionIDs = append(summary.DirectionIDs, id)
			summary.DirectionAnchorIDs = append(summary.DirectionAnchorIDs, strings.TrimSpace(attrs["id"]))
		}
		if section := strings.TrimSpace(attrs["data-preview-section"]); section != "" {
			summary.Sections[section] = true
		}
		if width := strings.TrimSpace(attrs["data-width"]); width != "" {
			summary.Widths[width] = true
		}
		if tag == "button" {
			if state := strings.TrimSpace(attrs["data-state"]); state != "" {
				summary.States[state] = true
			}
		}
		for name := range attrs {
			if strings.HasPrefix(name, "on") {
				summary.InlineEventHandlers = append(summary.InlineEventHandlers, name)
			}
		}
		for _, attr := range []string{"src", "poster"} {
			if ref := strings.TrimSpace(attrs[attr]); ref != "" && !strings.HasPrefix(strings.ToLower(ref), "data:") {
				summary.ExternalDeps = append(summary.ExternalDeps, ref)
			}
		}
		if tag == "link" {
			if ref := strings.TrimSpace(attrs["href"]); ref != "" {
				summary.ExternalDeps = append(summary.ExternalDeps, ref)
			}
		}
	}
	summary.StyleText = strings.Join(extractTagBodies(content, "style", ""), "\n")
	scripts := extractTagBodies(content, "script", "")
	summary.ScriptText = strings.Join(scripts, "\n")
	summary.PreviewManifestText = firstTagBodyByID(content, "script", designPreviewManifestID)
	summary.UITargetManifest = firstTagBodyByID(content, "script", uiTargetManifestID)
	return summary
}

func parseAttrs(text string) map[string]string {
	attrs := map[string]string{}
	attrRE := regexp.MustCompile(`(?is)([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*("[^"]*"|'[^']*'|[^\s"'>]+)|\b([a-zA-Z_:][-a-zA-Z0-9_:.]*)\b`)
	for _, match := range attrRE.FindAllStringSubmatch(text, -1) {
		if match[1] != "" {
			value := strings.Trim(match[2], `"'`)
			attrs[strings.ToLower(match[1])] = value
		} else if match[3] != "" {
			attrs[strings.ToLower(match[3])] = ""
		}
	}
	return attrs
}

func hasNonDataCSSURL(styleText string) bool {
	for _, match := range cssURLReferenceRE.FindAllStringSubmatch(styleText, -1) {
		if len(match) > 1 && !strings.HasPrefix(strings.ToLower(strings.TrimSpace(match[1])), "data:") {
			return true
		}
	}
	return false
}

func extractTagBodies(content, tag, attrNeedle string) []string {
	re := regexp.MustCompile(`(?is)<` + regexp.QuoteMeta(tag) + `\b([^>]*)>(.*?)</` + regexp.QuoteMeta(tag) + `>`)
	var bodies []string
	for _, match := range re.FindAllStringSubmatch(content, -1) {
		if attrNeedle == "" || strings.Contains(match[1], attrNeedle) {
			bodies = append(bodies, match[2])
		}
	}
	return bodies
}

func firstTagBodyByID(content, tag, id string) string {
	needle1 := `id="` + id + `"`
	needle2 := `id='` + id + `'`
	for _, body := range extractTagBodies(content, tag, needle1) {
		return strings.TrimSpace(body)
	}
	for _, body := range extractTagBodies(content, tag, needle2) {
		return strings.TrimSpace(body)
	}
	return ""
}

func previewManifestDiagnostics(manifest map[string]any, directionIDs []string, ready bool) []designDiagnostic {
	var diagnostics []designDiagnostic
	if manifest["schema"] != designPreviewManifestSchema {
		addDesignDiagnostic(&diagnostics, "preview-invalid-manifest-schema", "preview manifest schema must equal "+designPreviewManifestSchema, "manifest.schema")
	}
	if ready && manifest["configured"] != true {
		addDesignDiagnostic(&diagnostics, "preview-manifest-not-configured", "ready preview manifest must set configured to true", "manifest.configured")
	}
	directions, ok := manifest["directions"].([]any)
	if !ok || len(directions) != 3 {
		addDesignDiagnostic(&diagnostics, "preview-manifest-direction-count", "preview manifest must define exactly three directions", "manifest.directions")
		return diagnostics
	}
	var manifestIDs []string
	for index, raw := range directions {
		direction, ok := raw.(map[string]any)
		if !ok {
			addDesignDiagnostic(&diagnostics, "preview-invalid-direction", "each preview manifest direction must be an object", fmt.Sprintf("manifest.directions[%d]", index))
			continue
		}
		id := strings.TrimSpace(fmt.Sprint(direction["id"]))
		manifestIDs = append(manifestIDs, id)
		if !previewDirectionIDRE.MatchString(id) {
			addDesignDiagnostic(&diagnostics, "preview-invalid-direction-id", "direction IDs must use the direction-<slug> form", fmt.Sprintf("manifest.directions[%d].id", index))
		}
		for _, field := range []string{"motion", "modes"} {
			if _, ok := direction[field].(map[string]any); !ok {
				addDesignDiagnostic(&diagnostics, "preview-incomplete-"+map[string]string{"motion": "motion-system", "modes": "color-mode"}[field], "direction "+id+" must define "+field, fmt.Sprintf("manifest.directions[%d].%s", index, field))
			}
		}
		if ready {
			for _, field := range []string{"name", "visual_thesis", "content_thesis", "interaction_thesis", "signature_element", "gain", "cost"} {
				if strings.TrimSpace(fmt.Sprint(direction[field])) == "" || fmt.Sprint(direction[field]) == "<nil>" {
					addDesignDiagnostic(&diagnostics, "preview-incomplete-direction", "ready direction "+id+" must define "+field, fmt.Sprintf("manifest.directions[%d].%s", index, field))
				}
			}
		}
	}
	if !reflect.DeepEqual(manifestIDs, directionIDs) {
		addDesignDiagnostic(&diagnostics, "preview-manifest-direction-mismatch", "preview manifest direction IDs must match the three rendered direction IDs in order", "manifest.directions")
	}
	if decisions, ok := manifest["decisions"].([]any); !ok || len(decisions) == 0 {
		addDesignDiagnostic(&diagnostics, "preview-missing-decisions", "preview manifest must define stable design decisions", "manifest.decisions")
	}
	diagnostics = append(diagnostics, previewCapabilityDiagnostics(manifest, directions, ready)...)
	diagnostics = append(diagnostics, previewHandoffDiagnostics(manifest, ready)...)
	return diagnostics
}

func previewCapabilityDiagnostics(manifest map[string]any, directions []any, ready bool) []designDiagnostic {
	var diagnostics []designDiagnostic
	model, ok := manifest["capability_model"].(map[string]any)
	if !ok {
		addDesignDiagnostic(&diagnostics, "preview-missing-capability-model", "preview manifest must define a platform capability model", "manifest.capability_model")
		return diagnostics
	}
	if strings.TrimSpace(fmt.Sprint(model["schema"])) != designCapabilityModelSchema {
		addDesignDiagnostic(&diagnostics, "preview-invalid-capability-model-schema", "capability model schema must equal "+designCapabilityModelSchema, "manifest.capability_model.schema")
	}
	registry, err := loadDesignCapabilityRegistry()
	if err != nil {
		addDesignDiagnostic(&diagnostics, "preview-capability-registry-error", err.Error(), "manifest.capability_model")
		return diagnostics
	}
	profilesByID := map[string]map[string]any{}
	for _, raw := range registry["profiles"].([]any) {
		if profile, ok := raw.(map[string]any); ok {
			profilesByID[strings.TrimSpace(fmt.Sprint(profile["id"]))] = profile
		}
	}
	profileIDs := stringList(model["profile_ids"])
	if len(profileIDs) == 0 {
		addDesignDiagnostic(&diagnostics, "preview-missing-capability-profile", "capability model must select at least one profile", "manifest.capability_model.profile_ids")
		return diagnostics
	}
	var contractProfileIDs []string
	if contracts, ok := model["profiles"].([]any); ok {
		for _, raw := range contracts {
			if contract, ok := raw.(map[string]any); ok {
				contractProfileIDs = append(contractProfileIDs, strings.TrimSpace(fmt.Sprint(contract["id"])))
			}
		}
	}
	if !reflect.DeepEqual(profileIDs, contractProfileIDs) {
		addDesignDiagnostic(&diagnostics, "preview-profile-contract-mismatch", "capability profile contracts must match profile_ids in order", "manifest.capability_model.profiles")
	}
	if stringInSlice("no-ui", profileIDs) {
		message := "no-ui work must record design_system_status not-applicable with current evidence and skip preview, approval, handoff, ui-target, and visual comparison"
		if len(profileIDs) > 1 {
			message = "no-ui cannot be combined with visual profiles"
		}
		addDesignDiagnostic(&diagnostics, "preview-nonvisual-profile", message, "manifest.capability_model.profile_ids")
		return diagnostics
	}
	var selected []map[string]any
	for _, profileID := range profileIDs {
		profile := profilesByID[profileID]
		if profile == nil {
			addDesignDiagnostic(&diagnostics, "preview-unknown-capability-profile", "unknown capability profile: "+profileID, "manifest.capability_model.profile_ids")
			continue
		}
		selected = append(selected, profile)
	}
	requiredCapabilities := map[string]bool{}
	requiredInputs := map[string]bool{}
	requiredUnits := map[string]bool{}
	for _, profile := range selected {
		for value := range listToStringSet(profile["capability_ids"]) {
			requiredCapabilities[value] = true
		}
		for value := range listToStringSet(profile["input_modes"]) {
			requiredInputs[value] = true
		}
		for value := range listToStringSet(profile["measurement_units"]) {
			requiredUnits[value] = true
		}
	}
	declaredCapabilities := listToStringSet(model["capability_ids"])
	declaredInputs := listToStringSet(model["input_modes"])
	declaredUnits := listToStringSet(model["measurement_units"])
	for _, contract := range []struct {
		code     string
		label    string
		required map[string]bool
		declared map[string]bool
		path     string
	}{
		{"preview-missing-profile-capability", "capabilities", requiredCapabilities, declaredCapabilities, "manifest.capability_model.capability_ids"},
		{"preview-missing-profile-input", "input modes", requiredInputs, declaredInputs, "manifest.capability_model.input_modes"},
		{"preview-missing-profile-unit", "measurement units", requiredUnits, declaredUnits, "manifest.capability_model.measurement_units"},
	} {
		var missing []string
		for value := range contract.required {
			if !contract.declared[value] {
				missing = append(missing, value)
			}
		}
		if len(missing) > 0 {
			sort.Strings(missing)
			addDesignDiagnostic(&diagnostics, contract.code, "selected profiles require "+contract.label+": "+strings.Join(missing, ", "), contract.path)
		}
	}
	specimens, ok := model["specimens"].([]any)
	if !ok || len(specimens) == 0 {
		addDesignDiagnostic(&diagnostics, "preview-missing-capability-specimens", "visual capability profiles require concrete specimens", "manifest.capability_model.specimens")
		return diagnostics
	}
	content, _ := manifest["content"].(map[string]any)
	var specimenIDs []string
	specimenSeen := map[string]bool{}
	specimenCapabilities := map[string]bool{}
	specimenIDsByProfile := map[string][]string{}
	specimenKindsByProfile := map[string]map[string]bool{}
	for index, raw := range specimens {
		specimen, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		specimenID := strings.TrimSpace(fmt.Sprint(specimen["id"]))
		specimenIDs = append(specimenIDs, specimenID)
		if !designSpecimenIDRE.MatchString(specimenID) {
			addDesignDiagnostic(&diagnostics, "preview-invalid-specimen-id", "specimen IDs must use stable SP-* form", fmt.Sprintf("manifest.capability_model.specimens[%d].id", index))
		}
		if specimenSeen[specimenID] {
			addDesignDiagnostic(&diagnostics, "preview-duplicate-specimen-id", "capability specimen IDs must be unique", "manifest.capability_model.specimens")
		}
		specimenSeen[specimenID] = true
		profileID := strings.TrimSpace(fmt.Sprint(specimen["profile_id"]))
		if !stringInSlice(profileID, profileIDs) {
			addDesignDiagnostic(&diagnostics, "preview-specimen-profile-mismatch", "specimen profile_id must reference a selected capability profile", fmt.Sprintf("manifest.capability_model.specimens[%d].profile_id", index))
		} else {
			specimenIDsByProfile[profileID] = append(specimenIDsByProfile[profileID], specimenID)
			if specimenKindsByProfile[profileID] == nil {
				specimenKindsByProfile[profileID] = map[string]bool{}
			}
			specimenKindsByProfile[profileID][strings.TrimSpace(fmt.Sprint(specimen["kind"]))] = true
		}
		for capability := range listToStringSet(specimen["capability_ids"]) {
			specimenCapabilities[capability] = true
			if !declaredCapabilities[capability] {
				addDesignDiagnostic(&diagnostics, "preview-unknown-specimen-capability", "specimen references undeclared capability: "+capability, fmt.Sprintf("manifest.capability_model.specimens[%d].capability_ids", index))
			}
		}
		if ready {
			var missingContent []string
			for _, key := range stringList(specimen["content_keys"]) {
				if content == nil || !nonEmpty(content[key]) {
					missingContent = append(missingContent, key)
				}
			}
			if len(missingContent) > 0 {
				addDesignDiagnostic(&diagnostics, "preview-missing-specimen-content", "ready specimen requires representative content keys: "+strings.Join(missingContent, ", "), fmt.Sprintf("manifest.capability_model.specimens[%d].content_keys", index))
			}
		}
	}
	var uncovered []string
	for capability := range declaredCapabilities {
		if !specimenCapabilities[capability] {
			uncovered = append(uncovered, capability)
		}
	}
	if len(uncovered) > 0 {
		sort.Strings(uncovered)
		addDesignDiagnostic(&diagnostics, "preview-uncovered-capability", "every declared capability must be demonstrated by a specimen: "+strings.Join(uncovered, ", "), "manifest.capability_model.specimens")
	}
	for _, profile := range selected {
		profileID := strings.TrimSpace(fmt.Sprint(profile["id"]))
		var missingKinds []string
		for _, raw := range profile["specimens"].([]any) {
			specimen, ok := raw.(map[string]any)
			if !ok {
				continue
			}
			kind := strings.TrimSpace(fmt.Sprint(specimen["kind"]))
			if !specimenKindsByProfile[profileID][kind] {
				missingKinds = append(missingKinds, kind)
			}
		}
		if len(missingKinds) > 0 {
			addDesignDiagnostic(&diagnostics, "preview-missing-profile-specimen", "profile "+profileID+" requires specimen kinds: "+strings.Join(missingKinds, ", "), "manifest.capability_model.specimens")
		}
	}
	for index, raw := range directions {
		if direction, ok := raw.(map[string]any); ok && !reflect.DeepEqual(stringList(direction["specimen_ids"]), specimenIDs) {
			addDesignDiagnostic(&diagnostics, "preview-direction-specimen-mismatch", "all directions must cover the same ordered capability specimens", fmt.Sprintf("manifest.directions[%d].specimen_ids", index))
		}
	}
	handoff, _ := manifest["handoff"].(map[string]any)
	targets, _ := handoff["responsive_matrix"].([]any)
	acceptance, _ := handoff["visual_acceptance_matrix"].([]any)
	targetProfiles := map[string]string{}
	coveredProfiles := map[string]bool{}
	for index, raw := range targets {
		target, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		targetID := strings.TrimSpace(fmt.Sprint(target["id"]))
		profileID := strings.TrimSpace(fmt.Sprint(target["profile_id"]))
		targetProfiles[targetID] = profileID
		if !stringInSlice(profileID, profileIDs) {
			addDesignDiagnostic(&diagnostics, "preview-target-profile-mismatch", "presentation target profile_id must reference a selected profile", fmt.Sprintf("manifest.handoff.responsive_matrix[%d].profile_id", index))
		} else {
			coveredProfiles[profileID] = true
		}
	}
	for _, profileID := range profileIDs {
		if !coveredProfiles[profileID] {
			addDesignDiagnostic(&diagnostics, "preview-missing-profile-target", "every selected profile requires a presentation target: "+profileID, "manifest.handoff.responsive_matrix")
		}
	}
	acceptedSpecimens := map[string]bool{}
	for index, raw := range acceptance {
		row, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		profileID := targetProfiles[strings.TrimSpace(fmt.Sprint(row["target_id"]))]
		actual := stringList(row["specimen_ids"])
		if !reflect.DeepEqual(actual, specimenIDsByProfile[profileID]) {
			addDesignDiagnostic(&diagnostics, "preview-acceptance-specimen-mismatch", "visual acceptance row must exactly bind its profile specimens", fmt.Sprintf("manifest.handoff.visual_acceptance_matrix[%d].specimen_ids", index))
		}
		for _, specimenID := range actual {
			acceptedSpecimens[specimenID] = true
		}
	}
	var missingAccepted []string
	for _, specimenID := range specimenIDs {
		if !acceptedSpecimens[specimenID] {
			missingAccepted = append(missingAccepted, specimenID)
		}
	}
	if len(missingAccepted) > 0 {
		addDesignDiagnostic(&diagnostics, "preview-incomplete-specimen-acceptance", "visual acceptance must cover every capability specimen: "+strings.Join(missingAccepted, ", "), "manifest.handoff.visual_acceptance_matrix")
	}
	return diagnostics
}

func previewHandoffDiagnostics(manifest map[string]any, ready bool) []designDiagnostic {
	var diagnostics []designDiagnostic
	knownDecisions := map[string]bool{}
	decisions, _ := manifest["decisions"].([]any)
	for index, raw := range decisions {
		decision, ok := raw.(map[string]any)
		if !ok {
			addDesignDiagnostic(&diagnostics, "preview-invalid-decision", "each decision must be an object", fmt.Sprintf("manifest.decisions[%d]", index))
			continue
		}
		id := strings.TrimSpace(fmt.Sprint(decision["id"]))
		if !canonicalDecisionIDRE.MatchString(id) {
			addDesignDiagnostic(&diagnostics, "preview-invalid-decision-id", "decision IDs must use canonical DS-* form", fmt.Sprintf("manifest.decisions[%d].id", index))
			continue
		}
		knownDecisions[id] = true
		if ready {
			for _, field := range []string{"kind", "title", "statement", "source_ref", "verification"} {
				if !nonEmpty(decision[field]) {
					addDesignDiagnostic(&diagnostics, "preview-incomplete-decision", "ready decisions must define "+field, fmt.Sprintf("manifest.decisions[%d].%s", index, field))
				}
			}
			if !isNonEmptyStringList(decision["affected_surfaces"], true) {
				addDesignDiagnostic(&diagnostics, "preview-incomplete-decision", "ready decisions must define affected_surfaces", fmt.Sprintf("manifest.decisions[%d].affected_surfaces", index))
			}
		}
	}

	seenHandoffIDs := map[string]bool{}
	validateID := func(raw any, path string) string {
		id := strings.TrimSpace(fmt.Sprint(raw))
		if !canonicalHandoffIDRE.MatchString(id) {
			addDesignDiagnostic(&diagnostics, "preview-invalid-handoff-id", "handoff IDs must use canonical DH-* form", path)
			return ""
		}
		if seenHandoffIDs[id] {
			addDesignDiagnostic(&diagnostics, "preview-duplicate-handoff-id", "handoff IDs must be unique", path)
		}
		seenHandoffIDs[id] = true
		return id
	}

	bindings, ok := manifest["token_map"].([]any)
	if !ok || len(bindings) == 0 {
		addDesignDiagnostic(&diagnostics, "preview-missing-implementation-bindings", "preview manifest must define implementation bindings", "manifest.token_map")
	}
	for index, raw := range bindings {
		binding, ok := raw.(map[string]any)
		if !ok {
			addDesignDiagnostic(&diagnostics, "preview-invalid-implementation-binding", "each implementation binding must be an object", fmt.Sprintf("manifest.token_map[%d]", index))
			continue
		}
		validateID(binding["id"], fmt.Sprintf("manifest.token_map[%d].id", index))
		decisionID := strings.TrimSpace(fmt.Sprint(binding["decision_id"]))
		if !knownDecisions[decisionID] {
			addDesignDiagnostic(&diagnostics, "preview-unknown-binding-decision", "implementation binding must reference a known DS-* decision", fmt.Sprintf("manifest.token_map[%d].decision_id", index))
		}
		if ready {
			for _, field := range []string{"source_path", "preview_token", "production_owner", "production_target", "verification"} {
				if !nonEmpty(binding[field]) {
					addDesignDiagnostic(&diagnostics, "preview-incomplete-implementation-binding", "ready implementation bindings must define "+field, fmt.Sprintf("manifest.token_map[%d].%s", index, field))
				}
			}
		}
	}

	handoff, ok := manifest["handoff"].(map[string]any)
	if !ok {
		addDesignDiagnostic(&diagnostics, "preview-missing-handoff", "preview manifest must define an implementation handoff", "manifest.handoff")
		return diagnostics
	}
	mode := strings.TrimSpace(fmt.Sprint(handoff["reproduction_mode"]))
	if mode != "exact" && mode != "platform-adapted" {
		addDesignDiagnostic(&diagnostics, "preview-invalid-reproduction-mode", "handoff reproduction_mode must be exact or platform-adapted", "manifest.handoff.reproduction_mode")
	}
	components, componentsOK := handoff["component_contracts"].([]any)
	responsive, responsiveOK := handoff["responsive_matrix"].([]any)
	acceptance, acceptanceOK := handoff["visual_acceptance_matrix"].([]any)
	if !componentsOK || len(components) == 0 {
		addDesignDiagnostic(&diagnostics, "preview-missing-component-contracts", "handoff must define component contracts", "manifest.handoff.component_contracts")
	}
	if !responsiveOK || len(responsive) == 0 {
		addDesignDiagnostic(&diagnostics, "preview-missing-responsive-matrix", "handoff must define responsive targets", "manifest.handoff.responsive_matrix")
	}
	if !acceptanceOK || len(acceptance) == 0 {
		addDesignDiagnostic(&diagnostics, "preview-missing-visual-acceptance", "handoff must define visual acceptance rows", "manifest.handoff.visual_acceptance_matrix")
	}
	tolerance, toleranceOK := handoff["comparison_tolerance"].(map[string]any)
	if !toleranceOK || len(tolerance) == 0 {
		addDesignDiagnostic(&diagnostics, "preview-missing-comparison-tolerance", "handoff must define structured comparison tolerance", "manifest.handoff.comparison_tolerance")
	} else {
		for _, field := range []string{"structure", "content", "tokens", "text_wrap"} {
			if strings.TrimSpace(fmt.Sprint(tolerance[field])) != "exact" {
				addDesignDiagnostic(&diagnostics, "preview-invalid-comparison-tolerance", "comparison tolerance "+field+" must be exact", "manifest.handoff.comparison_tolerance."+field)
			}
		}
		if strings.TrimSpace(fmt.Sprint(tolerance["platform_variance"])) != "approved-deviation-only" {
			addDesignDiagnostic(&diagnostics, "preview-invalid-comparison-tolerance", "platform variance must be approved-deviation-only", "manifest.handoff.comparison_tolerance.platform_variance")
		}
		for _, field := range []string{"geometry", "color", "motion"} {
			entry, ok := tolerance[field].(map[string]any)
			descriptor := "unit"
			if field == "color" {
				descriptor = "method"
			}
			if !ok || !nonEmpty(entry[descriptor]) || entry["max_delta"] == nil {
				addDesignDiagnostic(&diagnostics, "preview-invalid-comparison-tolerance", "comparison tolerance "+field+" must define its method/unit and max_delta", "manifest.handoff.comparison_tolerance."+field)
			}
		}
	}
	deviations, deviationsOK := handoff["accepted_deviations"].([]any)
	if !deviationsOK {
		addDesignDiagnostic(&diagnostics, "preview-invalid-accepted-deviations", "handoff accepted_deviations must be an array", "manifest.handoff.accepted_deviations")
	}

	requiredStates := map[string]bool{}
	for index, raw := range components {
		component, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		validateID(component["id"], fmt.Sprintf("manifest.handoff.component_contracts[%d].id", index))
		if ready && (!nonEmpty(component["component"]) || !isNonEmptyStringList(component["anatomy"], true) || !isNonEmptyStringList(component["required_states"], true) || !isNonEmptyStringList(component["decision_ids"], true) || !isNonEmptyStringList(component["must_match"], true)) {
			addDesignDiagnostic(&diagnostics, "preview-incomplete-component-contract", "component contracts require component, anatomy, states, decisions, and must_match", fmt.Sprintf("manifest.handoff.component_contracts[%d]", index))
		}
		for state := range listToStringSet(component["required_states"]) {
			requiredStates[state] = true
		}
		for decisionID := range listToStringSet(component["decision_ids"]) {
			if !knownDecisions[decisionID] {
				addDesignDiagnostic(&diagnostics, "preview-unknown-handoff-decision", "component contract must reference known DS-* decisions", fmt.Sprintf("manifest.handoff.component_contracts[%d].decision_ids", index))
			}
		}
	}

	responsiveIDs := map[string]bool{}
	for index, raw := range responsive {
		row, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		id := validateID(row["id"], fmt.Sprintf("manifest.handoff.responsive_matrix[%d].id", index))
		if id != "" {
			responsiveIDs[id] = true
		}
		if target, ok := row["target"].(map[string]any); !ok || !nonEmpty(target["width"]) || !nonEmpty(target["height"]) || !nonEmpty(target["unit"]) {
			addDesignDiagnostic(&diagnostics, "preview-incomplete-responsive-target", "responsive targets require width, height, and unit", fmt.Sprintf("manifest.handoff.responsive_matrix[%d].target", index))
		}
		if ready && (!nonEmpty(row["profile_id"]) || !nonEmpty(row["review_width_px"]) || !nonEmpty(row["label"]) || !nonEmpty(row["state"]) || !nonEmpty(row["adaptation"]) || !isNonEmptyStringList(row["decision_ids"], true)) {
			addDesignDiagnostic(&diagnostics, "preview-incomplete-responsive-contract", "responsive contracts require profile, review width, label, state, adaptation, and decisions", fmt.Sprintf("manifest.handoff.responsive_matrix[%d]", index))
		}
		for decisionID := range listToStringSet(row["decision_ids"]) {
			if !knownDecisions[decisionID] {
				addDesignDiagnostic(&diagnostics, "preview-unknown-handoff-decision", "responsive contract must reference known DS-* decisions", fmt.Sprintf("manifest.handoff.responsive_matrix[%d].decision_ids", index))
			}
		}
	}

	requiredEvidence := map[string]bool{
		"structure_snapshot": true, "visual_capture": true,
		"runtime_diagnostics": true, "visual_comparison_or_human_review": true,
	}
	coveredTargets := map[string]bool{}
	coveredStates := map[string]bool{}
	coveredDecisions := map[string]bool{}
	for index, raw := range acceptance {
		row, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		validateID(row["id"], fmt.Sprintf("manifest.handoff.visual_acceptance_matrix[%d].id", index))
		targetID := strings.TrimSpace(fmt.Sprint(row["target_id"]))
		if !responsiveIDs[targetID] {
			addDesignDiagnostic(&diagnostics, "preview-unknown-acceptance-target", "visual acceptance must reference a responsive target", fmt.Sprintf("manifest.handoff.visual_acceptance_matrix[%d].target_id", index))
		}
		coveredTargets[targetID] = true
		for state := range listToStringSet(row["states"]) {
			coveredStates[state] = true
		}
		if ready && (!isNonEmptyStringList(row["specimen_ids"], true) || !isNonEmptyStringList(row["states"], true) || !isNonEmptyStringList(row["color_modes"], true) || !isNonEmptyStringList(row["motion_modes"], true) || !isNonEmptyStringList(row["decision_ids"], true) || !isNonEmptyStringList(row["must_match"], true)) {
			addDesignDiagnostic(&diagnostics, "preview-incomplete-visual-acceptance", "visual acceptance rows require specimens, states, color/motion modes, decisions, and must_match", fmt.Sprintf("manifest.handoff.visual_acceptance_matrix[%d]", index))
		}
		for decisionID := range listToStringSet(row["decision_ids"]) {
			coveredDecisions[decisionID] = true
			if !knownDecisions[decisionID] {
				addDesignDiagnostic(&diagnostics, "preview-unknown-handoff-decision", "visual acceptance must reference known DS-* decisions", fmt.Sprintf("manifest.handoff.visual_acceptance_matrix[%d].decision_ids", index))
			}
		}
		if !stringSetEqual(listToStringSet(row["evidence"]), requiredEvidence) {
			addDesignDiagnostic(&diagnostics, "preview-incomplete-handoff-evidence", "each visual acceptance row must require structure, visual, runtime, and comparison evidence", fmt.Sprintf("manifest.handoff.visual_acceptance_matrix[%d].evidence", index))
		}
	}
	for index, raw := range deviations {
		deviation, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		validateID(deviation["id"], fmt.Sprintf("manifest.handoff.accepted_deviations[%d].id", index))
		decisionID := strings.TrimSpace(fmt.Sprint(deviation["decision_id"]))
		if !knownDecisions[decisionID] {
			addDesignDiagnostic(&diagnostics, "preview-unknown-handoff-decision", "accepted deviation must reference a known DS-* decision", fmt.Sprintf("manifest.handoff.accepted_deviations[%d].decision_id", index))
		}
		if ready && (!nonEmpty(deviation["reason"]) || !nonEmpty(deviation["approval_ref"])) {
			addDesignDiagnostic(&diagnostics, "preview-incomplete-accepted-deviation", "accepted deviations require reason and approval_ref", fmt.Sprintf("manifest.handoff.accepted_deviations[%d]", index))
		}
	}
	if !stringSetEqual(coveredTargets, responsiveIDs) {
		addDesignDiagnostic(&diagnostics, "preview-incomplete-responsive-coverage", "visual acceptance rows must exactly cover responsive targets", "manifest.handoff.visual_acceptance_matrix")
	}
	if !stringSetContainsAll(coveredStates, sortedBoolKeys(requiredStates)) {
		addDesignDiagnostic(&diagnostics, "preview-incomplete-state-coverage", "visual acceptance rows must cover every required component state", "manifest.handoff.visual_acceptance_matrix")
	}
	if !stringSetContainsAll(coveredDecisions, sortedBoolKeys(knownDecisions)) {
		addDesignDiagnostic(&diagnostics, "preview-incomplete-decision-coverage", "visual acceptance rows must cover every design decision", "manifest.handoff.visual_acceptance_matrix")
	}
	return diagnostics
}

func validatePreviewApprovalSidecar(path, content, approvedDirection string, manifest map[string]any) []designDiagnostic {
	var diagnostics []designDiagnostic
	sidecar := strings.TrimSuffix(path, filepath.Ext(path)) + ".approval.json"
	raw, err := os.ReadFile(sidecar)
	if err != nil {
		addDesignDiagnostic(&diagnostics, "preview-missing-approval-sidecar", "approved preview requires "+filepath.Base(sidecar), sidecar)
		return diagnostics
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		addDesignDiagnostic(&diagnostics, "preview-invalid-approval-sidecar", "cannot read approval sidecar: "+err.Error(), sidecar)
		return diagnostics
	}
	expected := map[string]any{
		"schema":          designPreviewApprovalSchema,
		"preview_file":    filepath.Base(path),
		"direction_id":    approvedDirection,
		"preview_ref":     filepath.Base(path) + "#" + approvedDirection,
		"html_sha256":     sha256String(content),
		"manifest_sha256": canonicalJSONSHA256(manifest),
		"handoff_file":    filepath.Base(strings.TrimSuffix(path, filepath.Ext(path)) + ".handoff.json"),
		"handoff_ref":     filepath.Base(strings.TrimSuffix(path, filepath.Ext(path)) + ".handoff.json"),
	}
	for key, value := range expected {
		if strings.TrimSpace(fmt.Sprint(payload[key])) != strings.TrimSpace(fmt.Sprint(value)) {
			addDesignDiagnostic(&diagnostics, "preview-stale-approval-sidecar", "approval sidecar "+key+" does not bind the current approved preview", filepath.Base(sidecar)+"."+key)
		}
	}
	if !isNonEmptyStringList(payload["decision_ids"], true) {
		addDesignDiagnostic(&diagnostics, "preview-invalid-approval-decisions", "approval sidecar decision_ids must be a list of stable non-empty IDs", filepath.Base(sidecar)+".decision_ids")
	}
	if !hexDigestRE.MatchString(strings.TrimSpace(fmt.Sprint(payload["handoff_sha256"]))) {
		addDesignDiagnostic(&diagnostics, "preview-invalid-handoff-digest", "approval sidecar handoff_sha256 must be a SHA-256 digest", filepath.Base(sidecar)+".handoff_sha256")
	}
	if !stringSetEqual(listToStringSet(payload["handoff_contract_ids"]), stringSliceSet(manifestHandoffContractIDs(manifest))) {
		addDesignDiagnostic(&diagnostics, "preview-stale-handoff-binding", "approval sidecar handoff_contract_ids do not bind the immutable handoff", filepath.Base(sidecar)+".handoff_contract_ids")
	}
	if !reflect.DeepEqual(stringList(payload["capability_profile_ids"]), manifestCapabilityProfileIDs(manifest)) {
		addDesignDiagnostic(&diagnostics, "preview-stale-handoff-binding", "approval sidecar capability_profile_ids do not bind the immutable handoff", filepath.Base(sidecar)+".capability_profile_ids")
	}
	if !reflect.DeepEqual(stringList(payload["specimen_ids"]), manifestSpecimenIDs(manifest)) {
		addDesignDiagnostic(&diagnostics, "preview-stale-handoff-binding", "approval sidecar specimen_ids do not bind the immutable handoff", filepath.Base(sidecar)+".specimen_ids")
	}
	diagnostics = append(diagnostics, validatePreviewHandoffSidecar(path, content, approvedDirection, manifest, payload)...)
	return diagnostics
}

func validatePreviewHandoffSidecar(path, content, approvedDirection string, manifest, approvalPayload map[string]any) []designDiagnostic {
	var diagnostics []designDiagnostic
	handoffPath := strings.TrimSuffix(path, filepath.Ext(path)) + ".handoff.json"
	raw, err := os.ReadFile(handoffPath)
	if err != nil {
		addDesignDiagnostic(&diagnostics, "preview-missing-handoff-sidecar", "approved preview requires "+filepath.Base(handoffPath), handoffPath)
		return diagnostics
	}
	var handoff map[string]any
	if err := json.Unmarshal(raw, &handoff); err != nil {
		addDesignDiagnostic(&diagnostics, "preview-invalid-handoff-sidecar", "cannot read handoff sidecar: "+err.Error(), handoffPath)
		return diagnostics
	}
	if handoff["schema"] != designHandoffSchema {
		addDesignDiagnostic(&diagnostics, "preview-invalid-handoff-schema", "handoff schema must equal "+designHandoffSchema, filepath.Base(handoffPath)+".schema")
	}
	actualDigest := sha256String(string(raw))
	if strings.TrimSpace(fmt.Sprint(approvalPayload["handoff_sha256"])) != actualDigest {
		addDesignDiagnostic(&diagnostics, "preview-stale-handoff-binding", "approval sidecar handoff_sha256 does not bind the immutable handoff", filepath.Base(handoffPath))
	}
	expected, buildErr := buildDesignHandoffPayload(path, content, approvedDirection, manifest)
	if buildErr != nil {
		addDesignDiagnostic(&diagnostics, "preview-invalid-handoff-sidecar", buildErr.Error(), handoffPath)
		return diagnostics
	}
	if canonicalJSONSHA256(handoff) != canonicalJSONSHA256(expected) {
		addDesignDiagnostic(&diagnostics, "preview-stale-handoff-content", "handoff sidecar must exactly match the approved direction and manifest", handoffPath)
	}
	reproduction, _ := handoff["reproduction"].(map[string]any)
	ids := listToStringSet(reproduction["contract_ids"])
	if len(ids) == 0 || !stringSetEqual(ids, stringSliceSet(manifestHandoffContractIDs(manifest))) {
		addDesignDiagnostic(&diagnostics, "preview-invalid-handoff-contract-ids", "handoff contract_ids must exactly match the approved DH-* set", filepath.Base(handoffPath)+".reproduction.contract_ids")
	}
	return diagnostics
}

func validateUITargetReadyManifest(manifest map[string]any, diagnostics *[]designDiagnostic) {
	if feature, ok := manifest["feature"].(map[string]any); !ok {
		addDesignDiagnostic(diagnostics, "ui-target-incomplete-feature", "ready UI target must define feature name, short name, title, and job", "manifest.feature")
	} else {
		for _, field := range []string{"name", "short_name", "title", "job"} {
			if strings.TrimSpace(fmt.Sprint(feature[field])) == "" || fmt.Sprint(feature[field]) == "<nil>" {
				addDesignDiagnostic(diagnostics, "ui-target-incomplete-feature", "ready UI target must define feature name, short name, title, and job", "manifest.feature")
				break
			}
		}
	}
	approval, ok := manifest["approval"].(map[string]any)
	if !ok {
		addDesignDiagnostic(diagnostics, "ui-target-missing-approval", "ready UI target must bind its approved design source", "manifest.approval")
	} else {
		ref := strings.TrimSpace(fmt.Sprint(approval["ref"]))
		direction := strings.TrimSpace(fmt.Sprint(approval["direction_id"]))
		if ref == "" || ref == "<nil>" || direction == "" || direction == "<nil>" {
			addDesignDiagnostic(diagnostics, "ui-target-incomplete-approval", "ready UI target approval requires ref and direction_id", "manifest.approval")
		}
		if regexp.MustCompile(`(?i)round-\d+\.html#direction-[a-z0-9-]+$`).MatchString(ref) {
			for _, field := range []string{"preview_sha256", "manifest_sha256", "handoff_sha256"} {
				if !hexDigestRE.MatchString(strings.TrimSpace(fmt.Sprint(approval[field]))) {
					addDesignDiagnostic(diagnostics, "ui-target-invalid-approval-digest", "approved HTML preview requires a valid "+field, "manifest.approval."+field)
				}
			}
			handoffRef := strings.TrimSpace(fmt.Sprint(approval["handoff_ref"]))
			if !strings.HasSuffix(strings.ToLower(handoffRef), ".handoff.json") {
				addDesignDiagnostic(diagnostics, "ui-target-invalid-handoff-reference", "approved HTML preview requires an immutable handoff_ref", "manifest.approval.handoff_ref")
			}
		}
	}
	if content, ok := manifest["content"].(map[string]any); !ok || len(content) == 0 {
		addDesignDiagnostic(diagnostics, "ui-target-incomplete-content", "ready UI target content must be representative and non-empty", "manifest.content")
	} else {
		for _, value := range content {
			if strings.TrimSpace(fmt.Sprint(value)) == "" || fmt.Sprint(value) == "<nil>" {
				addDesignDiagnostic(diagnostics, "ui-target-incomplete-content", "ready UI target content must be representative and non-empty", "manifest.content")
				break
			}
		}
	}
	ids, ok := manifest["decision_ids"].([]any)
	if !ok || len(ids) == 0 {
		addDesignDiagnostic(diagnostics, "ui-target-invalid-decisions", "ready UI target must carry canonical DS-* decision IDs", "manifest.decision_ids")
		return
	}
	for _, raw := range ids {
		id, ok := raw.(string)
		if !ok || !uiCanonicalDecisionIDRE.MatchString(strings.TrimSpace(id)) {
			addDesignDiagnostic(diagnostics, "ui-target-invalid-decisions", "ready UI target must carry canonical DS-* decision IDs", "manifest.decision_ids")
			return
		}
	}
	handoffIDs, ok := manifest["handoff_contract_ids"].([]any)
	if !ok || len(handoffIDs) == 0 {
		addDesignDiagnostic(diagnostics, "ui-target-invalid-handoff-contracts", "ready UI target must carry canonical DH-* handoff contract IDs", "manifest.handoff_contract_ids")
		return
	}
	for _, raw := range handoffIDs {
		id, ok := raw.(string)
		if !ok || !canonicalHandoffIDRE.MatchString(strings.TrimSpace(id)) {
			addDesignDiagnostic(diagnostics, "ui-target-invalid-handoff-contracts", "ready UI target must carry canonical DH-* handoff contract IDs", "manifest.handoff_contract_ids")
			return
		}
	}
}

func toTailwindTheme(ds map[string]any) map[string]any {
	extend := map[string]any{}
	tokenMap, _ := ds["tokens"].(map[string]any)
	categoryMap := map[string]string{
		"color":      "colors",
		"spacing":    "spacing",
		"radius":     "borderRadius",
		"typography": "fontFamily",
		"motion":     "transitionDuration",
	}
	for category, target := range categoryMap {
		entries, _ := tokenMap[category].(map[string]any)
		if len(entries) == 0 {
			continue
		}
		bucket := map[string]any{}
		for name, raw := range entries {
			token, _ := raw.(map[string]any)
			key := strings.ReplaceAll(name, ".", "-")
			value := token["value"]
			if category == "motion" && strings.HasPrefix(name, "easing.") {
				continue
			}
			bucket[key] = value
		}
		extend[target] = bucket
	}
	if entries, _ := tokenMap["motion"].(map[string]any); len(entries) > 0 {
		timing := map[string]any{}
		for name, raw := range entries {
			if !strings.HasPrefix(name, "easing.") {
				continue
			}
			token, _ := raw.(map[string]any)
			timing[strings.ReplaceAll(name, ".", "-")] = token["value"]
		}
		extend["transitionTimingFunction"] = timing
	}
	return map[string]any{"theme": map[string]any{"extend": extend}}
}

func locateTemplate(name string) (string, error) {
	candidates := []string{}
	if cwd, err := os.Getwd(); err == nil {
		candidates = append(candidates,
			filepath.Join(cwd, ".specify", "templates", name),
			filepath.Join(cwd, "templates", name),
		)
	}
	if executable, err := os.Executable(); err == nil {
		candidates = append(candidates, filepath.Join(filepath.Dir(executable), "..", "templates", name))
	}
	if _, file, _, ok := runtime.Caller(0); ok {
		root := filepath.Clean(filepath.Join(filepath.Dir(file), "..", ".."))
		candidates = append(candidates, filepath.Join(root, "templates", name))
	}
	for _, candidate := range candidates {
		if info, err := os.Stat(candidate); err == nil && info.Mode().IsRegular() {
			return candidate, nil
		}
	}
	return "", fmt.Errorf("design template does not exist: %s", name)
}

func designReferenceContent(source, notes string) string {
	notes = strings.TrimSpace(notes)
	if notes == "" {
		notes = "No notes supplied."
	}
	return "# Design References\n\n" +
		"This file is input for `sp-design`. It is not the project design system.\n\n" +
		"## Imported Reference\n\n" +
		"- Source: " + strings.TrimSpace(source) + "\n" +
		"- Notes: " + notes + "\n\n" +
		"## Synthesis Instructions\n\n" +
		"- Extract reusable design principles.\n" +
		"- Remove brand-specific expression.\n" +
		"- Write original project guidance into `DESIGN.md` only after user approval in `sp-design`.\n"
}

func designContainedPath(path string, allowMissing bool) (string, Envelope, bool) {
	root, err := os.Getwd()
	if err != nil {
		return "", NewEnvelope("error", "resolve project root: "+err.Error()), false
	}
	target, err := resolveProjectContainedPath(root, path)
	if err != nil {
		env := NewEnvelope("usage-error", "design path is invalid")
		env.Blockers = append(env.Blockers, err.Error())
		return "", env, false
	}
	if !allowMissing {
		if info, err := os.Stat(target); err == nil && !info.Mode().IsRegular() {
			env := NewEnvelope("blocked", "design path is not a file")
			env.Blockers = append(env.Blockers, target+" is not a file")
			return "", env, false
		}
	}
	return target, Envelope{}, true
}

func writeDesignDiagnostics(stdout io.Writer, diagnostics []designDiagnostic, okSummary string) int {
	env := NewEnvelope("ok", okSummary)
	env.Data["ok"] = true
	env.Data["diagnostics"] = diagnostics
	for _, diagnostic := range diagnostics {
		env.Items = append(env.Items, map[string]any{"code": diagnostic.Code, "message": diagnostic.Message, "path": diagnostic.Path, "level": diagnostic.Level})
	}
	if len(diagnostics) > 0 {
		env.Status = "invalid"
		env.Summary = "design validation failed"
		env.Data["ok"] = false
	}
	return writeEnvelope(stdout, env)
}

func writeDesignError(stdout io.Writer, status, message string) int {
	env := NewEnvelope(status, message)
	env.Blockers = append(env.Blockers, message)
	return writeEnvelope(stdout, env)
}

func supportedDesignLintLevel(level string) bool {
	return level == "structural" || level == "ready"
}

func firstPositional(args []string, fallback string) string {
	skipNext := false
	valueFlags := map[string]bool{
		"--format": true, "--level": true, "--out": true, "--out-dir": true,
		"--notes": true, "--direction": true, "--manifest": true,
	}
	for _, arg := range args {
		if skipNext {
			skipNext = false
			continue
		}
		if valueFlags[arg] {
			skipNext = true
			continue
		}
		if !strings.HasPrefix(arg, "-") {
			return arg
		}
	}
	return fallback
}

func addDesignDiagnostic(diagnostics *[]designDiagnostic, code, message, path string) {
	*diagnostics = append(*diagnostics, designDiagnostic{Code: code, Message: message, Path: path, Level: "error"})
}

func joinDiagnostics(diagnostics []designDiagnostic) string {
	parts := make([]string, 0, len(diagnostics))
	for _, diagnostic := range diagnostics {
		parts = append(parts, diagnostic.Code+": "+diagnostic.Message)
	}
	return strings.Join(parts, "; ")
}

func parseJSONObject(text string) (map[string]any, error) {
	if strings.TrimSpace(text) == "" {
		return nil, fmt.Errorf("embedded manifest is not valid JSON: empty")
	}
	var payload map[string]any
	if err := json.Unmarshal([]byte(text), &payload); err != nil {
		return nil, fmt.Errorf("embedded manifest is not valid JSON: %v", err)
	}
	return payload, nil
}

func replaceEmbeddedJSON(content, id string, payload map[string]any) (string, error) {
	rendered, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return "", err
	}
	re := regexp.MustCompile(`(?is)<script\b([^>]*)>(.*?)</script>`)
	matches := re.FindAllStringSubmatchIndex(content, -1)
	var builder strings.Builder
	last := 0
	count := 0
	for _, match := range matches {
		attrs := content[match[2]:match[3]]
		if !strings.Contains(attrs, `id="`+id+`"`) && !strings.Contains(attrs, `id='`+id+`'`) {
			continue
		}
		count++
		builder.WriteString(content[last:match[0]])
		openEnd := strings.Index(content[match[0]:match[1]], ">")
		if openEnd < 0 {
			return "", fmt.Errorf("design preview manifest script is malformed")
		}
		openTagEnd := match[0] + openEnd + 1
		builder.WriteString(content[match[0]:openTagEnd])
		builder.WriteString("\n")
		builder.Write(rendered)
		builder.WriteString("\n  </script>")
		last = match[1]
	}
	if count != 1 {
		return "", fmt.Errorf("design preview must contain exactly one %s", id)
	}
	builder.WriteString(content[last:])
	return builder.String(), nil
}

func replaceHTMLAttribute(content, name, value string) (string, error) {
	re := regexp.MustCompile(`(` + regexp.QuoteMeta(name) + `\s*=\s*")[^"]*(")`)
	if !re.MatchString(content) {
		return "", fmt.Errorf("design preview is missing required attribute %s", name)
	}
	updated := re.ReplaceAllString(content, "${1}"+value+"${2}")
	return updated, nil
}

func previewRoundFromPath(path string) string {
	match := regexp.MustCompile(`(?i)^round-(\d+)$`).FindStringSubmatch(strings.TrimSuffix(filepath.Base(path), filepath.Ext(path)))
	if match == nil {
		return ""
	}
	number, err := strconv.Atoi(match[1])
	if err != nil {
		return ""
	}
	return strconv.Itoa(number)
}

func manifestDecisionIDs(manifest map[string]any) []string {
	decisions, _ := manifest["decisions"].([]any)
	var ids []string
	for _, raw := range decisions {
		decision, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		id := strings.TrimSpace(fmt.Sprint(decision["id"]))
		if id != "" && id != "<nil>" {
			ids = append(ids, id)
		}
	}
	return ids
}

func manifestDirectionIDs(manifest map[string]any) []string {
	directions, _ := manifest["directions"].([]any)
	ids := make([]string, 0, len(directions))
	for _, raw := range directions {
		direction, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		ids = append(ids, strings.TrimSpace(fmt.Sprint(direction["id"])))
	}
	return ids
}

func manifestHandoffContractIDs(manifest map[string]any) []string {
	handoff, _ := manifest["handoff"].(map[string]any)
	collections := []any{
		manifest["token_map"],
		handoff["component_contracts"],
		handoff["responsive_matrix"],
		handoff["visual_acceptance_matrix"],
		handoff["accepted_deviations"],
	}
	var ids []string
	for _, collection := range collections {
		rows, _ := collection.([]any)
		for _, raw := range rows {
			row, ok := raw.(map[string]any)
			if !ok {
				continue
			}
			id := strings.TrimSpace(fmt.Sprint(row["id"]))
			if id != "" && id != "<nil>" {
				ids = append(ids, id)
			}
		}
	}
	return ids
}

func manifestCapabilityProfileIDs(manifest map[string]any) []string {
	model, _ := manifest["capability_model"].(map[string]any)
	return stringList(model["profile_ids"])
}

func manifestSpecimenIDs(manifest map[string]any) []string {
	model, _ := manifest["capability_model"].(map[string]any)
	specimens, _ := model["specimens"].([]any)
	var ids []string
	for _, raw := range specimens {
		specimen, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		id := strings.TrimSpace(fmt.Sprint(specimen["id"]))
		if id != "" && id != "<nil>" {
			ids = append(ids, id)
		}
	}
	return ids
}

func buildDesignHandoffPayload(path, content, directionID string, manifest map[string]any) (map[string]any, error) {
	var selected map[string]any
	for _, raw := range manifest["directions"].([]any) {
		direction, ok := raw.(map[string]any)
		if ok && strings.TrimSpace(fmt.Sprint(direction["id"])) == directionID {
			selected = cloneJSONMap(direction)
			break
		}
	}
	if selected == nil {
		return nil, fmt.Errorf("cannot build handoff for missing approved direction %s", directionID)
	}
	handoff, ok := manifest["handoff"].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("design preview manifest has no handoff contract")
	}
	reproduction := cloneJSONMap(handoff)
	reproduction["capability_model"] = cloneJSONValue(manifest["capability_model"])
	responsiveByID := map[string]map[string]any{}
	responsive, _ := reproduction["responsive_matrix"].([]any)
	for _, raw := range responsive {
		row, ok := raw.(map[string]any)
		if ok {
			responsiveByID[strings.TrimSpace(fmt.Sprint(row["id"]))] = row
		}
	}
	acceptance, _ := reproduction["visual_acceptance_matrix"].([]any)
	resolvedAcceptance := make([]any, 0, len(acceptance))
	for _, raw := range acceptance {
		row, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		resolved := cloneJSONMap(row)
		responsiveRow := responsiveByID[strings.TrimSpace(fmt.Sprint(row["target_id"]))]
		var targets []any
		for _, colorMode := range stringList(row["color_modes"]) {
			for _, motionMode := range stringList(row["motion_modes"]) {
				query := "mode=" + url.QueryEscape(colorMode) + "&motion=" + url.QueryEscape(motionMode) + "&capture=1"
				if profileID := strings.TrimSpace(fmt.Sprint(responsiveRow["profile_id"])); profileID != "" && profileID != "<nil>" {
					query += "&profile=" + url.QueryEscape(profileID)
				}
				if targetID := strings.TrimSpace(fmt.Sprint(responsiveRow["id"])); targetID != "" && targetID != "<nil>" {
					query += "&target=" + url.QueryEscape(targetID)
				}
				if responsiveRow["review_width_px"] != nil {
					query += "&viewport=" + url.QueryEscape(jsonNumberString(responsiveRow["review_width_px"]))
				}
				targets = append(targets, map[string]any{
					"ref":         filepath.Base(path) + "?" + query + "#" + directionID,
					"color_mode":  colorMode,
					"motion_mode": motionMode,
				})
			}
		}
		resolved["approved_targets"] = targets
		resolvedAcceptance = append(resolvedAcceptance, resolved)
	}
	reproduction["visual_acceptance_matrix"] = resolvedAcceptance
	reproduction["contract_ids"] = manifestHandoffContractIDs(manifest)
	review, _ := manifest["review"].(map[string]any)
	return map[string]any{
		"schema": designHandoffSchema,
		"approval": map[string]any{
			"preview_file":    filepath.Base(path),
			"preview_ref":     filepath.Base(path) + "#" + directionID,
			"direction_id":    directionID,
			"review_round":    strings.TrimSpace(fmt.Sprint(review["round"])),
			"preview_sha256":  sha256String(content),
			"manifest_sha256": canonicalJSONSHA256(manifest),
			"decision_ids":    manifestDecisionIDs(manifest),
		},
		"project":                 cloneJSONValue(manifest["project"]),
		"direction":               selected,
		"content":                 cloneJSONValue(manifest["content"]),
		"boundaries":              cloneJSONValue(manifest["boundaries"]),
		"decisions":               cloneJSONValue(manifest["decisions"]),
		"implementation_bindings": cloneJSONValue(manifest["token_map"]),
		"reproduction":            reproduction,
	}, nil
}

func cloneJSONValue(value any) any {
	raw, _ := json.Marshal(value)
	var cloned any
	_ = json.Unmarshal(raw, &cloned)
	return cloned
}

func cloneJSONMap(value map[string]any) map[string]any {
	cloned, _ := cloneJSONValue(value).(map[string]any)
	return cloned
}

func jsonNumberString(value any) string {
	switch typed := value.(type) {
	case float64:
		return strconv.FormatFloat(typed, 'f', -1, 64)
	case json.Number:
		return typed.String()
	default:
		return strings.TrimSpace(fmt.Sprint(value))
	}
}

func canonicalJSONSHA256(payload any) string {
	raw, _ := json.Marshal(payload)
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}

func sha256String(content string) string {
	sum := sha256.Sum256([]byte(content))
	return hex.EncodeToString(sum[:])
}

func marshalPretty(payload any) (string, error) {
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return "", err
	}
	return string(raw) + "\n", nil
}

func writeTextAtomic(path, content string) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	tmp, err := os.CreateTemp(filepath.Dir(path), "."+filepath.Base(path)+".*.tmp")
	if err != nil {
		return err
	}
	tmpName := tmp.Name()
	if _, err := tmp.WriteString(content); err != nil {
		_ = tmp.Close()
		_ = os.Remove(tmpName)
		return err
	}
	if err := tmp.Close(); err != nil {
		_ = os.Remove(tmpName)
		return err
	}
	if err := replaceFile(tmpName, path); err != nil {
		_ = os.Remove(tmpName)
		return err
	}
	return nil
}

func stringInSlice(value string, list []string) bool {
	for _, item := range list {
		if item == value {
			return true
		}
	}
	return false
}

func hasDuplicates(list []string) bool {
	seen := map[string]bool{}
	for _, item := range list {
		if seen[item] {
			return true
		}
		seen[item] = true
	}
	return false
}

func nonEmpty(value any) bool {
	if value == nil {
		return false
	}
	return strings.TrimSpace(fmt.Sprint(value)) != ""
}

func isNonEmptyStringList(value any, requireNonEmpty bool) bool {
	list, ok := value.([]any)
	if !ok || (requireNonEmpty && len(list) == 0) {
		return false
	}
	for _, raw := range list {
		text, ok := raw.(string)
		if !ok || strings.TrimSpace(text) == "" {
			return false
		}
	}
	return true
}

func stringList(value any) []string {
	var result []string
	switch list := value.(type) {
	case []any:
		result = make([]string, 0, len(list))
		for _, raw := range list {
			text, ok := raw.(string)
			if ok && strings.TrimSpace(text) != "" {
				result = append(result, strings.TrimSpace(text))
			}
		}
	case []string:
		result = make([]string, 0, len(list))
		for _, text := range list {
			if strings.TrimSpace(text) != "" {
				result = append(result, strings.TrimSpace(text))
			}
		}
	}
	return result
}

func stringSliceSet(values []string) map[string]bool {
	result := map[string]bool{}
	for _, value := range values {
		if strings.TrimSpace(value) != "" {
			result[strings.TrimSpace(value)] = true
		}
	}
	return result
}

func listToStringSet(value any) map[string]bool {
	result := map[string]bool{}
	list, ok := value.([]any)
	if !ok {
		return result
	}
	for _, raw := range list {
		switch typed := raw.(type) {
		case string:
			if strings.TrimSpace(typed) != "" {
				result[strings.TrimSpace(typed)] = true
			}
		case float64:
			result[strconv.Itoa(int(typed))] = true
		}
	}
	return result
}

func stringSetEqual(left, right map[string]bool) bool {
	if len(left) != len(right) {
		return false
	}
	for key := range left {
		if !right[key] {
			return false
		}
	}
	return true
}

func stringSetContainsAll(set map[string]bool, values []string) bool {
	for _, value := range values {
		if !set[value] {
			return false
		}
	}
	return true
}

func sortedKeys(m map[string]any) []string {
	keys := make([]string, 0, len(m))
	for key := range m {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}

func sortedBoolKeys(m map[string]bool) []string {
	keys := make([]string, 0, len(m))
	for key := range m {
		keys = append(keys, key)
	}
	sort.Strings(keys)
	return keys
}
