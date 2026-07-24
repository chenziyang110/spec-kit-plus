package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
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
	designPreviewSchema         = "spec-kit-design-preview-v1"
	designPreviewManifestSchema = "spec-kit-design-preview-manifest-v1"
	designPreviewApprovalSchema = "spec-kit-design-preview-approval-v1"
	designPreviewManifestID     = "design-preview-manifest"
	uiTargetSchema              = "spec-kit-ui-target-v1"
	uiTargetManifestSchema      = "spec-kit-ui-target-manifest-v1"
	uiTargetManifestID          = "ui-target-manifest"
)

var (
	frontMatterRE           = regexp.MustCompile(`(?s)\A---\s*\r?\n(.*?)\r?\n---\s*\r?\n?(.*)\z`)
	tokenNameRE             = regexp.MustCompile(`^[a-z][a-z0-9]*(?:\.[a-z0-9]+)*$`)
	tokenRefRE              = regexp.MustCompile(`^\{([a-z][a-z0-9]*)\.([a-z][a-z0-9]*(?:\.[a-z0-9]+)*)\}$`)
	headingRECache          = map[string]*regexp.Regexp{}
	previewDirectionIDRE    = regexp.MustCompile(`^direction-[a-z0-9][a-z0-9-]*$`)
	previewPlaceholderRE    = regexp.MustCompile(`__[A-Z0-9_]+__`)
	remoteReferenceRE       = regexp.MustCompile(`(?i)(?:https?:)?//|@import\b`)
	cssURLReferenceRE       = regexp.MustCompile(`(?is)url\s*\(\s*["']?([^"')\s]+)`)
	networkRuntimeRE        = regexp.MustCompile(`(?i)\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(`)
	uiPersistenceRuntimeRE  = regexp.MustCompile(`(?i)\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(|\b(?:localStorage|sessionStorage|indexedDB|document\.cookie)\b`)
	hexDigestRE             = regexp.MustCompile(`^[0-9a-f]{64}$`)
	canonicalDecisionIDRE   = regexp.MustCompile(`^DS-[A-Z0-9]+(?:-[A-Z0-9]+)+$`)
	uiCanonicalDecisionIDRE = regexp.MustCompile(`^DS-[A-Z]+-\d{3}$`)
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
	case "preview-lint":
		return runDesignPreviewLint(args[1:], stdout)
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
	written, err := scaffoldDesignPreview(target, hasFlag(args, "--force"))
	if err != nil {
		return writeDesignError(stdout, "blocked", err.Error())
	}
	env = NewEnvelope("ok", "design preview scaffold written")
	env.Data["path"] = written
	env.NextArgv = []string{"specify-runtime", "design", "preview-lint", written, "--level", "ready"}
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
	keys := []string{"schema", "name", "version", "status", "approval", "product_context", "direction_contract", "platforms", "tokens", "color_modes", "components", "responsive", "content", "decisions", "verification", "accessibility"}
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
	payload := map[string]any{
		"schema":          designPreviewApprovalSchema,
		"preview_file":    filepath.Base(path),
		"direction_id":    directionID,
		"preview_ref":     filepath.Base(path) + "#" + directionID,
		"review_round":    strings.TrimSpace(fmt.Sprint(review["round"])),
		"html_sha256":     sha256String(updated),
		"manifest_sha256": canonicalJSONSHA256(manifest),
		"decision_ids":    decisionIDs,
	}
	if err := writeTextAtomic(path, updated); err != nil {
		return nil, err
	}
	sidecar := strings.TrimSuffix(path, filepath.Ext(path)) + ".approval.json"
	if err := writeJSONAtomic(sidecar, payload); err != nil {
		return nil, err
	}
	if diagnostics := lintDesignPreviewFile(path, "ready"); len(diagnostics) > 0 {
		return nil, fmt.Errorf("approved design preview failed deterministic validation: %s", joinDiagnostics(diagnostics))
	}
	return payload, nil
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
		for _, field := range []string{"preview_sha256", "manifest_sha256"} {
			if !hexDigestRE.MatchString(strings.TrimSpace(fmt.Sprint(approval[field]))) {
				addDesignDiagnostic(diagnostics, "missing-approved-preview-digest", "design_system.approval."+field+" must be a SHA-256 digest", "design_system.approval."+field)
			}
		}
		if strings.TrimSpace(fmt.Sprint(approval["review_round"])) == "" || fmt.Sprint(approval["review_round"]) == "<nil>" {
			addDesignDiagnostic(diagnostics, "missing-approved-review-round", "design_system.approval.review_round must identify the approved round", "design_system.approval.review_round")
		}
		if !isNonEmptyStringList(approval["decision_ids"], true) {
			addDesignDiagnostic(diagnostics, "missing-approved-decision-ids", "design_system.approval.decision_ids must freeze the approved DS-* set", "design_system.approval.decision_ids")
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
	}
	for key, value := range expected {
		if strings.TrimSpace(fmt.Sprint(payload[key])) != strings.TrimSpace(fmt.Sprint(value)) {
			addDesignDiagnostic(&diagnostics, "preview-stale-approval-sidecar", "approval sidecar "+key+" does not bind the current approved preview", filepath.Base(sidecar)+"."+key)
		}
	}
	if !isNonEmptyStringList(payload["decision_ids"], true) {
		addDesignDiagnostic(&diagnostics, "preview-invalid-approval-decisions", "approval sidecar decision_ids must be a list of stable non-empty IDs", filepath.Base(sidecar)+".decision_ids")
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
			for _, field := range []string{"preview_sha256", "manifest_sha256"} {
				if !hexDigestRE.MatchString(strings.TrimSpace(fmt.Sprint(approval[field]))) {
					addDesignDiagnostic(diagnostics, "ui-target-invalid-approval-digest", "approved HTML preview requires a valid "+field, "manifest.approval."+field)
				}
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
		candidates = append(candidates, filepath.Join(cwd, "templates", name))
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
		"--notes": true, "--direction": true,
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
	updated := re.ReplaceAllString(content, "${1}"+value+"${2}")
	if updated == content {
		return "", fmt.Errorf("design preview is missing required attribute %s", name)
	}
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
