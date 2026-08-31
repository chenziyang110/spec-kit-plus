package main

import (
	"bytes"
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
	"unicode/utf8"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/filelock"
)

const (
	designPreviewSchema            = "spec-kit-design-preview-v1"
	designPreviewManifestSchema    = "spec-kit-design-preview-manifest-v1"
	designPreviewApprovalSchema    = "spec-kit-design-preview-approval-v1"
	designImageApprovalSchema      = "spec-kit-design-image-approval-v1"
	designHandoffSchema            = "spec-kit-design-handoff-v1"
	designChangeSchema             = "spec-kit-ui-design-change-v1"
	designChangeIndexSchema        = "spec-kit-ui-design-index-v1"
	uiProfessionalSkillCatalog     = "spec-kit-ui-professional-v1"
	designCapabilityProfilesSchema = "spec-kit-design-capability-profiles-v1"
	designCapabilityModelSchema    = "spec-kit-design-capability-model-v1"
	designPreviewManifestID        = "design-preview-manifest"
	uiTargetSchema                 = "spec-kit-ui-target-v1"
	uiTargetManifestSchema         = "spec-kit-ui-target-manifest-v1"
	uiTargetManifestID             = "ui-target-manifest"
)

var designImageSuffixes = map[string]bool{
	".png": true, ".jpg": true, ".jpeg": true, ".webp": true,
}

func acquireDesignIndexLock(root string) (func(), error) {
	designRoot := filepath.Join(root, ".specify", "design")
	if err := os.MkdirAll(designRoot, 0o755); err != nil {
		return nil, fmt.Errorf("create UI design transaction directory: %w", err)
	}
	release, err := filelock.Acquire(filepath.Join(designRoot, ".index.lock"))
	if err != nil {
		return nil, fmt.Errorf("acquire UI design index transaction: %w", err)
	}
	return release, nil
}

var (
	frontMatterRE           = regexp.MustCompile(`(?s)\A---\s*\r?\n(.*?)\r?\n---\s*\r?\n?(.*)\z`)
	tokenNameRE             = regexp.MustCompile(`^[a-z][a-z0-9]*(?:\.[a-z0-9]+)*$`)
	tokenRefRE              = regexp.MustCompile(`^\{([a-z][a-z0-9]*)\.([a-z][a-z0-9]*(?:\.[a-z0-9]+)*)\}$`)
	headingRECache          = map[string]*regexp.Regexp{}
	previewDirectionIDRE    = regexp.MustCompile(`^direction-[a-z0-9][a-z0-9-]*$`)
	designSpecimenIDRE      = regexp.MustCompile(`^SP-[A-Z0-9]+(?:-[A-Z0-9]+)+$`)
	previewPlaceholderRE    = regexp.MustCompile(`__[A-Z0-9_]+__`)
	previewSeedRE           = regexp.MustCompile(`(?i)(?:freeform-seed|unfinished prototype seed|replace this seed)`)
	remoteReferenceRE       = regexp.MustCompile(`(?i)(?:https?:)?//|@import\b`)
	cssURLReferenceRE       = regexp.MustCompile(`(?is)url\s*\(\s*["']?([^"')\s]+)`)
	networkRuntimeRE        = regexp.MustCompile(`(?i)\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(`)
	uiPersistenceRuntimeRE  = regexp.MustCompile(`(?i)\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(|\b(?:localStorage|sessionStorage|indexedDB|document\.cookie)\b`)
	hexDigestRE             = regexp.MustCompile(`^[0-9a-f]{64}$`)
	canonicalDecisionIDRE   = regexp.MustCompile(`^DS-[A-Z0-9]+(?:-[A-Z0-9]+)+$`)
	uiCanonicalDecisionIDRE = regexp.MustCompile(`^DS-[A-Z0-9]+(?:-[A-Z0-9]+)+$`)
	canonicalHandoffIDRE    = regexp.MustCompile(`^DH-[A-Z0-9]+(?:-[A-Z0-9]+)+$`)
	designChangeIDRE        = regexp.MustCompile(`^UD-[0-9]{4,}$`)
	designChangeScopeRE     = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9._:/-]*$`)
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
	case "change":
		return runDesignChange(args[1:], stdout)
	case "iterate":
		return runDesignIterate(args[1:], stdout)
	case "register":
		return runDesignRegister(args[1:], stdout)
	case "resolve":
		return runDesignResolve(args[1:], stdout)
	case "diff":
		return runDesignDiff(args[1:], stdout)
	case "impact":
		return runDesignImpact(args[1:], stdout)
	case "adopt":
		return runDesignAdopt(args[1:], stdout)
	case "adoption":
		return runDesignAdoption(args[1:], stdout)
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

func runDesignChange(args []string, stdout io.Writer) int {
	if len(args) == 0 || strings.HasPrefix(args[0], "-") {
		return writeDesignError(stdout, "usage-error", "design change requires a UD-* change ID")
	}
	title := strings.TrimSpace(optionValue(args, "--title", ""))
	if title == "" {
		return writeDesignError(stdout, "usage-error", "design change requires --title")
	}
	changeType := strings.ToLower(strings.TrimSpace(optionValue(args, "--type", "extension")))
	scopes := optionValues(args, "--scope")
	profileIDs, err := parseDesignCapabilityProfileIDs(optionValue(args, "--profiles", "web"))
	if err != nil {
		return writeDesignError(stdout, "usage-error", err.Error())
	}
	path, err := scaffoldDesignChange(
		args[0],
		title,
		changeType,
		scopes,
		profileIDs,
		optionValues(args, "--baseline-ref"),
		optionValues(args, "--supersedes"),
		"",
		"",
	)
	if err != nil {
		return writeDesignError(stdout, "blocked", err.Error())
	}
	workspace := filepath.Dir(path)
	env := NewEnvelope("ok", "UI design change workspace created")
	env.Data["path"] = filepath.ToSlash(path)
	env.Data["index_path"] = ".specify/design/index.json"
	env.Data["brief_path"] = filepath.ToSlash(filepath.Join(workspace, "brief.md"))
	env.NextArgv = []string{
		"specify-runtime", "design", "preview-manifest",
		"--profiles", strings.Join(profileIDs, ","),
		"--out", filepath.ToSlash(filepath.Join(workspace, "previews", "round-01.manifest.json")),
	}
	return writeEnvelope(stdout, env)
}

func runDesignRegister(args []string, stdout io.Writer) int {
	if len(args) == 0 || strings.HasPrefix(args[0], "-") {
		return writeDesignError(stdout, "usage-error", "design register requires a change-local design-change.md path")
	}
	target, env, ok := designContainedPath(args[0], false)
	if !ok {
		return writeEnvelope(stdout, env)
	}
	record, err := registerDesignChange(target)
	if err != nil {
		return writeDesignError(stdout, "blocked", err.Error())
	}
	env = NewEnvelope("ok", "UI design change registered")
	env.Data["change"] = record
	return writeEnvelope(stdout, env)
}

func runDesignLint(args []string, stdout io.Writer) int {
	level := strings.ToLower(optionValue(args, "--level", "structural"))
	if !supportedDesignLintLevel(level) {
		return writeDesignError(stdout, "usage-error", "unsupported design lint level: "+level)
	}
	path := firstPositional(args, "")
	if path == "" {
		return writeDesignError(stdout, "usage-error", "design lint requires a change-local design-change.md path")
	}
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
	var diagnostics []designDiagnostic
	if strings.EqualFold(filepath.Ext(target), ".html") {
		diagnostics = lintDesignPreviewFile(target, level)
	} else {
		diagnostics = lintDesignImageBundle(target, level)
	}
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
	var payload map[string]any
	var err error
	if strings.EqualFold(filepath.Ext(target), ".html") {
		for _, option := range []string{"--manifest", "--prompt", "--image-inspection", "--image-editing"} {
			if strings.TrimSpace(optionValue(args, option, "")) != "" {
				return writeDesignError(stdout, "usage-error", "HTML approval does not accept image manifest, prompt, or capability flags")
			}
		}
		payload, err = approveDesignPreview(target, direction)
	} else {
		manifestArg := strings.TrimSpace(optionValue(args, "--manifest", ""))
		promptArg := strings.TrimSpace(optionValue(args, "--prompt", ""))
		inspection := strings.TrimSpace(optionValue(args, "--image-inspection", ""))
		editing := strings.TrimSpace(optionValue(args, "--image-editing", ""))
		if manifestArg == "" || promptArg == "" {
			return writeDesignError(stdout, "usage-error", "image approval requires --manifest and --prompt")
		}
		if inspection == "" || editing == "" {
			return writeDesignError(stdout, "usage-error", "image approval requires --image-inspection and --image-editing")
		}
		manifestPath, manifestEnv, manifestOK := designContainedPath(manifestArg, false)
		if !manifestOK {
			return writeEnvelope(stdout, manifestEnv)
		}
		promptPath, promptEnv, promptOK := designContainedPath(promptArg, false)
		if !promptOK {
			return writeEnvelope(stdout, promptEnv)
		}
		payload, err = approveDesignImage(target, manifestPath, promptPath, direction, inspection, editing)
	}
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
	path := firstPositional(args, "")
	if path == "" {
		return writeDesignError(stdout, "usage-error", "design export requires a change-local design-change.md path")
	}
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

func normalizeDesignChangeValues(values []string, field string, required bool) ([]string, error) {
	normalized := []string{}
	seen := map[string]bool{}
	for _, raw := range values {
		value := strings.TrimSpace(raw)
		if value == "" {
			continue
		}
		if seen[value] {
			return nil, fmt.Errorf("%s values must be unique", field)
		}
		seen[value] = true
		normalized = append(normalized, value)
	}
	if required && len(normalized) == 0 {
		return nil, fmt.Errorf("at least one %s value is required", field)
	}
	return normalized, nil
}

func designTemplateJSON(value any) (string, error) {
	raw, err := json.Marshal(value)
	if err != nil {
		return "", err
	}
	return string(raw), nil
}

func scaffoldDesignChange(changeID, title, changeType string, scopes, profileIDs, baselineRefs, supersedes []string, iterationOf, basisSHA256 string) (string, error) {
	changeID = strings.ToUpper(strings.TrimSpace(changeID))
	if !designChangeIDRE.MatchString(changeID) {
		return "", fmt.Errorf("change ID must use UD- followed by at least four digits")
	}
	title = strings.TrimSpace(title)
	if title == "" {
		return "", fmt.Errorf("design change title is required")
	}
	changeType = strings.ToLower(strings.TrimSpace(changeType))
	changeTypes := map[string]bool{"greenfield": true, "preserve": true, "overhaul": true, "extension": true}
	if !changeTypes[changeType] {
		return "", fmt.Errorf("design change type must be greenfield, preserve, overhaul, or extension")
	}
	normalizedScopes, err := normalizeDesignChangeValues(scopes, "scope", true)
	if err != nil {
		return "", err
	}
	for _, scope := range normalizedScopes {
		if !designChangeScopeRE.MatchString(scope) {
			return "", fmt.Errorf("design change scope must be a stable path-like identifier: %s", scope)
		}
	}
	normalizedProfiles, err := normalizeDesignChangeValues(profileIDs, "profile", true)
	if err != nil {
		return "", err
	}
	if _, err := selectDesignCapabilityProfiles(normalizedProfiles); err != nil {
		return "", err
	}
	normalizedBaselines, err := normalizeDesignChangeValues(baselineRefs, "baseline-ref", false)
	if err != nil {
		return "", err
	}
	normalizedSupersedes, err := normalizeDesignChangeValues(supersedes, "supersedes", false)
	if err != nil {
		return "", err
	}
	for index, supersededID := range normalizedSupersedes {
		normalizedSupersedes[index] = strings.ToUpper(supersededID)
		if !designChangeIDRE.MatchString(normalizedSupersedes[index]) {
			return "", fmt.Errorf("supersedes values must use UD- followed by at least four digits")
		}
		if normalizedSupersedes[index] == changeID {
			return "", fmt.Errorf("a design change cannot supersede itself")
		}
	}
	root, err := os.Getwd()
	if err != nil {
		return "", err
	}
	release, err := acquireDesignIndexLock(root)
	if err != nil {
		return "", err
	}
	defer release()

	workspace := filepath.Join(".specify", "design", "changes", changeID)
	designPath := filepath.Join(workspace, "design-change.md")
	if _, err := os.Stat(designPath); err == nil {
		return "", fmt.Errorf("design change already exists: %s", changeID)
	} else if !os.IsNotExist(err) {
		return "", err
	}

	indexPath := filepath.Join(".specify", "design", "index.json")
	indexPayload := map[string]any{
		"schema":  designChangeIndexSchema,
		"changes": []any{},
	}
	if raw, err := os.ReadFile(indexPath); err == nil {
		if err := json.Unmarshal(raw, &indexPayload); err != nil {
			return "", fmt.Errorf("cannot read design change index: %v", err)
		}
	} else if !os.IsNotExist(err) {
		return "", fmt.Errorf("cannot read design change index: %v", err)
	}
	if indexPayload["schema"] != designChangeIndexSchema {
		return "", fmt.Errorf("design change index has an invalid schema")
	}
	changes, ok := indexPayload["changes"].([]any)
	if !ok {
		return "", fmt.Errorf("design change index changes must be a list")
	}
	for _, rawChange := range changes {
		change, _ := rawChange.(map[string]any)
		if strings.TrimSpace(fmt.Sprint(change["id"])) == changeID {
			return "", fmt.Errorf("design change already exists: %s", changeID)
		}
	}

	templatePath, err := locateTemplate("design-change-template.md")
	if err != nil {
		return "", err
	}
	template, err := os.ReadFile(templatePath)
	if err != nil {
		return "", err
	}
	replacements := map[string]any{
		"__DESIGN_CHANGE_ID__":            changeID,
		"__DESIGN_CHANGE_TITLE__":         title,
		"__DESIGN_CHANGE_TYPE__":          changeType,
		"__DESIGN_CHANGE_SCOPES__":        normalizedScopes,
		"__DESIGN_CHANGE_PROFILES__":      normalizedProfiles,
		"__DESIGN_CHANGE_BASELINE_REFS__": normalizedBaselines,
		"__DESIGN_CHANGE_SUPERSEDES__":    normalizedSupersedes,
		"__DESIGN_CHANGE_ITERATION_OF__":  nil,
	}
	if iterationOf != "" {
		replacements["__DESIGN_CHANGE_ITERATION_OF__"] = iterationOf
	}
	rendered := string(template)
	for placeholder, value := range replacements {
		literal, err := designTemplateJSON(value)
		if err != nil {
			return "", err
		}
		rendered = strings.ReplaceAll(rendered, placeholder, literal)
	}
	doc, err := parseDesignMarkdown(rendered, templatePath)
	if err != nil {
		return "", fmt.Errorf("rendered design change template is invalid: %v", err)
	}
	if doc.DesignSystem["schema"] != designChangeSchema {
		return "", fmt.Errorf("rendered design change template has an invalid schema")
	}

	briefTemplatePath, err := locateTemplate("design-brief-template.md")
	if err != nil {
		return "", err
	}
	brief, err := os.ReadFile(briefTemplatePath)
	if err != nil {
		return "", err
	}
	if err := writeTextAtomic(designPath, rendered); err != nil {
		return "", err
	}
	if err := writeTextAtomic(filepath.Join(workspace, "brief.md"), string(brief)); err != nil {
		return "", err
	}
	if err := os.MkdirAll(filepath.Join(workspace, "previews"), 0o755); err != nil {
		return "", err
	}
	record := map[string]any{
		"id":              changeID,
		"title":           title,
		"design_ref":      filepath.ToSlash(designPath),
		"status":          "draft",
		"change_type":     changeType,
		"scope":           normalizedScopes,
		"supersedes":      normalizedSupersedes,
		"approval_sha256": nil,
		"consumers":       []any{},
	}
	if iterationOf != "" {
		record["iteration_of"] = iterationOf
		record["basis_sha256"] = basisSHA256
	}
	changes = append(changes, record)
	indexPayload["changes"] = changes
	if err := writeJSONAtomic(indexPath, indexPayload); err != nil {
		return "", err
	}
	return designPath, nil
}

func registerDesignChange(path string) (map[string]any, error) {
	root, err := os.Getwd()
	if err != nil {
		return nil, err
	}
	release, err := acquireDesignIndexLock(root)
	if err != nil {
		return nil, err
	}
	defer release()
	if diagnostics := lintDesignFile(path, "ready"); len(diagnostics) > 0 {
		return nil, errors.New(joinDiagnostics(diagnostics))
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	doc, err := parseDesignMarkdown(string(raw), path)
	if err != nil {
		return nil, err
	}
	if doc.DesignSystem["schema"] != designChangeSchema {
		return nil, fmt.Errorf("only change-scoped design contracts can be registered")
	}
	changeID := strings.TrimSpace(fmt.Sprint(doc.DesignSystem["id"]))
	relative, err := filepath.Rel(root, path)
	if err != nil {
		return nil, err
	}
	relative = filepath.ToSlash(relative)
	parts := strings.Split(relative, "/")
	if len(parts) != 5 || parts[0] != ".specify" || parts[1] != "design" || parts[2] != "changes" || parts[3] != changeID || parts[4] != "design-change.md" {
		return nil, fmt.Errorf("design change must be inside .specify/design/changes/<UD-ID>/design-change.md and match design_change.id")
	}

	indexPath := filepath.Join(root, ".specify", "design", "index.json")
	indexRaw, err := os.ReadFile(indexPath)
	if err != nil {
		return nil, fmt.Errorf("cannot read design change index: %v", err)
	}
	index := map[string]any{}
	if err := json.Unmarshal(indexRaw, &index); err != nil {
		return nil, fmt.Errorf("cannot read design change index: %v", err)
	}
	if index["schema"] != designChangeIndexSchema {
		return nil, fmt.Errorf("design change index has an invalid schema")
	}
	changes, ok := index["changes"].([]any)
	if !ok {
		return nil, fmt.Errorf("design change index changes must be a list")
	}
	records := map[string]map[string]any{}
	for _, rawRecord := range changes {
		record, ok := rawRecord.(map[string]any)
		if !ok {
			continue
		}
		recordID := strings.TrimSpace(fmt.Sprint(record["id"]))
		records[recordID] = record
	}
	record := records[changeID]
	if record == nil {
		return nil, fmt.Errorf("design change %s is not registered in index.json", changeID)
	}
	digestBytes := sha256.Sum256(raw)
	digest := hex.EncodeToString(digestBytes[:])
	if record["status"] == "approved" || record["status"] == "superseded" {
		if record["approval_sha256"] == digest {
			return record, nil
		}
		return nil, fmt.Errorf("registered design change %s is immutable; create a new UD-* change", changeID)
	}

	scope, _ := doc.DesignSystem["scope"].(map[string]any)
	scopes := stringList(scope["surfaces"])
	relationships, _ := doc.DesignSystem["relationships"].(map[string]any)
	supersedes := stringList(relationships["supersedes"])
	iterationOf, _ := relationships["iteration_of"].(string)
	iterationOf = strings.TrimSpace(iterationOf)
	supersedesSet := map[string]bool{}
	for _, supersededID := range supersedes {
		if records[supersededID] == nil {
			return nil, fmt.Errorf("design change supersedes unknown ID: %s", supersededID)
		}
		supersedesSet[supersededID] = true
	}

	if iterationOf != "" {
		source := records[iterationOf]
		if source == nil || !designRecordIsRegistered(source) {
			return nil, fmt.Errorf("design iteration source %s must be registered", iterationOf)
		}
		basisSHA := strings.TrimSpace(fmt.Sprint(record["basis_sha256"]))
		if record["iteration_of"] != iterationOf || basisSHA != strings.TrimSpace(fmt.Sprint(source["approval_sha256"])) {
			return nil, fmt.Errorf("design iteration source binding does not match its index record")
		}
		wantBaseline := strings.TrimSpace(fmt.Sprint(source["design_ref"])) + "#sha256=" + basisSHA
		if !designStringContains(stringList(doc.DesignSystem["baseline_refs"]), wantBaseline) || !supersedesSet[iterationOf] {
			return nil, fmt.Errorf("design iteration must preserve its exact source baseline and supersedes relationship")
		}
	}

	type supersession struct {
		record map[string]any
		scopes []string
	}
	var supersededRecords []supersession
	for _, rawOther := range changes {
		other, ok := rawOther.(map[string]any)
		if !ok || other["id"] == changeID || other["status"] != "approved" {
			continue
		}
		intersections := designRecordActiveIntersections(other, scopes)
		if len(intersections) == 0 {
			continue
		}
		otherID := strings.TrimSpace(fmt.Sprint(other["id"]))
		if !supersedesSet[otherID] {
			return nil, fmt.Errorf("design change %s overlaps approved design change %s; declare supersedes or narrow the scope", changeID, otherID)
		}
		supersededRecords = append(supersededRecords, supersession{record: other, scopes: intersections})
	}

	if strings.TrimSpace(fmt.Sprint(record["design_ref"])) != relative {
		return nil, fmt.Errorf("design change path does not match index design_ref")
	}
	if !reflect.DeepEqual(stringList(record["scope"]), scopes) {
		return nil, fmt.Errorf("design change scope does not match its index record")
	}
	if !reflect.DeepEqual(stringList(record["supersedes"]), supersedes) {
		return nil, fmt.Errorf("design change supersedes relationships do not match its index record")
	}
	for _, prior := range supersededRecords {
		addDesignSupersededScopes(prior.record, prior.scopes, changeID)
	}
	record["status"] = "approved"
	record["approval_sha256"] = digest
	if err := writeJSONAtomic(indexPath, index); err != nil {
		return nil, err
	}
	return record, nil
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
	keys := []string{"schema", "name", "version", "status", "approval", "product_context", "professional_skill_route", "style_authority", "direction_contract", "platforms", "capability_profiles", "specimens", "tokens", "color_modes", "components", "responsive", "content", "decisions", "verification", "accessibility"}
	if _, ok := doc.FrontMatter["design_change"]; ok {
		keys = append(keys, "id", "title", "change_type", "scope", "baseline_refs", "relationships", "constraints")
	}
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
	collaboration, ok := manifest["visual_collaboration"].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("design preview manifest must freeze the live visual capability route")
	}
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
		"visual_medium":          "html",
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
	for _, field := range []string{"image_generation", "image_inspection", "image_editing", "inspection_owner", "prompt_strategy"} {
		payload[field] = strings.TrimSpace(fmt.Sprint(collaboration[field]))
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

func designImageArtifactDiagnostics(path string) ([]byte, []designDiagnostic) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, []designDiagnostic{{Code: "image-missing-file", Message: "cannot read design image: " + err.Error(), Path: path, Level: "error"}}
	}
	var diagnostics []designDiagnostic
	suffix := strings.ToLower(filepath.Ext(path))
	if !designImageSuffixes[suffix] {
		addDesignDiagnostic(&diagnostics, "image-unsupported-format", "design image must be PNG, JPEG, or WEBP", path)
		return raw, diagnostics
	}
	matches := false
	switch suffix {
	case ".png":
		matches = len(raw) >= 8 && bytes.Equal(raw[:8], []byte{0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n'})
	case ".jpg", ".jpeg":
		matches = len(raw) >= 3 && raw[0] == 0xff && raw[1] == 0xd8 && raw[2] == 0xff
	case ".webp":
		matches = len(raw) >= 12 && string(raw[:4]) == "RIFF" && string(raw[8:12]) == "WEBP"
	}
	if !matches {
		addDesignDiagnostic(&diagnostics, "image-format-mismatch", "design image bytes do not match the PNG, JPEG, or WEBP extension", path)
	}
	return raw, diagnostics
}

func adjacentDesignImageBundlePath(imagePath, candidate, expectedName, label string) (string, error) {
	imageDir, err := filepath.Abs(filepath.Dir(imagePath))
	if err != nil {
		return "", err
	}
	candidateDir, err := filepath.Abs(filepath.Dir(candidate))
	if err != nil {
		return "", err
	}
	if filepath.Base(candidate) != expectedName || filepath.Clean(candidateDir) != filepath.Clean(imageDir) {
		return "", fmt.Errorf("design image %s must be the adjacent %s", label, expectedName)
	}
	return candidate, nil
}

func approveDesignImage(path, manifestPath, promptPath, directionID, imageInspection, imageEditing string) (map[string]any, error) {
	imageBytes, imageDiagnostics := designImageArtifactDiagnostics(path)
	if len(imageDiagnostics) > 0 {
		return nil, errors.New(joinDiagnostics(imageDiagnostics))
	}
	imageInspection = strings.ToLower(strings.TrimSpace(imageInspection))
	imageEditing = strings.ToLower(strings.TrimSpace(imageEditing))
	for label, value := range map[string]string{"image inspection": imageInspection, "image editing": imageEditing} {
		if value != "available" && value != "unavailable" {
			return nil, fmt.Errorf("%s must be available or unavailable", label)
		}
	}
	base := strings.TrimSuffix(filepath.Base(path), filepath.Ext(path))
	var err error
	manifestPath, err = adjacentDesignImageBundlePath(path, manifestPath, base+".manifest.json", "manifest")
	if err != nil {
		return nil, err
	}
	promptPath, err = adjacentDesignImageBundlePath(path, promptPath, base+".prompt.md", "prompt")
	if err != nil {
		return nil, err
	}
	manifestRaw, err := os.ReadFile(manifestPath)
	if err != nil {
		return nil, fmt.Errorf("cannot read design image manifest: %w", err)
	}
	var manifest map[string]any
	if err := json.Unmarshal(manifestRaw, &manifest); err != nil {
		return nil, fmt.Errorf("cannot read design image manifest: %w", err)
	}
	review, ok := manifest["review"].(map[string]any)
	if !ok {
		return nil, fmt.Errorf("design image manifest review must be an object")
	}
	status := strings.ToLower(strings.TrimSpace(fmt.Sprint(review["status"])))
	approvalPath := strings.TrimSuffix(path, filepath.Ext(path)) + ".approval.json"
	if status == "approved" {
		return nil, fmt.Errorf("design image round is already approved and immutable: %s", path)
	}
	if _, statErr := os.Stat(approvalPath); statErr == nil {
		return nil, fmt.Errorf("design image round is already approved and immutable: %s", path)
	}
	if status != "candidate" {
		return nil, fmt.Errorf("design image manifest must be a configured candidate before approval")
	}
	var directionIDs []string
	if directions, ok := manifest["directions"].([]any); ok {
		for _, raw := range directions {
			if direction, ok := raw.(map[string]any); ok {
				if id := strings.TrimSpace(fmt.Sprint(direction["id"])); id != "" && id != "<nil>" {
					directionIDs = append(directionIDs, id)
				}
			}
		}
	}
	if !stringInSlice(directionID, directionIDs) {
		return nil, fmt.Errorf("unknown design direction %s; choose one of %s", directionID, strings.Join(directionIDs, ", "))
	}
	promptBytes, err := os.ReadFile(promptPath)
	if err != nil || !utf8.Valid(promptBytes) {
		if err == nil {
			err = fmt.Errorf("prompt is not valid UTF-8")
		}
		return nil, fmt.Errorf("cannot read image generation prompt: %w", err)
	}
	promptText := string(promptBytes)
	if len(strings.TrimSpace(promptText)) < 40 || previewPlaceholderRE.MatchString(promptText) {
		return nil, fmt.Errorf("image generation prompt must be project-specific, non-placeholder Markdown")
	}
	inspectionOwner := "user"
	if imageInspection == "available" {
		inspectionOwner = "agent-and-user"
	}
	manifest["visual_collaboration"] = map[string]any{
		"primary_medium":   "image-primary",
		"image_generation": "available",
		"image_inspection": imageInspection,
		"image_editing":    imageEditing,
		"inspection_owner": inspectionOwner,
		"prompt_strategy":  "image-generation",
	}
	review["status"] = "approved"
	review["approved_direction"] = directionID
	if diagnostics := previewManifestDiagnostics(manifest, directionIDs, true, "image-primary"); len(diagnostics) > 0 {
		return nil, fmt.Errorf("design image manifest is not ready for approval: %s", joinDiagnostics(diagnostics))
	}
	decisionIDs := manifestDecisionIDs(manifest)
	if len(decisionIDs) == 0 {
		return nil, fmt.Errorf("design image manifest must define stable decisions before approval")
	}
	promptSHA256 := sha256Bytes(promptBytes)
	imageSHA256 := sha256Bytes(imageBytes)
	handoffPath := strings.TrimSuffix(path, filepath.Ext(path)) + ".handoff.json"
	handoffPayload, err := buildDesignHandoffPayloadForMedium(path, imageBytes, directionID, manifest, "image", promptSHA256, inspectionOwner)
	if err != nil {
		return nil, err
	}
	handoffText, err := marshalPretty(handoffPayload)
	if err != nil {
		return nil, fmt.Errorf("cannot render design image handoff: %w", err)
	}
	payload := map[string]any{
		"schema":                 designImageApprovalSchema,
		"visual_medium":          "image",
		"preview_file":           filepath.Base(path),
		"direction_id":           directionID,
		"preview_ref":            filepath.Base(path) + "#" + directionID,
		"review_round":           strings.TrimSpace(fmt.Sprint(review["round"])),
		"image_sha256":           imageSHA256,
		"preview_sha256":         imageSHA256,
		"manifest_file":          filepath.Base(manifestPath),
		"manifest_ref":           filepath.Base(manifestPath),
		"manifest_sha256":        canonicalJSONSHA256(manifest),
		"prompt_file":            filepath.Base(promptPath),
		"prompt_ref":             filepath.Base(promptPath),
		"prompt_sha256":          promptSHA256,
		"image_generation":       "available",
		"image_inspection":       imageInspection,
		"image_editing":          imageEditing,
		"inspection_owner":       inspectionOwner,
		"prompt_strategy":        "image-generation",
		"decision_ids":           decisionIDs,
		"handoff_file":           filepath.Base(handoffPath),
		"handoff_ref":            filepath.Base(handoffPath),
		"handoff_sha256":         sha256String(handoffText),
		"handoff_contract_ids":   manifestHandoffContractIDs(manifest),
		"capability_profile_ids": manifestCapabilityProfileIDs(manifest),
		"specimen_ids":           manifestSpecimenIDs(manifest),
	}
	manifestText, err := marshalPretty(manifest)
	if err != nil {
		return nil, fmt.Errorf("cannot render approved design image manifest: %w", err)
	}
	approvalText, err := marshalPretty(payload)
	if err != nil {
		return nil, fmt.Errorf("cannot render design image approval: %w", err)
	}
	if err := validateDesignImageApprovalBundle(path, imageBytes, manifestText, promptBytes, handoffText, approvalText); err != nil {
		return nil, err
	}
	projectRoot, err := os.Getwd()
	if err != nil {
		return nil, err
	}
	if _, err := applyFileTransaction(projectRoot, "design.approve-image", []fileTransactionUpdate{
		{Path: manifestPath, Content: []byte(manifestText), Perm: 0o644},
		{Path: handoffPath, Content: []byte(handoffText), Perm: 0o644},
		{Path: approvalPath, Content: []byte(approvalText), Perm: 0o644},
	}); err != nil {
		return nil, fmt.Errorf("cannot commit design image approval: %w", err)
	}
	return payload, nil
}

func validateDesignImageApprovalBundle(path string, imageBytes []byte, manifestText string, promptBytes []byte, handoffText, approvalText string) error {
	validationRoot, err := os.MkdirTemp(filepath.Dir(path), ".design-image-approval-validation-*")
	if err != nil {
		return err
	}
	defer os.RemoveAll(validationRoot)
	base := strings.TrimSuffix(filepath.Base(path), filepath.Ext(path))
	imagePath := filepath.Join(validationRoot, filepath.Base(path))
	files := []struct {
		path    string
		content []byte
	}{
		{imagePath, imageBytes},
		{filepath.Join(validationRoot, base+".manifest.json"), []byte(manifestText)},
		{filepath.Join(validationRoot, base+".prompt.md"), promptBytes},
		{filepath.Join(validationRoot, base+".handoff.json"), []byte(handoffText)},
		{filepath.Join(validationRoot, base+".approval.json"), []byte(approvalText)},
	}
	for _, file := range files {
		if err := os.WriteFile(file.path, file.content, 0o644); err != nil {
			return err
		}
	}
	if diagnostics := lintDesignImageBundle(imagePath, "ready"); len(diagnostics) > 0 {
		return fmt.Errorf("approved design image failed deterministic validation: %s", joinDiagnostics(diagnostics))
	}
	return nil
}

func lintDesignImageBundle(path, level string) []designDiagnostic {
	imageBytes, diagnostics := designImageArtifactDiagnostics(path)
	if len(diagnostics) > 0 || strings.EqualFold(level, "structural") {
		return diagnostics
	}
	basePath := strings.TrimSuffix(path, filepath.Ext(path))
	approvalPath := basePath + ".approval.json"
	approvalRaw, err := os.ReadFile(approvalPath)
	if err != nil {
		addDesignDiagnostic(&diagnostics, "image-missing-approval-sidecar", "cannot read approved image sidecar: "+err.Error(), approvalPath)
		return diagnostics
	}
	var approval map[string]any
	if err := json.Unmarshal(approvalRaw, &approval); err != nil {
		addDesignDiagnostic(&diagnostics, "image-invalid-approval-sidecar", "cannot read approved image sidecar: "+err.Error(), approvalPath)
		return diagnostics
	}
	directionID := strings.TrimSpace(fmt.Sprint(approval["direction_id"]))
	imageSHA256 := sha256Bytes(imageBytes)
	expected := map[string]any{
		"schema":           designImageApprovalSchema,
		"visual_medium":    "image",
		"preview_file":     filepath.Base(path),
		"preview_ref":      filepath.Base(path) + "#" + directionID,
		"image_sha256":     imageSHA256,
		"preview_sha256":   imageSHA256,
		"manifest_file":    filepath.Base(basePath + ".manifest.json"),
		"manifest_ref":     filepath.Base(basePath + ".manifest.json"),
		"prompt_file":      filepath.Base(basePath + ".prompt.md"),
		"prompt_ref":       filepath.Base(basePath + ".prompt.md"),
		"handoff_file":     filepath.Base(basePath + ".handoff.json"),
		"handoff_ref":      filepath.Base(basePath + ".handoff.json"),
		"image_generation": "available",
		"prompt_strategy":  "image-generation",
	}
	for key, value := range expected {
		if strings.TrimSpace(fmt.Sprint(approval[key])) != strings.TrimSpace(fmt.Sprint(value)) {
			addDesignDiagnostic(&diagnostics, "image-stale-approval-sidecar", "image approval sidecar "+key+" does not bind the immutable round", filepath.Base(approvalPath)+"."+key)
		}
	}
	imageInspection := strings.TrimSpace(fmt.Sprint(approval["image_inspection"]))
	imageEditing := strings.TrimSpace(fmt.Sprint(approval["image_editing"]))
	inspectionOwner := strings.TrimSpace(fmt.Sprint(approval["inspection_owner"]))
	expectedOwner := "user"
	if imageInspection == "available" {
		expectedOwner = "agent-and-user"
	}
	if (imageInspection != "available" && imageInspection != "unavailable") || (imageEditing != "available" && imageEditing != "unavailable") || inspectionOwner != expectedOwner {
		addDesignDiagnostic(&diagnostics, "image-invalid-capability-binding", "image approval must bind inspection/editing availability and the truthful inspection owner", approvalPath)
	}

	manifestPath := basePath + ".manifest.json"
	manifestRaw, err := os.ReadFile(manifestPath)
	if err != nil {
		addDesignDiagnostic(&diagnostics, "image-invalid-manifest", "cannot read design image manifest: "+err.Error(), manifestPath)
		return diagnostics
	}
	var manifest map[string]any
	if err := json.Unmarshal(manifestRaw, &manifest); err != nil {
		addDesignDiagnostic(&diagnostics, "image-invalid-manifest", "cannot read design image manifest: "+err.Error(), manifestPath)
		return diagnostics
	}
	if strings.TrimSpace(fmt.Sprint(approval["manifest_sha256"])) != canonicalJSONSHA256(manifest) {
		addDesignDiagnostic(&diagnostics, "image-stale-manifest-binding", "image approval sidecar does not bind the immutable manifest", manifestPath)
	}
	var directionIDs []string
	if directions, ok := manifest["directions"].([]any); ok {
		for _, raw := range directions {
			if direction, ok := raw.(map[string]any); ok {
				directionIDs = append(directionIDs, strings.TrimSpace(fmt.Sprint(direction["id"])))
			}
		}
	}
	diagnostics = append(diagnostics, previewManifestDiagnostics(manifest, directionIDs, true, "image-primary")...)
	review, _ := manifest["review"].(map[string]any)
	if strings.TrimSpace(fmt.Sprint(review["status"])) != "approved" || strings.TrimSpace(fmt.Sprint(review["approved_direction"])) != directionID {
		addDesignDiagnostic(&diagnostics, "image-unapproved-manifest", "design image manifest must freeze the approved direction", "manifest.review")
	}
	expectedCollaboration := map[string]any{
		"primary_medium":   "image-primary",
		"image_generation": "available",
		"image_inspection": imageInspection,
		"image_editing":    imageEditing,
		"inspection_owner": inspectionOwner,
		"prompt_strategy":  "image-generation",
	}
	if !reflect.DeepEqual(manifest["visual_collaboration"], expectedCollaboration) {
		addDesignDiagnostic(&diagnostics, "image-capability-manifest-drift", "manifest visual_collaboration must match the approved live capability route", "manifest.visual_collaboration")
	}

	promptPath := basePath + ".prompt.md"
	promptBytes, err := os.ReadFile(promptPath)
	if err != nil || !utf8.Valid(promptBytes) {
		if err == nil {
			err = fmt.Errorf("prompt is not valid UTF-8")
		}
		addDesignDiagnostic(&diagnostics, "image-invalid-generation-prompt", "cannot read image generation prompt: "+err.Error(), promptPath)
		return diagnostics
	}
	if len(strings.TrimSpace(string(promptBytes))) < 40 || previewPlaceholderRE.Match(promptBytes) || strings.TrimSpace(fmt.Sprint(approval["prompt_sha256"])) != sha256Bytes(promptBytes) {
		addDesignDiagnostic(&diagnostics, "image-stale-prompt-binding", "approved image must bind its project-specific generation/edit prompt", promptPath)
	}

	handoffPath := basePath + ".handoff.json"
	handoffRaw, err := os.ReadFile(handoffPath)
	if err != nil {
		addDesignDiagnostic(&diagnostics, "image-invalid-handoff-sidecar", "cannot read design image handoff: "+err.Error(), handoffPath)
		return diagnostics
	}
	var handoff map[string]any
	if err := json.Unmarshal(handoffRaw, &handoff); err != nil {
		addDesignDiagnostic(&diagnostics, "image-invalid-handoff-sidecar", "cannot read design image handoff: "+err.Error(), handoffPath)
		return diagnostics
	}
	if strings.TrimSpace(fmt.Sprint(approval["handoff_sha256"])) != sha256Bytes(handoffRaw) {
		addDesignDiagnostic(&diagnostics, "image-stale-handoff-binding", "image approval sidecar does not bind the immutable handoff", handoffPath)
	}
	expectedHandoff, buildErr := buildDesignHandoffPayloadForMedium(path, imageBytes, directionID, manifest, "image", sha256Bytes(promptBytes), inspectionOwner)
	if buildErr != nil {
		addDesignDiagnostic(&diagnostics, "image-invalid-handoff-sidecar", buildErr.Error(), handoffPath)
		return diagnostics
	}
	if canonicalJSONSHA256(handoff) != canonicalJSONSHA256(expectedHandoff) {
		addDesignDiagnostic(&diagnostics, "image-stale-handoff-sidecar", "image handoff must be the exact deterministic projection of the approved concept", handoffPath)
	}
	return diagnostics
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
	if len(parsed.DirectionIDs) != 1 {
		addDesignDiagnostic(&diagnostics, "preview-direction-count", "design preview must contain exactly one current concept", "data-direction-id")
	}
	if hasDuplicates(parsed.DirectionIDs) {
		addDesignDiagnostic(&diagnostics, "preview-duplicate-direction", "design direction IDs must be unique", "data-direction-id")
	}
	if !reflect.DeepEqual(parsed.DirectionIDs, parsed.DirectionAnchorIDs) {
		addDesignDiagnostic(&diagnostics, "preview-direction-anchor-mismatch", "every direction control must expose an id equal to its data-direction-id", "data-direction-id.id")
	}
	manifest, err := parseJSONObject(parsed.PreviewManifestText)
	if err != nil {
		addDesignDiagnostic(&diagnostics, "preview-invalid-manifest", err.Error(), "script#"+designPreviewManifestID)
	} else {
		diagnostics = append(diagnostics, previewManifestDiagnostics(manifest, parsed.DirectionIDs, level == "ready", "html-primary")...)
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
		if strings.ToLower(strings.TrimSpace(parsed.PreviewAttrs["data-prototype-status"])) != "authored" || previewSeedRE.MatchString(content) {
			addDesignDiagnostic(&diagnostics, "preview-unfinished-prototype", "ready preview must replace the prototype seed and set data-prototype-status=authored after visual inspection", "data-prototype-status")
		}
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
	decisionKindsByContract := map[string][]string{
		"component_contracts":  {"color", "typography", "spacing", "component", "motion"},
		"interaction_matrix":   {"component", "motion", "responsive"},
		"editing_matrix":       {"typography", "spacing", "component", "motion", "responsive", "content"},
		"data_state_matrix":    {"color", "component", "content"},
		"accessibility_matrix": {"color", "typography", "spacing", "component", "motion", "responsive", "content"},
		"navigation_matrix":    {"component", "responsive", "content"},
		"content_matrix":       {"color", "typography", "spacing", "content"},
		"responsive_matrix":    {"typography", "spacing", "component", "responsive"},
		"motion_contract":      {"component", "motion"},
	}
	decisionIDs := manifestDecisionIDs(manifest)
	decisionIDsFor := func(contractKind string, source map[string]any) []string {
		requested := stringList(source["decision_kinds"])
		if len(requested) == 0 {
			requested = decisionKindsByContract[contractKind]
		}
		requestedSet := stringSliceSet(requested)
		var ids []string
		decisions, _ := manifest["decisions"].([]any)
		for _, raw := range decisions {
			decision, ok := raw.(map[string]any)
			if !ok || !requestedSet[strings.TrimSpace(fmt.Sprint(decision["kind"]))] {
				continue
			}
			id := strings.TrimSpace(fmt.Sprint(decision["id"]))
			if id != "" && id != "<nil>" {
				ids = append(ids, id)
			}
		}
		return ids
	}
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
	var components, responsive, acceptance, surfaceCatalog, scenarioMatrix []any
	var projectSourceRefs []string
	if project, ok := manifest["project"].(map[string]any); ok {
		projectSourceRefs = stringList(project["modules"])
	}
	professionalMatrices := map[string][]any{
		"interaction_matrix":   {},
		"editing_matrix":       {},
		"data_state_matrix":    {},
		"accessibility_matrix": {},
		"navigation_matrix":    {},
		"content_matrix":       {},
	}
	var motionPurposes, reducedMotionRules []string
	var motionTransitions []any
	feedbackTiming := map[string]int{}
	feedbackTimingSet := false
	riskRank := map[string]int{"low": 0, "medium": 1, "high": 2}
	riskLevel := ""
	var usabilityMethods, usabilityTasks, usabilityCriteria, smoothnessIDs []string
	methodSeen, taskSeen, criteriaSeen, smoothnessSeen := map[string]bool{}, map[string]bool{}, map[string]bool{}, map[string]bool{}
	performanceBudgets := map[string]float64{}
	budgetRowsSeen, budgetRowsValid := false, true
	humanReviewRequired := false
	for _, profile := range profiles {
		profileID := strings.TrimSpace(fmt.Sprint(profile["id"]))
		var profileSpecimenIDs, requiredStates []string
		var profileComponents, profileMotion, profileResponsive []any
		profileMatrices := map[string][]any{
			"interaction_matrix":   {},
			"editing_matrix":       {},
			"data_state_matrix":    {},
			"accessibility_matrix": {},
			"navigation_matrix":    {},
			"content_matrix":       {},
		}
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
			contract["interaction_modes"] = cloneJSONValue(profile["input_modes"])
			contract["decision_ids"] = designAnyStringList(decisionIDsFor("component_contracts", rawContract))
			delete(contract, "decision_kinds")
			components = append(components, contract)
			profileComponents = append(profileComponents, contract)
		}
		for field := range professionalMatrices {
			rows, _ := profile[field].([]any)
			for _, raw := range rows {
				row, ok := raw.(map[string]any)
				if !ok {
					continue
				}
				projected := cloneJSONMap(row)
				projected["decision_ids"] = designAnyStringList(decisionIDsFor(field, row))
				delete(projected, "decision_kinds")
				professionalMatrices[field] = append(professionalMatrices[field], projected)
				profileMatrices[field] = append(profileMatrices[field], projected)
			}
		}
		if motion, ok := profile["motion_contract"].(map[string]any); ok {
			if purpose := strings.TrimSpace(fmt.Sprint(motion["purpose"])); purpose != "" && purpose != "<nil>" {
				motionPurposes = append(motionPurposes, profileID+": "+purpose)
			}
			if reduced := strings.TrimSpace(fmt.Sprint(motion["reduced_motion"])); reduced != "" && reduced != "<nil>" {
				reducedMotionRules = append(reducedMotionRules, profileID+": "+reduced)
			}
			if transitions, ok := motion["transitions"].([]any); ok {
				for _, raw := range transitions {
					transition, ok := raw.(map[string]any)
					if !ok {
						continue
					}
					projected := cloneJSONMap(transition)
					projected["decision_ids"] = designAnyStringList(decisionIDsFor("motion_contract", transition))
					delete(projected, "decision_kinds")
					motionTransitions = append(motionTransitions, projected)
					profileMotion = append(profileMotion, projected)
				}
			}
			if timing, ok := motion["feedback_timing"].(map[string]any); ok {
				immediate, immediateOK := designJSONInt(timing["immediate_ms"])
				progress, progressOK := designJSONInt(timing["progress_ms"])
				timeout, timeoutOK := designJSONInt(timing["timeout_ms"])
				if immediateOK && progressOK && timeoutOK {
					if !feedbackTimingSet {
						feedbackTiming = map[string]int{"immediate_ms": immediate, "progress_ms": progress, "timeout_ms": timeout}
						feedbackTimingSet = true
					} else {
						feedbackTiming["immediate_ms"] = min(feedbackTiming["immediate_ms"], immediate)
						feedbackTiming["progress_ms"] = min(feedbackTiming["progress_ms"], progress)
						feedbackTiming["timeout_ms"] = max(feedbackTiming["timeout_ms"], timeout)
					}
				}
			}
		}
		if usability, ok := profile["usability_validation"].(map[string]any); ok {
			candidateRisk := strings.TrimSpace(fmt.Sprint(usability["risk_level"]))
			if riskRank[candidateRisk] > riskRank[riskLevel] || riskLevel == "" {
				riskLevel = candidateRisk
			}
			usabilityMethods = appendUniqueStrings(usabilityMethods, methodSeen, usability["methods"])
			usabilityTasks = appendUniqueStrings(usabilityTasks, taskSeen, usability["critical_tasks"])
			usabilityCriteria = appendUniqueStrings(usabilityCriteria, criteriaSeen, usability["success_criteria"])
			smoothnessIDs = appendUniqueStrings(smoothnessIDs, smoothnessSeen, usability["smoothness_acceptance_ids"])
			if configured, ok := usability["performance_budgets"].(map[string]any); ok {
				budgetRowsSeen = true
				candidate := map[string]float64{}
				for _, field := range []string{"inp_ms", "long_task_ms", "cls", "animation_dropped_frame_pct", "bundle_delta_kb"} {
					if value, valid := designJSONFloat(configured[field]); valid && value >= 0 {
						candidate[field] = value
					} else {
						budgetRowsValid = false
					}
				}
				for field, value := range candidate {
					current, exists := performanceBudgets[field]
					if !exists || value < current {
						performanceBudgets[field] = value
					}
				}
			}
			if required, ok := usability["human_review_required"].(bool); ok && required {
				humanReviewRequired = true
			}
		}
		for _, raw := range profile["targets"].([]any) {
			target, ok := raw.(map[string]any)
			if !ok {
				continue
			}
			targetID := strings.TrimSpace(fmt.Sprint(target["id"]))
			responsiveRow := map[string]any{
				"id":                targetID,
				"profile_id":        profileID,
				"label":             target["label"],
				"target":            cloneJSONValue(target["target"]),
				"review_width_px":   target["review_width_px"],
				"state":             "default",
				"adaptation":        target["adaptation"],
				"stretch_behavior":  target["stretch_behavior"],
				"overflow_behavior": target["overflow_behavior"],
				"decision_ids":      designAnyStringList(decisionIDsFor("responsive_matrix", target)),
			}
			responsive = append(responsive, responsiveRow)
			profileResponsive = append(profileResponsive, responsiveRow)
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

		profileKey := strings.ToUpper(profileID)
		surfaceID := "DH-SURFACE-" + profileKey + "-001"
		componentIDs := []string{}
		surfaceDecisionIDs := []string{}
		surfaceDecisionSeen := map[string]bool{}
		appendRowDecisions := func(rows []any) {
			for _, raw := range rows {
				row, ok := raw.(map[string]any)
				if !ok {
					continue
				}
				surfaceDecisionIDs = appendUniqueStrings(surfaceDecisionIDs, surfaceDecisionSeen, row["decision_ids"])
			}
		}
		for _, raw := range profileComponents {
			row := raw.(map[string]any)
			componentIDs = append(componentIDs, strings.TrimSpace(fmt.Sprint(row["id"])))
		}
		appendRowDecisions(profileComponents)
		for _, field := range []string{"interaction_matrix", "editing_matrix", "data_state_matrix", "accessibility_matrix", "navigation_matrix", "content_matrix"} {
			appendRowDecisions(profileMatrices[field])
		}
		appendRowDecisions(profileResponsive)
		appendRowDecisions(profileMotion)
		surfaceCatalog = append(surfaceCatalog, map[string]any{
			"id":            surfaceID,
			"profile_id":    profileID,
			"name":          strings.TrimSpace(fmt.Sprint(profile["label"])),
			"kind":          profileID,
			"entrypoint_id": "EP-" + profileKey + "-001",
			"source_refs":   designAnyStringList(projectSourceRefs),
			"specimen_ids":  designAnyStringList(profileSpecimenIDs),
			"component_ids": designAnyStringList(componentIDs),
			"decision_ids":  designAnyStringList(surfaceDecisionIDs),
		})

		type scenarioSource struct {
			field string
			rows  []any
		}
		sources := []scenarioSource{
			{"interaction_ids", profileMatrices["interaction_matrix"]},
			{"editing_ids", profileMatrices["editing_matrix"]},
			{"data_state_ids", profileMatrices["data_state_matrix"]},
			{"accessibility_ids", profileMatrices["accessibility_matrix"]},
			{"navigation_ids", profileMatrices["navigation_matrix"]},
			{"content_ids", profileMatrices["content_matrix"]},
			{"responsive_ids", profileResponsive},
			{"motion_transition_ids", profileMotion},
		}
		scenarioCount := 0
		for _, source := range sources {
			if len(source.rows) > scenarioCount {
				scenarioCount = len(source.rows)
			}
		}
		for index := 0; index < scenarioCount; index++ {
			scenario := map[string]any{
				"id":         fmt.Sprintf("DH-SCENARIO-%s-%03d", profileKey, index+1),
				"surface_id": surfaceID,
				"required":   true,
			}
			selectedRows := make([]map[string]any, 0, len(sources))
			scenarioDecisionIDs := []string{}
			scenarioDecisionSeen := map[string]bool{}
			for _, source := range sources {
				row := source.rows[index%len(source.rows)].(map[string]any)
				selectedRows = append(selectedRows, row)
				scenario[source.field] = designAnyStringList([]string{strings.TrimSpace(fmt.Sprint(row["id"]))})
				scenarioDecisionIDs = appendUniqueStrings(scenarioDecisionIDs, scenarioDecisionSeen, row["decision_ids"])
			}
			interaction := selectedRows[0]
			dataState := selectedRows[2]
			stateRow := func(name string) map[string]any {
				for _, raw := range profileMatrices["data_state_matrix"] {
					row := raw.(map[string]any)
					if strings.EqualFold(strings.TrimSpace(fmt.Sprint(row["state"])), name) {
						return row
					}
				}
				return dataState
			}
			successState := stateRow("populated")
			transientState := stateRow("partial")
			unavailableState := stateRow("unavailable")
			branchStateIDs := []string{}
			branchStateSeen := map[string]bool{}
			for _, row := range []map[string]any{dataState, successState, transientState, unavailableState} {
				rowID := strings.TrimSpace(fmt.Sprint(row["id"]))
				if rowID == "" || branchStateSeen[rowID] {
					continue
				}
				branchStateSeen[rowID] = true
				branchStateIDs = append(branchStateIDs, rowID)
				scenarioDecisionIDs = appendUniqueStrings(scenarioDecisionIDs, scenarioDecisionSeen, row["decision_ids"])
			}
			scenario["data_state_ids"] = designAnyStringList(branchStateIDs)
			accessibility := selectedRows[3]
			navigation := selectedRows[4]
			responsiveRow := selectedRows[6]
			focusCheckpoint := strings.TrimSpace(fmt.Sprint(accessibility["focus_order"]))
			announcementCheckpoint := strings.Join(stringList(accessibility["announcements"]), " ")
			recoveryCheckpoint := strings.TrimSpace(fmt.Sprint(navigation["interruption_recovery"]))
			scenario["name"] = fmt.Sprintf(
				"%s: %s via %s at %s",
				strings.TrimSpace(fmt.Sprint(profile["label"])),
				strings.TrimSpace(fmt.Sprint(dataState["state"])),
				strings.TrimSpace(fmt.Sprint(interaction["input"])),
				strings.TrimSpace(fmt.Sprint(responsiveRow["label"])),
			)
			scenario["interaction_script"] = map[string]any{
				"preconditions": designAnyStringList([]string{
					fmt.Sprintf(
						"Render %s at %s with %s.",
						surfaceID,
						strings.TrimSpace(fmt.Sprint(responsiveRow["label"])),
						strings.TrimRight(strings.TrimSpace(fmt.Sprint(dataState["data_condition"])), " .!?"),
					),
					fmt.Sprintf(
						"Begin in the %s state before %s.",
						strings.TrimSpace(fmt.Sprint(dataState["state"])),
						strings.TrimRight(strings.TrimSpace(fmt.Sprint(interaction["trigger"])), " .!?"),
					),
				}),
				"start_state_id": strings.TrimSpace(fmt.Sprint(dataState["id"])),
				"steps": []any{map[string]any{
					"input":             strings.TrimSpace(fmt.Sprint(interaction["input"])),
					"action":            strings.TrimSpace(fmt.Sprint(interaction["trigger"])),
					"expected_feedback": strings.TrimSpace(fmt.Sprint(interaction["immediate_feedback"])),
				}},
				"branches": []any{
					map[string]any{
						"conditions":        designAnyStringList([]string{"success"}),
						"setup":             "Complete the action once without interruption: " + strings.TrimSpace(fmt.Sprint(interaction["trigger"])),
						"expected_state_id": strings.TrimSpace(fmt.Sprint(successState["id"])),
						"expected_feedback": strings.TrimSpace(fmt.Sprint(successState["expectation"])),
						"focus_behavior":    focusCheckpoint,
						"announcement":      "Success: " + announcementCheckpoint,
						"continuation":      strings.TrimSpace(fmt.Sprint(navigation["destination"])),
					},
					map[string]any{
						"conditions":        designAnyStringList([]string{"failure", "timeout"}),
						"setup":             "Force the action to fail or exceed its timeout: " + strings.TrimSpace(fmt.Sprint(interaction["trigger"])),
						"expected_state_id": strings.TrimSpace(fmt.Sprint(unavailableState["id"])),
						"expected_feedback": strings.TrimSpace(fmt.Sprint(unavailableState["expectation"])),
						"focus_behavior":    focusCheckpoint,
						"announcement":      "Failure or timeout: " + announcementCheckpoint,
						"continuation":      recoveryCheckpoint,
					},
					map[string]any{
						"conditions":        designAnyStringList([]string{"cancel"}),
						"setup":             "Cancel the action before completion: " + strings.TrimSpace(fmt.Sprint(interaction["trigger"])),
						"expected_state_id": strings.TrimSpace(fmt.Sprint(dataState["id"])),
						"expected_feedback": strings.TrimSpace(fmt.Sprint(dataState["expectation"])),
						"focus_behavior":    focusCheckpoint,
						"announcement":      "Cancellation: " + announcementCheckpoint,
						"continuation":      strings.TrimSpace(fmt.Sprint(navigation["back_behavior"])),
					},
					map[string]any{
						"conditions":        designAnyStringList([]string{"retry", "duplicate", "out_of_order"}),
						"setup":             "Retry or repeat the action and resolve completions out of order: " + strings.TrimSpace(fmt.Sprint(interaction["trigger"])),
						"expected_state_id": strings.TrimSpace(fmt.Sprint(transientState["id"])),
						"expected_feedback": strings.TrimSpace(fmt.Sprint(transientState["expectation"])),
						"focus_behavior":    focusCheckpoint,
						"announcement":      "Retry, duplicate, or out-of-order completion: " + announcementCheckpoint,
						"continuation":      recoveryCheckpoint,
					},
				},
				"focus_checkpoint":        focusCheckpoint,
				"announcement_checkpoint": announcementCheckpoint,
				"completion_checkpoint":   strings.TrimSpace(fmt.Sprint(successState["expectation"])),
				"recovery_checkpoint":     recoveryCheckpoint,
			}
			rawScenario, _ := json.Marshal(selectedRows)
			scenarioText := strings.ToLower(string(rawScenario))
			risk := "low"
			for _, marker := range []string{"keyboard", "focus", "loading", "empty", "partial", "reduced", "overflow", "touch"} {
				if strings.Contains(scenarioText, marker) {
					risk = "medium"
					break
				}
			}
			for _, marker := range []string{"error", "offline", "permission", "destructive", "timeout", "failure", "recovery"} {
				if strings.Contains(scenarioText, marker) {
					risk = "high"
					break
				}
			}
			scenario["risk"] = risk
			scenario["decision_ids"] = designAnyStringList(scenarioDecisionIDs)
			scenarioMatrix = append(scenarioMatrix, scenario)
		}
	}
	handoff["component_contracts"] = components
	handoff["surface_catalog"] = surfaceCatalog
	handoff["scenario_matrix"] = scenarioMatrix
	for field, rows := range professionalMatrices {
		handoff[field] = rows
	}
	handoff["responsive_matrix"] = responsive
	handoff["motion_contract"] = map[string]any{
		"purpose":         strings.Join(motionPurposes, " "),
		"transitions":     motionTransitions,
		"reduced_motion":  strings.Join(reducedMotionRules, " "),
		"feedback_timing": feedbackTiming,
	}
	handoff["usability_validation"] = map[string]any{
		"risk_level":            riskLevel,
		"methods":               designAnyStringList(usabilityMethods),
		"critical_tasks":        designAnyStringList(usabilityTasks),
		"success_criteria":      designAnyStringList(usabilityCriteria),
		"human_review_required": humanReviewRequired,
	}
	if len(smoothnessIDs) > 0 {
		handoff["usability_validation"].(map[string]any)["smoothness_acceptance_ids"] = designAnyStringList(smoothnessIDs)
	}
	if budgetRowsSeen && budgetRowsValid && len(performanceBudgets) == 5 {
		budgetPayload := map[string]any{}
		for key, value := range performanceBudgets {
			budgetPayload[key] = value
		}
		handoff["usability_validation"].(map[string]any)["performance_budgets"] = budgetPayload
	}
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
	if diagnostics := previewManifestDiagnostics(manifest, directionIDs, true, "html-primary"); len(diagnostics) > 0 {
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
	if diagnostics := lintDesignPreviewFile(tempPath, "structural"); len(diagnostics) > 0 {
		return "", fmt.Errorf("rendered design preview is not ready: %s", joinDiagnostics(diagnostics))
	}
	return outPath, writeTextAtomic(outPath, content)
}

func renderPreviewDirectionIDs(content string, directionIDs []string) string {
	sourceIDs := []string{"direction-main"}
	sentinels := []string{"__SPECIFY_DIRECTION_SLOT_MAIN__"}
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
	legacyDesignSystem, hasLegacy := frontMatter["design_system"].(map[string]any)
	designChange, hasChange := frontMatter["design_change"].(map[string]any)
	if hasLegacy && hasChange {
		return designDocument{}, fmt.Errorf("%s: define exactly one of design_change or design_system", source)
	}
	ds := legacyDesignSystem
	if hasChange {
		ds = designChange
	}
	if !hasLegacy && !hasChange {
		return designDocument{}, fmt.Errorf("%s: missing design_change or legacy design_system mapping", source)
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
	if (strings.HasPrefix(value, "[") && strings.HasSuffix(value, "]")) ||
		(strings.HasPrefix(value, "{") && strings.HasSuffix(value, "}")) {
		var parsed any
		if err := json.Unmarshal([]byte(value), &parsed); err == nil {
			return parsed
		}
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

func uniquePrefixedStringList(value any, prefix string, limit int) ([]string, bool) {
	if !isNonEmptyStringList(value, false) {
		return nil, false
	}
	values := stringList(value)
	if limit >= 0 && len(values) > limit {
		return nil, false
	}
	seen := map[string]bool{}
	for _, value := range values {
		if (prefix != "" && !strings.HasPrefix(value, prefix)) || seen[value] {
			return nil, false
		}
		seen[value] = true
	}
	return values, true
}

func loadProfessionalSkillCatalogRefs() (map[string]string, error) {
	path, err := locateTemplate(filepath.Join("ui-professional-skills", "catalog.json"))
	if err != nil {
		return nil, err
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var payload map[string]any
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, err
	}
	if strings.TrimSpace(fmt.Sprint(payload["catalog_id"])) != uiProfessionalSkillCatalog {
		return nil, fmt.Errorf("unexpected UI professional skill catalog ID")
	}
	skills, ok := payload["skills"].([]any)
	if !ok {
		return nil, fmt.Errorf("UI professional skill catalog skills must be a list")
	}
	refs := map[string]string{}
	for _, rawSkill := range skills {
		skill, ok := rawSkill.(map[string]any)
		if !ok {
			return nil, fmt.Errorf("UI professional skill catalog entries must be objects")
		}
		skillID := strings.TrimSpace(fmt.Sprint(skill["id"]))
		reference := strings.TrimSpace(fmt.Sprint(skill["ref"]))
		if skillID == "" || skillID == "<nil>" || reference == "" || reference == "<nil>" || refs[skillID] != "" {
			return nil, fmt.Errorf("UI professional skill catalog entries require unique IDs and references")
		}
		refs[skillID] = reference
	}
	return refs, nil
}

func validateProfessionalSkillRoute(ds map[string]any, diagnostics *[]designDiagnostic, ready bool) {
	raw, exists := ds["professional_skill_route"]
	if !exists || raw == nil {
		// Preserve compatibility with contracts approved before this shared
		// progressive-disclosure router existed. New scaffolds always include it.
		return
	}
	path := "design_system.professional_skill_route"
	route, ok := raw.(map[string]any)
	if !ok {
		addDesignDiagnostic(diagnostics, "invalid-professional-skill-route", "professional_skill_route must be a mapping", path)
		return
	}
	var problems []string
	if strings.TrimSpace(fmt.Sprint(route["catalog_version"])) != uiProfessionalSkillCatalog {
		problems = append(problems, "catalog_version must equal "+uiProfessionalSkillCatalog)
	}
	status := strings.TrimSpace(fmt.Sprint(route["status"]))
	if status != "unresolved" && status != "question-required" && status != "resolved" {
		problems = append(problems, "status must be unresolved, question-required, or resolved")
	}
	domainID := ""
	if route["domain_skill_id"] != nil {
		domainID = strings.TrimSpace(fmt.Sprint(route["domain_skill_id"]))
		if !strings.HasPrefix(domainID, "domain-") {
			problems = append(problems, "domain_skill_id must be null or a domain-* ID")
		}
	}
	styleID := ""
	if route["style_skill_id"] != nil {
		styleID = strings.TrimSpace(fmt.Sprint(route["style_skill_id"]))
		if !strings.HasPrefix(styleID, "style-") {
			problems = append(problems, "style_skill_id must be null or a style-* ID")
		}
	}
	specialistIDs, specialistsOK := uniquePrefixedStringList(route["specialist_skill_ids"], "specialist-", 2)
	if !specialistsOK {
		problems = append(problems, "specialist_skill_ids must contain zero to two unique specialist-* IDs")
	}
	signals, signalsOK := route["matched_signals"].(map[string]any)
	if signalsOK {
		for skillID, rawSignals := range signals {
			if strings.TrimSpace(skillID) == "" || !isNonEmptyStringList(rawSignals, true) {
				signalsOK = false
				break
			}
		}
	}
	if !signalsOK {
		problems = append(problems, "matched_signals must map skill IDs to non-empty signal strings")
	}
	loadedRefs, loadedOK := uniquePrefixedStringList(route["loaded_refs"], "", 4)
	if !loadedOK {
		problems = append(problems, "loaded_refs must contain at most four unique references")
	}
	unresolved, unresolvedOK := uniquePrefixedStringList(route["unresolved_candidates"], "", -1)
	if !unresolvedOK {
		problems = append(problems, "unresolved_candidates must contain unique skill IDs")
	}
	catalogRefs, catalogErr := loadProfessionalSkillCatalogRefs()
	if catalogErr != nil {
		problems = append(problems, "the UI professional skill catalog is unavailable or invalid")
	} else if len(problems) == 0 {
		referencedIDs := append([]string{}, specialistIDs...)
		if domainID != "" {
			referencedIDs = append(referencedIDs, domainID)
		}
		if styleID != "" {
			referencedIDs = append(referencedIDs, styleID)
		}
		referencedIDs = append(referencedIDs, unresolved...)
		for skillID := range signals {
			referencedIDs = append(referencedIDs, skillID)
		}
		var unknownIDs []string
		seenUnknown := map[string]bool{}
		for _, skillID := range referencedIDs {
			if catalogRefs[skillID] == "" && !seenUnknown[skillID] {
				unknownIDs = append(unknownIDs, skillID)
				seenUnknown[skillID] = true
			}
		}
		if len(unknownIDs) > 0 {
			sort.Strings(unknownIDs)
			problems = append(problems, "route references unknown skill IDs: "+strings.Join(unknownIDs, ", "))
		}
	}
	if len(problems) > 0 {
		addDesignDiagnostic(diagnostics, "invalid-professional-skill-route", strings.Join(problems, "; "), path)
		return
	}
	if !ready {
		return
	}
	expectedRefs := 1 + len(specialistIDs)
	if styleID != "" {
		expectedRefs++
	}
	if domainID != "" {
		selectedIDs := []string{domainID}
		if styleID != "" {
			selectedIDs = append(selectedIDs, styleID)
		}
		selectedIDs = append(selectedIDs, specialistIDs...)
		expectedLoadedRefs := make([]string, 0, len(selectedIDs))
		for _, skillID := range selectedIDs {
			expectedLoadedRefs = append(expectedLoadedRefs, catalogRefs[skillID])
		}
		if !reflect.DeepEqual(loadedRefs, expectedLoadedRefs) {
			addDesignDiagnostic(diagnostics, "professional-skill-route-ref-mismatch", "loaded_refs must exactly match the selected domain, style, and specialists", path+".loaded_refs")
		}
	}
	if status != "resolved" || domainID == "" || len(loadedRefs) != expectedRefs || len(unresolved) > 0 {
		addDesignDiagnostic(diagnostics, "unresolved-professional-skill-route", "ready design must resolve one domain, optional one style, zero to two specialists, and the exact selected references", path)
	}
}

func validateStyleAuthority(ds map[string]any, diagnostics *[]designDiagnostic, ready bool) {
	raw, exists := ds["style_authority"]
	schema := strings.TrimSpace(fmt.Sprint(ds["schema"]))
	path := "design_system.style_authority"
	if !exists || raw == nil {
		if schema == designChangeSchema {
			addDesignDiagnostic(diagnostics, "invalid-style-authority", "current design changes require style_authority", path)
		}
		return
	}
	authority, ok := raw.(map[string]any)
	expectedFields := []string{
		"mode", "scope_level", "source_refs", "protected_surfaces",
		"allowed_style_delta_surfaces", "authorization_source",
	}
	if !ok || len(authority) != len(expectedFields) {
		addDesignDiagnostic(diagnostics, "invalid-style-authority", "style_authority must contain the current exact fields", path)
		return
	}
	for _, field := range expectedFields {
		if _, present := authority[field]; !present {
			addDesignDiagnostic(diagnostics, "invalid-style-authority", "style_authority must contain the current exact fields", path)
			return
		}
	}
	mode := strings.TrimSpace(fmt.Sprint(authority["mode"]))
	if authority["mode"] == nil {
		mode = ""
	}
	scopeLevel := ""
	if authority["scope_level"] != nil {
		scopeLevel = strings.TrimSpace(fmt.Sprint(authority["scope_level"]))
	}
	problems := []string{}
	validModes := map[string]bool{
		"unresolved": true, "greenfield": true, "inherit-existing": true,
		"page-overhaul-authorized": true,
	}
	if !validModes[mode] {
		problems = append(problems, "mode is invalid")
	}
	if scopeLevel != "" && scopeLevel != "feature-partial" && scopeLevel != "page" {
		problems = append(problems, "scope_level must be null, feature-partial, or page")
	}
	lists := map[string][]string{}
	for _, field := range []string{"source_refs", "protected_surfaces", "allowed_style_delta_surfaces"} {
		values := []any{}
		listOK := true
		switch rawValues := authority[field].(type) {
		case []any:
			values = rawValues
		case []string:
			values = make([]any, 0, len(rawValues))
			for _, value := range rawValues {
				values = append(values, value)
			}
		default:
			listOK = false
		}
		seen := map[string]bool{}
		normalized := []string{}
		if !listOK {
			problems = append(problems, field+" must contain unique nonblank strings")
			lists[field] = normalized
			continue
		}
		valid := true
		for _, value := range values {
			text, stringOK := value.(string)
			text = strings.TrimSpace(text)
			if !stringOK || text == "" || seen[text] {
				valid = false
				break
			}
			seen[text] = true
			normalized = append(normalized, text)
		}
		if !valid {
			problems = append(problems, field+" must contain unique nonblank strings")
			normalized = []string{}
		}
		lists[field] = normalized
	}
	authorization := ""
	authorizationPresent := authority["authorization_source"] != nil
	if authorizationPresent {
		value, stringOK := authority["authorization_source"].(string)
		authorization = strings.TrimSpace(value)
		if !stringOK || authorization == "" {
			problems = append(problems, "authorization_source must be null or a nonblank string")
		}
	}
	if len(problems) > 0 {
		addDesignDiagnostic(diagnostics, "invalid-style-authority", strings.Join(problems, "; "), path)
		return
	}
	if !ready {
		return
	}

	violations := []string{}
	protected := stringSliceSet(lists["protected_surfaces"])
	allowed := stringSliceSet(lists["allowed_style_delta_surfaces"])
	baselineGuards := []string{"global-shell", "shared-components"}
	styleSkillID := ""
	if route, routeOK := ds["professional_skill_route"].(map[string]any); routeOK && route["style_skill_id"] != nil {
		styleSkillID = strings.TrimSpace(fmt.Sprint(route["style_skill_id"]))
	}
	changeType := strings.TrimSpace(fmt.Sprint(ds["change_type"]))
	declaredSurfaces := map[string]bool{}
	if scope, scopeOK := ds["scope"].(map[string]any); scopeOK {
		declaredSurfaces = stringSliceSet(stringList(scope["surfaces"]))
	}
	hasBaselineGuards := true
	for _, guard := range baselineGuards {
		if !protected[guard] {
			hasBaselineGuards = false
		}
	}
	switch mode {
	case "unresolved":
		violations = append(violations, "ready design must resolve style authority")
	case "greenfield":
		if schema == designChangeSchema && changeType != "greenfield" {
			violations = append(violations, "greenfield style authority requires change_type greenfield")
		}
		if authorizationPresent {
			violations = append(violations, "greenfield cannot claim overhaul authorization")
		}
	case "inherit-existing":
		if scopeLevel != "feature-partial" {
			violations = append(violations, "inherit-existing requires feature-partial scope")
		}
		if len(lists["source_refs"]) == 0 {
			violations = append(violations, "inherit-existing requires live UI source_refs")
		}
		if !hasBaselineGuards {
			violations = append(violations, "inherit-existing must protect global-shell and shared-components")
		}
		if len(allowed) > 0 {
			violations = append(violations, "inherit-existing cannot allow a style delta")
		}
		if authorizationPresent {
			violations = append(violations, "inherit-existing cannot claim overhaul authorization")
		}
		if styleSkillID != "" {
			violations = append(violations, "inherit-existing requires style_skill_id null")
		}
	case "page-overhaul-authorized":
		if changeType != "overhaul" {
			violations = append(violations, "page overhaul style authority requires change_type overhaul")
		}
		if scopeLevel != "page" {
			violations = append(violations, "page overhaul style authority requires page scope")
		}
		if len(lists["source_refs"]) == 0 {
			violations = append(violations, "page overhaul requires live UI source_refs")
		}
		if !hasBaselineGuards {
			violations = append(violations, "page overhaul must protect global-shell and shared-components")
		}
		allowedValid := len(allowed) > 0
		for surface := range allowed {
			if !declaredSurfaces[surface] {
				allowedValid = false
			}
			if surface == "global-shell" || surface == "shared-components" {
				violations = append(violations, "global shell and shared components cannot be style delta surfaces")
			}
		}
		if !allowedValid {
			violations = append(violations, "allowed style delta surfaces must be exact declared page surfaces")
		}
		if !authorizationPresent || authorization == "" {
			violations = append(violations, "page overhaul requires explicit authorization_source")
		}
	}
	if len(violations) > 0 {
		addDesignDiagnostic(diagnostics, "style-authority-violation", strings.Join(violations, "; "), path)
	}
}

func validateDesignSystem(doc designDocument, diagnostics *[]designDiagnostic) {
	ds := doc.DesignSystem
	schema := strings.TrimSpace(fmt.Sprint(ds["schema"]))
	if schema != "spec-kit-design-v1" && schema != designChangeSchema {
		addDesignDiagnostic(diagnostics, "invalid-schema", "schema must equal spec-kit-ui-design-change-v1 or legacy spec-kit-design-v1", "design_change.schema")
	}
	if schema == designChangeSchema {
		validateDesignChangeMetadata(ds, diagnostics)
		verification, ok := ds["verification"].(map[string]any)
		if !ok {
			addDesignDiagnostic(diagnostics, "missing-source-continuity", "design_change.verification must contain source_continuity", "design_change.verification.source_continuity")
		} else if err := validateDesignSourceContinuity(verification["source_continuity"], "design_change.verification.source_continuity", false); err != nil {
			addDesignDiagnostic(diagnostics, "invalid-source-continuity", err.Error(), "design_change.verification.source_continuity")
		}
	}
	validateProfessionalSkillRoute(ds, diagnostics, false)
	validateStyleAuthority(ds, diagnostics, false)
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

func validateDesignChangeMetadata(change map[string]any, diagnostics *[]designDiagnostic) {
	changeID := strings.TrimSpace(fmt.Sprint(change["id"]))
	if !designChangeIDRE.MatchString(changeID) {
		addDesignDiagnostic(diagnostics, "invalid-design-change-id", "design_change.id must use UD- followed by at least four digits", "design_change.id")
	}
	if strings.TrimSpace(fmt.Sprint(change["title"])) == "" {
		addDesignDiagnostic(diagnostics, "missing-design-change-title", "design_change.title must be non-empty", "design_change.title")
	}
	changeType := strings.ToLower(strings.TrimSpace(fmt.Sprint(change["change_type"])))
	validTypes := map[string]bool{"greenfield": true, "preserve": true, "overhaul": true, "extension": true}
	if !validTypes[changeType] {
		addDesignDiagnostic(diagnostics, "invalid-design-change-type", "design_change.change_type must be greenfield, preserve, overhaul, or extension", "design_change.change_type")
	}
	scope, ok := change["scope"].(map[string]any)
	if !ok {
		addDesignDiagnostic(diagnostics, "invalid-design-change-scope", "design_change.scope must be a mapping", "design_change.scope")
	} else {
		surfaces, ok := scope["surfaces"].([]any)
		if !ok || len(surfaces) == 0 {
			addDesignDiagnostic(diagnostics, "invalid-design-change-surfaces", "design_change.scope.surfaces must contain stable path-like identifiers", "design_change.scope.surfaces")
		} else {
			for _, rawSurface := range surfaces {
				if !designChangeScopeRE.MatchString(strings.TrimSpace(fmt.Sprint(rawSurface))) {
					addDesignDiagnostic(diagnostics, "invalid-design-change-surfaces", "design_change.scope.surfaces must contain stable path-like identifiers", "design_change.scope.surfaces")
					break
				}
			}
		}
		for _, field := range []string{"entrypoints", "states", "platforms"} {
			if _, ok := scope[field].([]any); !ok {
				addDesignDiagnostic(diagnostics, "invalid-design-change-scope", "design_change.scope."+field+" must be a list", "design_change.scope."+field)
			}
		}
	}
	if _, ok := change["baseline_refs"].([]any); !ok {
		addDesignDiagnostic(diagnostics, "invalid-design-change-baselines", "design_change.baseline_refs must be a list", "design_change.baseline_refs")
	}
	relationships, ok := change["relationships"].(map[string]any)
	if !ok {
		addDesignDiagnostic(diagnostics, "invalid-design-change-relationships", "design_change.relationships must be a mapping", "design_change.relationships")
	} else {
		for _, field := range []string{"supersedes", "depends_on", "conflicts_with"} {
			if _, ok := relationships[field].([]any); !ok {
				addDesignDiagnostic(diagnostics, "invalid-design-change-relationships", "design_change.relationships."+field+" must be a list", "design_change.relationships."+field)
			}
		}
		iterationRaw := relationships["iteration_of"]
		if iterationRaw != nil {
			iterationOf, valid := iterationRaw.(string)
			iterationOf = strings.TrimSpace(iterationOf)
			if !valid || !designChangeIDRE.MatchString(iterationOf) || iterationOf == strings.TrimSpace(fmt.Sprint(change["id"])) {
				addDesignDiagnostic(diagnostics, "invalid-design-change-iteration", "design_change.relationships.iteration_of must be null or a different canonical UD-* ID", "design_change.relationships.iteration_of")
			} else if !designStringContains(stringList(relationships["supersedes"]), iterationOf) {
				addDesignDiagnostic(diagnostics, "invalid-design-change-iteration", "an iteration source must also appear in relationships.supersedes", "design_change.relationships.iteration_of")
			}
		}
	}
	constraints, ok := change["constraints"].(map[string]any)
	if !ok {
		addDesignDiagnostic(diagnostics, "invalid-design-change-constraints", "design_change.constraints must be a mapping", "design_change.constraints")
	} else {
		for _, field := range []string{"must_preserve", "may_adapt", "must_not"} {
			if _, ok := constraints[field].([]any); !ok {
				addDesignDiagnostic(diagnostics, "invalid-design-change-constraints", "design_change.constraints."+field+" must be a list", "design_change.constraints."+field)
			}
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

func validateDesignSourceContinuity(value any, path string, ready bool) error {
	continuity, ok := value.(map[string]any)
	if !ok {
		return fmt.Errorf("%s must be an object", path)
	}
	if ready {
		if err := validateQuickSourceContinuity(continuity); err != nil {
			return errors.New(strings.Replace(err.Error(), "ui_confirmation.source_continuity", path, 1))
		}
		return nil
	}
	if err := validateQuickContinuityKnownFields(
		continuity,
		path,
		"schema", "applicability", "mode", "reason", "coverage", "authority_refs",
		"surface_bindings", "action_bindings", "asset_bindings", "unresolved_gaps",
	); err != nil {
		return err
	}
	if stringValue(continuity["schema"]) != "spec-kit-ui-source-continuity-v1" {
		return fmt.Errorf("%s.schema must be spec-kit-ui-source-continuity-v1", path)
	}
	if _, exists := continuity["reason"]; !exists {
		return fmt.Errorf("%s.reason is required", path)
	}
	coverage := mapValue(continuity["coverage"])
	if coverage == nil {
		return fmt.Errorf("%s.coverage must be an object", path)
	}
	if err := validateQuickContinuityKnownFields(coverage, path+".coverage", "surface_ids", "interaction_ids", "component_ids"); err != nil {
		return err
	}
	coverageSurfaces, coverageSurfacesOK := quickContinuityStringList(coverage["surface_ids"])
	coverageInteractions, coverageInteractionsOK := quickContinuityStringList(coverage["interaction_ids"])
	coverageComponents, coverageComponentsOK := quickContinuityStringList(coverage["component_ids"])
	applicability := strings.TrimSpace(stringValue(continuity["applicability"]))
	mode := strings.TrimSpace(stringValue(continuity["mode"]))
	if !quickContains([]string{"not-assessed", "not-applicable", "required"}, applicability) {
		return fmt.Errorf("%s.applicability is unsupported", path)
	}
	if !quickContains([]string{"none", "reference-grounded", "live-product", "implementation-backed", "mixed"}, mode) {
		return fmt.Errorf("%s.mode is unsupported", path)
	}
	authorityRefs, authorityOK := quickContinuityStringList(continuity["authority_refs"])
	surfaces, surfacesOK := quickContinuityRows(continuity["surface_bindings"])
	actions, actionsOK := quickContinuityRows(continuity["action_bindings"])
	assets, assetsOK := quickContinuityRows(continuity["asset_bindings"])
	gaps, gapsOK := quickContinuityStringList(continuity["unresolved_gaps"])
	if !coverageSurfacesOK || !coverageInteractionsOK || !coverageComponentsOK || !authorityOK || !surfacesOK || !actionsOK || !assetsOK || !gapsOK {
		return fmt.Errorf("%s refs, bindings, and unresolved_gaps must use the declared array shapes", path)
	}
	if applicability == "required" && mode == "none" {
		return fmt.Errorf("%s.mode must identify the governing source mode when required", path)
	}
	if applicability != "required" {
		if mode != "none" {
			return fmt.Errorf("%s.mode must be none when source continuity is not required", path)
		}
		if len(coverageSurfaces)+len(coverageInteractions)+len(coverageComponents)+len(authorityRefs)+len(surfaces)+len(actions)+len(assets)+len(gaps) != 0 {
			return fmt.Errorf("%s must keep source arrays empty when source continuity is not required", path)
		}
		if applicability == "not-applicable" && strings.TrimSpace(stringValue(continuity["reason"])) == "" {
			return fmt.Errorf("%s.reason is required when not-applicable", path)
		}
	}
	return validateMigrationContract(continuity, path)
}

func validateDesignHandoffSourceContinuityCoverage(handoff map[string]any, path string) error {
	continuity := mapValue(handoff["source_continuity"])
	if continuity == nil || strings.TrimSpace(stringValue(continuity["applicability"])) != "required" {
		return nil
	}
	coverage := mapValue(continuity["coverage"])
	if coverage == nil {
		return fmt.Errorf("%s.coverage must be an object", path)
	}
	checks := []struct {
		field      string
		collection string
	}{
		{field: "surface_ids", collection: "surface_catalog"},
		{field: "interaction_ids", collection: "interaction_matrix"},
		{field: "component_ids", collection: "component_contracts"},
	}
	for _, check := range checks {
		declared, ok := quickContinuityStringList(coverage[check.field])
		if !ok {
			return fmt.Errorf("%s.coverage.%s must be an array", path, check.field)
		}
		rows, ok := quickContinuityRows(handoff[check.collection])
		if !ok {
			return fmt.Errorf("%s cannot verify %s against %s", path, check.field, check.collection)
		}
		if err := validateQuickContinuityCoverage(path+".coverage."+check.field, declared, rows, "id"); err != nil {
			return err
		}
	}
	return validateMigrationComponentBindings(continuity, handoff["component_contracts"])
}

func validateDesignReadiness(doc designDocument, diagnostics *[]designDiagnostic) {
	ds := doc.DesignSystem
	validateProfessionalSkillRoute(ds, diagnostics, true)
	validateStyleAuthority(ds, diagnostics, true)
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
	if strings.TrimSpace(fmt.Sprint(ds["schema"])) == designChangeSchema {
		verification, ok := ds["verification"].(map[string]any)
		if !ok {
			addDesignDiagnostic(diagnostics, "missing-design-professional-contract", "design_change.verification must carry the professional UI contract", "design_change.verification")
		} else {
			if err := validateDesignSourceContinuity(
				verification["source_continuity"],
				"design_change.verification.source_continuity",
				true,
			); err != nil {
				addDesignDiagnostic(diagnostics, "invalid-source-continuity", err.Error(), "design_change.verification.source_continuity")
			}
			var handoffIDs []string
			if ok {
				if approval, approvalOK := ds["approval"].(map[string]any); approvalOK {
					handoffIDs = stringList(approval["handoff_contract_ids"])
				}
			}
			validateDesignProfessionalVerification(verification, manifestDecisionIDs(ds), handoffIDs, nil, diagnostics)
		}
	}
}

func validateDesignProfessionalVerification(verification map[string]any, decisionIDs, handoffContractIDs []string, immutableHandoff map[string]any, diagnostics *[]designDiagnostic) {
	knownDecisions := stringSliceSet(decisionIDs)
	frozenIDs := stringSliceSet(handoffContractIDs)
	seenIDs := map[string]bool{}
	fields := []string{"interaction_matrix", "editing_matrix", "data_state_matrix", "accessibility_matrix", "navigation_matrix", "content_matrix"}
	validateBoundID := func(row map[string]any, path string) {
		id := strings.TrimSpace(fmt.Sprint(row["id"]))
		if !canonicalHandoffIDRE.MatchString(id) || seenIDs[id] || (len(frozenIDs) > 0 && !frozenIDs[id]) {
			addDesignDiagnostic(diagnostics, "invalid-design-professional-contract-id", "professional contract IDs must be unique frozen DH-* values", path+".id")
		}
		seenIDs[id] = true
		decisions := stringList(row["decision_ids"])
		if len(decisions) == 0 || !stringSetContainsAll(knownDecisions, decisions) {
			addDesignDiagnostic(diagnostics, "invalid-design-professional-decision-binding", "professional contract decision_ids must reference approved DS-* decisions", path+".decision_ids")
		}
	}
	graphFields := []string{"surface_catalog", "scenario_matrix"}
	for _, field := range graphFields {
		rows, ok := verification[field].([]any)
		if !ok || len(rows) == 0 {
			addDesignDiagnostic(diagnostics, "missing-design-professional-contract", "verification."+field+" must be a non-empty list", "design_change.verification."+field)
			continue
		}
		for index, raw := range rows {
			row, ok := raw.(map[string]any)
			path := fmt.Sprintf("design_change.verification.%s[%d]", field, index)
			if !ok {
				addDesignDiagnostic(diagnostics, "invalid-design-professional-contract", field+" rows must be mappings", path)
				continue
			}
			validateBoundID(row, path)
			valid := true
			if field == "surface_catalog" {
				valid = nonEmpty(row["profile_id"]) && nonEmpty(row["name"]) && nonEmpty(row["kind"]) && nonEmpty(row["entrypoint_id"]) && isNonEmptyStringList(row["source_refs"], true) && isNonEmptyStringList(row["specimen_ids"], true) && isNonEmptyStringList(row["component_ids"], true)
			} else {
				risk := strings.TrimSpace(fmt.Sprint(row["risk"]))
				required, requiredOK := row["required"].(bool)
				valid = nonEmpty(row["surface_id"]) && nonEmpty(row["name"]) && (risk == "low" || risk == "medium" || risk == "high") && requiredOK && required && validDesignInteractionScript(row["interaction_script"], listToStringSet(row["data_state_ids"]))
				for _, refField := range []string{"interaction_ids", "editing_ids", "data_state_ids", "accessibility_ids", "navigation_ids", "content_ids", "responsive_ids", "motion_transition_ids"} {
					valid = valid && isNonEmptyStringList(row[refField], true)
				}
			}
			if !valid {
				addDesignDiagnostic(diagnostics, "incomplete-design-professional-contract", field+" row is missing executable graph fields", path)
			}
		}
	}
	for _, field := range fields {
		rows, ok := verification[field].([]any)
		if !ok || len(rows) == 0 {
			addDesignDiagnostic(diagnostics, "missing-design-professional-contract", "verification."+field+" must be a non-empty list", "design_change.verification."+field)
			continue
		}
		for index, raw := range rows {
			row, ok := raw.(map[string]any)
			path := fmt.Sprintf("design_change.verification.%s[%d]", field, index)
			if !ok {
				addDesignDiagnostic(diagnostics, "invalid-design-professional-contract", field+" rows must be mappings", path)
				continue
			}
			validateBoundID(row, path)
			if !validDesignProfessionalRow(field, row) {
				addDesignDiagnostic(diagnostics, "incomplete-design-professional-contract", field+" row is missing executable fields", path)
			}
		}
	}
	motion, motionOK := verification["motion_contract"].(map[string]any)
	if !motionOK || !validDesignMotionContract(motion) {
		addDesignDiagnostic(diagnostics, "incomplete-design-professional-contract", "verification.motion_contract requires purpose, transitions, reduced motion, and ordered feedback timing", "design_change.verification.motion_contract")
	} else {
		for index, raw := range motion["transitions"].([]any) {
			transition, ok := raw.(map[string]any)
			path := fmt.Sprintf("design_change.verification.motion_contract.transitions[%d]", index)
			if !ok {
				addDesignDiagnostic(diagnostics, "invalid-design-professional-contract", "motion transitions must be mappings", path)
				continue
			}
			validateBoundID(transition, path)
			if !validDesignMotionTransition(transition) {
				addDesignDiagnostic(diagnostics, "incomplete-design-professional-contract", "motion transition is missing executable fields", path)
			}
		}
	}
	usability, usabilityOK := verification["usability_validation"].(map[string]any)
	if !usabilityOK || !validDesignUsabilityValidation(usability) {
		addDesignDiagnostic(diagnostics, "incomplete-design-professional-contract", "verification.usability_validation requires risk, methods, tasks, success criteria, and human-review decision", "design_change.verification.usability_validation")
		if usabilityOK && strings.TrimSpace(fmt.Sprint(usability["risk_level"])) == "high" {
			if humanReview, ok := usability["human_review_required"].(bool); !ok || !humanReview {
				addDesignDiagnostic(diagnostics, "design-high-risk-human-review-required", "high-risk usability validation must require human review", "design_change.verification.usability_validation.human_review_required")
			}
		}
	}
	if immutableHandoff != nil {
		allFields := append(append([]string{}, graphFields...), fields...)
		for _, field := range append(allFields, "source_continuity", "motion_contract", "usability_validation") {
			if canonicalJSONSHA256(verification[field]) != canonicalJSONSHA256(immutableHandoff[field]) {
				addDesignDiagnostic(diagnostics, "design-professional-contract-drift", "verification."+field+" must exactly match the immutable approved handoff", "design_change.verification."+field)
			}
		}
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
		suffix := strings.ToLower(filepath.Ext(previewRef))
		if (suffix != ".html" && !designImageSuffixes[suffix]) || direction == "" {
			continue
		}
		previewPath := filepath.Join(filepath.Dir(doc.Source), filepath.FromSlash(previewRef))
		var diagnosticsPreview []designDiagnostic
		if suffix == ".html" {
			diagnosticsPreview = lintDesignPreviewFile(previewPath, "ready")
		} else {
			diagnosticsPreview = lintDesignImageBundle(previewPath, "ready")
		}
		if len(diagnosticsPreview) > 0 {
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
			sidecarField := "manifest_sha256"
			if field == "preview_sha256" {
				sidecarField = "html_sha256"
				if suffix != ".html" {
					sidecarField = "image_sha256"
				}
			}
			if strings.TrimSpace(fmt.Sprint(approval[field])) != strings.TrimSpace(fmt.Sprint(sidecar[sidecarField])) {
				addDesignDiagnostic(diagnostics, "approved-preview-digest-mismatch", "approval."+field+" must match the immutable preview sidecar", "design_system.approval."+field)
			}
		}
		if suffix != ".html" {
			for _, field := range []string{"visual_medium", "prompt_sha256", "inspection_owner"} {
				if strings.TrimSpace(fmt.Sprint(approval[field])) != strings.TrimSpace(fmt.Sprint(sidecar[field])) {
					addDesignDiagnostic(diagnostics, "approved-image-provenance-mismatch", "approval."+field+" must match the immutable image approval sidecar", "design_system.approval."+field)
				}
			}
			promptRef := strings.TrimSpace(fmt.Sprint(approval["prompt_ref"]))
			expectedPromptPath := strings.TrimSuffix(previewPath, filepath.Ext(previewPath)) + ".prompt.md"
			resolvedPromptPath := filepath.Join(filepath.Dir(doc.Source), filepath.FromSlash(promptRef))
			expectedAbs, expectedErr := filepath.Abs(expectedPromptPath)
			resolvedAbs, resolvedErr := filepath.Abs(resolvedPromptPath)
			if promptRef == "" || expectedErr != nil || resolvedErr != nil || filepath.Clean(expectedAbs) != filepath.Clean(resolvedAbs) {
				addDesignDiagnostic(diagnostics, "approved-image-prompt-reference-mismatch", "approval.prompt_ref must identify the exact adjacent image-generation prompt", "design_system.approval.prompt_ref")
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
		if strings.TrimSpace(fmt.Sprint(doc.DesignSystem["schema"])) == designChangeSchema {
			verification, verificationOK := doc.DesignSystem["verification"].(map[string]any)
			reproduction, reproductionOK := handoff["reproduction"].(map[string]any)
			if verificationOK && reproductionOK {
				validateDesignProfessionalVerification(
					verification,
					stringList(approval["decision_ids"]),
					stringList(approval["handoff_contract_ids"]),
					reproduction,
					diagnostics,
				)
			}
		}
		return
	}
	addDesignDiagnostic(diagnostics, "missing-local-approved-preview", "approved UI design requires a local immutable HTML or image round reference", "design_system.approval.visual_refs")
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

func previewVisualCollaborationDiagnostics(manifest map[string]any, expectedPrimaryMedium string) []designDiagnostic {
	var diagnostics []designDiagnostic
	collaboration, ok := manifest["visual_collaboration"].(map[string]any)
	if !ok {
		addDesignDiagnostic(&diagnostics, "preview-invalid-visual-collaboration", "preview manifest must freeze the live visual capability route", "manifest.visual_collaboration")
		return diagnostics
	}
	primaryMedium := strings.TrimSpace(fmt.Sprint(collaboration["primary_medium"]))
	imageGeneration := strings.TrimSpace(fmt.Sprint(collaboration["image_generation"]))
	imageInspection := strings.TrimSpace(fmt.Sprint(collaboration["image_inspection"]))
	imageEditing := strings.TrimSpace(fmt.Sprint(collaboration["image_editing"]))
	inspectionOwner := strings.TrimSpace(fmt.Sprint(collaboration["inspection_owner"]))
	promptStrategy := strings.TrimSpace(fmt.Sprint(collaboration["prompt_strategy"]))
	expectedOwner := "user"
	if imageInspection == "available" {
		expectedOwner = "agent-and-user"
	}
	validCapabilities := (imageInspection == "available" || imageInspection == "unavailable") && (imageEditing == "available" || imageEditing == "unavailable")
	validRoute := validCapabilities && inspectionOwner == expectedOwner && ((primaryMedium == "image-primary" && imageGeneration == "available" && promptStrategy == "image-generation") || (primaryMedium == "html-primary" && imageGeneration == "unavailable" && promptStrategy == "html-authoring"))
	if expectedPrimaryMedium != "" && primaryMedium != expectedPrimaryMedium {
		validRoute = false
	}
	if !validRoute {
		addDesignDiagnostic(&diagnostics, "preview-invalid-visual-collaboration", "visual_collaboration must truthfully bind the selected medium, independent image capabilities, prompt strategy, and inspection owner", "manifest.visual_collaboration")
	}
	return diagnostics
}

func previewManifestDiagnostics(manifest map[string]any, directionIDs []string, ready bool, expectedPrimaryMedium string) []designDiagnostic {
	var diagnostics []designDiagnostic
	if manifest["schema"] != designPreviewManifestSchema {
		addDesignDiagnostic(&diagnostics, "preview-invalid-manifest-schema", "preview manifest schema must equal "+designPreviewManifestSchema, "manifest.schema")
	}
	if ready && manifest["configured"] != true {
		addDesignDiagnostic(&diagnostics, "preview-manifest-not-configured", "ready preview manifest must set configured to true", "manifest.configured")
	}
	diagnostics = append(diagnostics, previewVisualCollaborationDiagnostics(manifest, expectedPrimaryMedium)...)
	directions, ok := manifest["directions"].([]any)
	if !ok || len(directions) != 1 {
		addDesignDiagnostic(&diagnostics, "preview-manifest-direction-count", "preview manifest must define exactly one current concept", "manifest.directions")
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
			dials, dialsOK := direction["dials"].(map[string]any)
			if !dialsOK {
				addDesignDiagnostic(&diagnostics, "preview-missing-direction-dials", "ready direction "+id+" must define dials.variance/motion/density", fmt.Sprintf("manifest.directions[%d].dials", index))
			} else {
				validDials := true
				for _, axis := range []string{"variance", "motion", "density"} {
					if !validDesignDial(dials[axis]) {
						validDials = false
					}
				}
				if !validDials {
					addDesignDiagnostic(&diagnostics, "preview-invalid-direction-dials", "ready direction "+id+" dials must be integers 1-10 for variance, motion, and density", fmt.Sprintf("manifest.directions[%d].dials", index))
				}
				reason := strings.TrimSpace(fmt.Sprint(dials["inference_reason"]))
				if reason == "" || reason == "<nil>" {
					addDesignDiagnostic(&diagnostics, "preview-missing-dial-inference", "ready direction "+id+" must explain dial inference_reason", fmt.Sprintf("manifest.directions[%d].dials.inference_reason", index))
				} else if previewPlaceholderRE.MatchString(reason) {
					addDesignDiagnostic(&diagnostics, "preview-unresolved-dial-inference", "ready direction "+id+" inference_reason must replace scaffold placeholders", fmt.Sprintf("manifest.directions[%d].dials.inference_reason", index))
				} else if scaffoldTasteReason(reason) {
					addDesignDiagnostic(&diagnostics, "preview-scaffold-taste-reason", "ready direction "+id+" inference_reason must use project intake instead of scaffold wording", fmt.Sprintf("manifest.directions[%d].dials.inference_reason", index))
				}
			}
			family := strings.TrimSpace(fmt.Sprint(direction["aesthetic_family"]))
			if family == "" || family == "<nil>" {
				addDesignDiagnostic(&diagnostics, "preview-missing-aesthetic-family", "ready direction "+id+" must define aesthetic_family", fmt.Sprintf("manifest.directions[%d].aesthetic_family", index))
			} else if previewPlaceholderRE.MatchString(family) {
				addDesignDiagnostic(&diagnostics, "preview-unresolved-aesthetic-family", "ready direction "+id+" aesthetic_family must replace scaffold placeholders", fmt.Sprintf("manifest.directions[%d].aesthetic_family", index))
			}
		}
	}
	if !reflect.DeepEqual(manifestIDs, directionIDs) {
		addDesignDiagnostic(&diagnostics, "preview-manifest-direction-mismatch", "preview manifest direction ID must match the rendered current concept", "manifest.directions")
	}
	if decisions, ok := manifest["decisions"].([]any); !ok || len(decisions) == 0 {
		addDesignDiagnostic(&diagnostics, "preview-missing-decisions", "preview manifest must define stable design decisions", "manifest.decisions")
	}
	diagnostics = append(diagnostics, previewCapabilityDiagnostics(manifest, directions, ready)...)
	diagnostics = append(diagnostics, previewHandoffDiagnostics(manifest, ready)...)
	return diagnostics
}

func validDesignDial(value any) bool {
	switch typed := value.(type) {
	case int:
		return typed >= 1 && typed <= 10
	case float64:
		return typed == float64(int(typed)) && typed >= 1 && typed <= 10
	case json.Number:
		parsed, err := strconv.Atoi(typed.String())
		return err == nil && parsed >= 1 && parsed <= 10
	default:
		return false
	}
}

func scaffoldTasteReason(value string) bool {
	lowered := strings.ToLower(strings.TrimSpace(value))
	for _, prefix := range []string{"scaffold baseline:", "scaffold default:", "template baseline:"} {
		if strings.HasPrefix(lowered, prefix) {
			return true
		}
	}
	return false
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
	if _, ok := handoff["source_continuity"].(map[string]any); !ok {
		addDesignDiagnostic(&diagnostics, "preview-source-continuity-invalid", "manifest.handoff.source_continuity must be an object", "manifest.handoff.source_continuity")
	} else if ready {
		if err := validateDesignSourceContinuity(
			handoff["source_continuity"],
			"manifest.handoff.source_continuity",
			true,
		); err != nil {
			addDesignDiagnostic(&diagnostics, "preview-source-continuity-invalid", err.Error(), "manifest.handoff.source_continuity")
		} else if err := validateDesignHandoffSourceContinuityCoverage(handoff, "manifest.handoff.source_continuity"); err != nil {
			addDesignDiagnostic(&diagnostics, "preview-source-continuity-coverage-mismatch", err.Error(), "manifest.handoff.source_continuity.coverage")
		}
	}
	components, componentsOK := handoff["component_contracts"].([]any)
	surfaces, surfacesOK := handoff["surface_catalog"].([]any)
	scenarios, scenariosOK := handoff["scenario_matrix"].([]any)
	responsive, responsiveOK := handoff["responsive_matrix"].([]any)
	acceptance, acceptanceOK := handoff["visual_acceptance_matrix"].([]any)
	if !componentsOK || len(components) == 0 {
		addDesignDiagnostic(&diagnostics, "preview-missing-component-contracts", "handoff must define component contracts", "manifest.handoff.component_contracts")
	}
	if !surfacesOK || len(surfaces) == 0 {
		addDesignDiagnostic(&diagnostics, "preview-missing-surface-catalog", "handoff must define a stable surface_catalog", "manifest.handoff.surface_catalog")
	}
	if !scenariosOK || len(scenarios) == 0 {
		addDesignDiagnostic(&diagnostics, "preview-missing-scenario-matrix", "handoff must define a bounded scenario_matrix", "manifest.handoff.scenario_matrix")
	}
	if !responsiveOK || len(responsive) == 0 {
		addDesignDiagnostic(&diagnostics, "preview-missing-responsive-matrix", "handoff must define responsive targets", "manifest.handoff.responsive_matrix")
	}
	if !acceptanceOK || len(acceptance) == 0 {
		addDesignDiagnostic(&diagnostics, "preview-missing-visual-acceptance", "handoff must define visual acceptance rows", "manifest.handoff.visual_acceptance_matrix")
	}
	professionalFields := []string{"interaction_matrix", "editing_matrix", "data_state_matrix", "accessibility_matrix", "navigation_matrix", "content_matrix"}
	for _, field := range professionalFields {
		rows, ok := handoff[field].([]any)
		if !ok || len(rows) == 0 {
			addDesignDiagnostic(&diagnostics, "preview-missing-"+strings.ReplaceAll(field, "_", "-"), "preview handoff must define a non-empty "+field, "manifest.handoff."+field)
			continue
		}
		for index, raw := range rows {
			row, ok := raw.(map[string]any)
			if !ok {
				addDesignDiagnostic(&diagnostics, "preview-incomplete-professional-contract", field+" rows must be objects", fmt.Sprintf("manifest.handoff.%s[%d]", field, index))
				continue
			}
			validateID(row["id"], fmt.Sprintf("manifest.handoff.%s[%d].id", field, index))
			if ready && !validDesignProfessionalRow(field, row) {
				addDesignDiagnostic(&diagnostics, "preview-incomplete-professional-contract", field+" row is missing its executable professional UI fields", fmt.Sprintf("manifest.handoff.%s[%d]", field, index))
			}
			for decisionID := range listToStringSet(row["decision_ids"]) {
				if !knownDecisions[decisionID] {
					addDesignDiagnostic(&diagnostics, "preview-unknown-handoff-decision", field+" row must reference known DS-* decisions", fmt.Sprintf("manifest.handoff.%s[%d].decision_ids", field, index))
				}
			}
		}
	}
	motionContract, motionOK := handoff["motion_contract"].(map[string]any)
	if !motionOK {
		addDesignDiagnostic(&diagnostics, "preview-missing-motion-contract", "preview handoff must define a structured motion_contract", "manifest.handoff.motion_contract")
	} else {
		transitions, transitionsOK := motionContract["transitions"].([]any)
		if !transitionsOK || len(transitions) == 0 {
			addDesignDiagnostic(&diagnostics, "preview-incomplete-motion-contract", "motion_contract.transitions must be a non-empty list", "manifest.handoff.motion_contract.transitions")
		}
		for index, raw := range transitions {
			transition, ok := raw.(map[string]any)
			if !ok {
				continue
			}
			validateID(transition["id"], fmt.Sprintf("manifest.handoff.motion_contract.transitions[%d].id", index))
			if ready && !validDesignMotionTransition(transition) {
				addDesignDiagnostic(&diagnostics, "preview-incomplete-motion-contract", "motion transitions require surface, trigger, response, duration, easing, interruption behavior, and decisions", fmt.Sprintf("manifest.handoff.motion_contract.transitions[%d]", index))
			}
			for decisionID := range listToStringSet(transition["decision_ids"]) {
				if !knownDecisions[decisionID] {
					addDesignDiagnostic(&diagnostics, "preview-unknown-handoff-decision", "motion transition must reference known DS-* decisions", fmt.Sprintf("manifest.handoff.motion_contract.transitions[%d].decision_ids", index))
				}
			}
		}
		if ready && !validDesignMotionContract(motionContract) {
			addDesignDiagnostic(&diagnostics, "preview-incomplete-motion-contract", "motion_contract requires purpose, reduced-motion behavior, transitions, and ordered immediate/progress/timeout timing", "manifest.handoff.motion_contract")
		}
	}

	componentIDs := map[string]bool{}
	for _, raw := range components {
		if row, ok := raw.(map[string]any); ok {
			componentIDs[strings.TrimSpace(fmt.Sprint(row["id"]))] = true
		}
	}
	knownSpecimens := stringSliceSet(manifestSpecimenIDs(manifest))
	surfaceIDs := map[string]bool{}
	for index, raw := range surfaces {
		surface, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		id := validateID(surface["id"], fmt.Sprintf("manifest.handoff.surface_catalog[%d].id", index))
		if id != "" {
			surfaceIDs[id] = true
		}
		if ready && (!nonEmpty(surface["profile_id"]) || !nonEmpty(surface["name"]) || !nonEmpty(surface["kind"]) || !nonEmpty(surface["entrypoint_id"]) || !isNonEmptyStringList(surface["source_refs"], true) || !isNonEmptyStringList(surface["specimen_ids"], true) || !stringSetContainsAll(knownSpecimens, stringList(surface["specimen_ids"])) || !isNonEmptyStringList(surface["component_ids"], true) || !stringSetContainsAll(componentIDs, stringList(surface["component_ids"])) || !isNonEmptyStringList(surface["decision_ids"], true)) {
			addDesignDiagnostic(&diagnostics, "preview-incomplete-surface-catalog", "surface_catalog rows require profile, official entrypoint, source, specimen, component, and decision bindings", fmt.Sprintf("manifest.handoff.surface_catalog[%d]", index))
		}
		for decisionID := range listToStringSet(surface["decision_ids"]) {
			if !knownDecisions[decisionID] {
				addDesignDiagnostic(&diagnostics, "preview-unknown-handoff-decision", "surface catalog must reference known DS-* decisions", fmt.Sprintf("manifest.handoff.surface_catalog[%d].decision_ids", index))
			}
		}
	}
	type scenarioValidationSource struct {
		field string
		rows  []any
	}
	interactionRows, _ := handoff["interaction_matrix"].([]any)
	editingRows, _ := handoff["editing_matrix"].([]any)
	dataStateRows, _ := handoff["data_state_matrix"].([]any)
	accessibilityRows, _ := handoff["accessibility_matrix"].([]any)
	navigationRows, _ := handoff["navigation_matrix"].([]any)
	contentRows, _ := handoff["content_matrix"].([]any)
	validationSources := []scenarioValidationSource{
		{"interaction_ids", interactionRows},
		{"editing_ids", editingRows},
		{"data_state_ids", dataStateRows},
		{"accessibility_ids", accessibilityRows},
		{"navigation_ids", navigationRows},
		{"content_ids", contentRows},
		{"responsive_ids", responsive},
	}
	if motionOK {
		if rows, ok := motionContract["transitions"].([]any); ok {
			validationSources = append(validationSources, scenarioValidationSource{"motion_transition_ids", rows})
		}
	}
	rowsByID := map[string]map[string]any{}
	knownScenarioRefs := map[string]map[string]bool{}
	coveredScenarioRefs := map[string]map[string]bool{}
	for _, source := range validationSources {
		knownScenarioRefs[source.field] = map[string]bool{}
		coveredScenarioRefs[source.field] = map[string]bool{}
		for _, raw := range source.rows {
			row, ok := raw.(map[string]any)
			if !ok {
				continue
			}
			id := strings.TrimSpace(fmt.Sprint(row["id"]))
			knownScenarioRefs[source.field][id] = true
			rowsByID[id] = row
		}
	}
	for index, raw := range scenarios {
		scenario, ok := raw.(map[string]any)
		if !ok {
			continue
		}
		validateID(scenario["id"], fmt.Sprintf("manifest.handoff.scenario_matrix[%d].id", index))
		valid := surfaceIDs[strings.TrimSpace(fmt.Sprint(scenario["surface_id"]))] && nonEmpty(scenario["name"])
		risk := strings.TrimSpace(fmt.Sprint(scenario["risk"]))
		valid = valid && (risk == "low" || risk == "medium" || risk == "high")
		required, requiredOK := scenario["required"].(bool)
		valid = valid && requiredOK && required && validDesignInteractionScript(scenario["interaction_script"], listToStringSet(scenario["data_state_ids"]))
		referencedIDs := map[string]bool{}
		for _, source := range validationSources {
			refs := stringList(scenario[source.field])
			if len(refs) == 0 || !stringSetContainsAll(knownScenarioRefs[source.field], refs) {
				valid = false
				continue
			}
			for _, id := range refs {
				coveredScenarioRefs[source.field][id] = true
				referencedIDs[id] = true
			}
		}
		expectedDecisions := map[string]bool{}
		for id := range referencedIDs {
			for decisionID := range listToStringSet(rowsByID[id]["decision_ids"]) {
				expectedDecisions[decisionID] = true
			}
		}
		if !stringSetEqual(listToStringSet(scenario["decision_ids"]), expectedDecisions) {
			valid = false
		}
		if ready && !valid {
			addDesignDiagnostic(&diagnostics, "preview-invalid-scenario-contract", "scenario_matrix rows must bind one known surface to known matrix rows with exact decision coverage", fmt.Sprintf("manifest.handoff.scenario_matrix[%d]", index))
		}
	}
	for _, source := range validationSources {
		if !stringSetEqual(coveredScenarioRefs[source.field], knownScenarioRefs[source.field]) {
			addDesignDiagnostic(&diagnostics, "preview-incomplete-scenario-coverage", "scenario_matrix must cover every "+source.field+" contract without a Cartesian expansion", "manifest.handoff.scenario_matrix")
		}
	}
	if usability, ok := handoff["usability_validation"].(map[string]any); !ok {
		addDesignDiagnostic(&diagnostics, "preview-missing-usability-validation", "preview handoff must define usability_validation", "manifest.handoff.usability_validation")
	} else if ready && !validDesignUsabilityValidation(usability) {
		addDesignDiagnostic(&diagnostics, "preview-incomplete-usability-validation", "usability_validation requires risk, methods, critical tasks, success criteria, and an explicit human-review decision", "manifest.handoff.usability_validation")
		if strings.TrimSpace(fmt.Sprint(usability["risk_level"])) == "high" {
			if humanReview, ok := usability["human_review_required"].(bool); !ok || !humanReview {
				addDesignDiagnostic(&diagnostics, "preview-high-risk-human-review-required", "high-risk usability validation must require human review", "manifest.handoff.usability_validation.human_review_required")
			}
		}
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
		governance := strings.TrimSpace(fmt.Sprint(component["governance"]))
		adoptionValid := true
		if adoption, exists := component["adoption"]; exists {
			adoptionValid = validDesignComponentAdoption(adoption)
		}
		if ready && (!nonEmpty(component["component"]) || !isNonEmptyStringList(component["anatomy"], true) || !isNonEmptyStringList(component["required_states"], true) || !isNonEmptyStringList(component["interaction_modes"], true) || !validDesignDataScenarios(component["data_scenarios"]) || !isNonEmptyStringList(component["variants"], true) || !isNonEmptyStringList(component["content_constraints"], true) || !isNonEmptyStringList(component["semantic_token_refs"], true) || (governance != "reuse" && governance != "extend" && governance != "new") || !nonEmpty(component["iconography"]) || !isNonEmptyStringList(component["decision_ids"], true) || !isNonEmptyStringList(component["must_match"], true) || !adoptionValid) {
			addDesignDiagnostic(&diagnostics, "preview-incomplete-component-contract", "component contracts require anatomy, states, interaction/data scenarios, variants, content constraints, semantic tokens, governance, iconography, decisions, and must_match", fmt.Sprintf("manifest.handoff.component_contracts[%d]", index))
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
		if ready && (!nonEmpty(row["profile_id"]) || !nonEmpty(row["review_width_px"]) || !nonEmpty(row["label"]) || !nonEmpty(row["state"]) || !nonEmpty(row["adaptation"]) || !nonEmpty(row["stretch_behavior"]) || !nonEmpty(row["overflow_behavior"]) || !isNonEmptyStringList(row["decision_ids"], true)) {
			addDesignDiagnostic(&diagnostics, "preview-incomplete-responsive-contract", "responsive contracts require profile, review width, label, state, adaptation, stretch behavior, overflow behavior, and decisions", fmt.Sprintf("manifest.handoff.responsive_matrix[%d]", index))
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
		"visual_medium":   "html",
		"preview_file":    filepath.Base(path),
		"direction_id":    approvedDirection,
		"preview_ref":     filepath.Base(path) + "#" + approvedDirection,
		"html_sha256":     sha256String(content),
		"manifest_sha256": canonicalJSONSHA256(manifest),
		"handoff_file":    filepath.Base(strings.TrimSuffix(path, filepath.Ext(path)) + ".handoff.json"),
		"handoff_ref":     filepath.Base(strings.TrimSuffix(path, filepath.Ext(path)) + ".handoff.json"),
	}
	if collaboration, ok := manifest["visual_collaboration"].(map[string]any); ok {
		for _, field := range []string{"image_generation", "image_inspection", "image_editing", "inspection_owner", "prompt_strategy"} {
			expected[field] = strings.TrimSpace(fmt.Sprint(collaboration[field]))
		}
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
		if regexp.MustCompile(`(?i)round-\d+\.(?:html|png|jpe?g|webp)#direction-[a-z0-9-]+$`).MatchString(ref) {
			for _, field := range []string{"preview_sha256", "manifest_sha256", "handoff_sha256"} {
				if !hexDigestRE.MatchString(strings.TrimSpace(fmt.Sprint(approval[field]))) {
					addDesignDiagnostic(diagnostics, "ui-target-invalid-approval-digest", "approved visual round requires a valid "+field, "manifest.approval."+field)
				}
			}
			handoffRef := strings.TrimSpace(fmt.Sprint(approval["handoff_ref"]))
			if !strings.HasSuffix(strings.ToLower(handoffRef), ".handoff.json") {
				addDesignDiagnostic(diagnostics, "ui-target-invalid-handoff-reference", "approved visual round requires an immutable handoff_ref", "manifest.approval.handoff_ref")
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
		"This file is input for `sp-design`. It is not an approved UI design change.\n\n" +
		"## Imported Reference\n\n" +
		"- Source: " + strings.TrimSpace(source) + "\n" +
		"- Notes: " + notes + "\n\n" +
		"## Synthesis Instructions\n\n" +
		"- Extract reusable design principles.\n" +
		"- Remove brand-specific expression.\n" +
		"- Write original scoped guidance into the change-local `design-change.md` only after user approval in `sp-design`.\n"
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
		handoff["surface_catalog"],
		handoff["scenario_matrix"],
		handoff["component_contracts"],
		handoff["interaction_matrix"],
		handoff["editing_matrix"],
		handoff["data_state_matrix"],
		handoff["accessibility_matrix"],
		handoff["navigation_matrix"],
		handoff["content_matrix"],
		handoff["responsive_matrix"],
		handoff["visual_acceptance_matrix"],
		handoff["accepted_deviations"],
	}
	if motion, ok := handoff["motion_contract"].(map[string]any); ok {
		collections = append(collections, motion["transitions"])
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
	return buildDesignHandoffPayloadForMedium(path, []byte(content), directionID, manifest, "html", "", "")
}

func buildDesignHandoffPayloadForMedium(path string, content []byte, directionID string, manifest map[string]any, visualMedium, promptSHA256, inspectionOwner string) (map[string]any, error) {
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
	// The selected direction owns review-board motion tokens. The reproduction
	// contract already contains profile-adapted implementation transitions and
	// reduced-motion behavior; keep those per-platform values intact.
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
				approvedRef := filepath.Base(path) + "#" + directionID
				if visualMedium == "html" {
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
					approvedRef = filepath.Base(path) + "?" + query + "#" + directionID
				}
				targets = append(targets, map[string]any{
					"ref":         approvedRef,
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
	approval := map[string]any{
		"preview_file":    filepath.Base(path),
		"preview_ref":     filepath.Base(path) + "#" + directionID,
		"direction_id":    directionID,
		"review_round":    strings.TrimSpace(fmt.Sprint(review["round"])),
		"preview_sha256":  sha256Bytes(content),
		"manifest_sha256": canonicalJSONSHA256(manifest),
		"decision_ids":    manifestDecisionIDs(manifest),
		"visual_medium":   visualMedium,
	}
	if collaboration, ok := manifest["visual_collaboration"].(map[string]any); ok {
		for _, field := range []string{"image_generation", "image_inspection", "image_editing", "inspection_owner", "prompt_strategy"} {
			if value := strings.TrimSpace(fmt.Sprint(collaboration[field])); value != "" && value != "<nil>" {
				approval[field] = value
			}
		}
	}
	if promptSHA256 != "" {
		approval["prompt_ref"] = strings.TrimSuffix(filepath.Base(path), filepath.Ext(path)) + ".prompt.md"
		approval["prompt_sha256"] = promptSHA256
	}
	if inspectionOwner != "" {
		approval["inspection_owner"] = inspectionOwner
	}
	return map[string]any{
		"schema":                  designHandoffSchema,
		"approval":                approval,
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

func designJSONInt(value any) (int, bool) {
	switch typed := value.(type) {
	case int:
		return typed, true
	case float64:
		if typed != float64(int(typed)) {
			return 0, false
		}
		return int(typed), true
	case json.Number:
		parsed, err := strconv.Atoi(typed.String())
		return parsed, err == nil
	default:
		return 0, false
	}
}

func designJSONFloat(value any) (float64, bool) {
	switch typed := value.(type) {
	case int:
		return float64(typed), true
	case float64:
		return typed, true
	case json.Number:
		parsed, err := strconv.ParseFloat(typed.String(), 64)
		return parsed, err == nil
	default:
		return 0, false
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

func sha256Bytes(content []byte) string {
	sum := sha256.Sum256(content)
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

func validDesignInteractionScript(value any, dataStateIDs map[string]bool) bool {
	script, ok := value.(map[string]any)
	if !ok || len(script) != 8 || !isNonEmptyStringList(script["preconditions"], true) || !dataStateIDs[strings.TrimSpace(fmt.Sprint(script["start_state_id"]))] {
		return false
	}
	for _, field := range []string{"focus_checkpoint", "announcement_checkpoint", "completion_checkpoint", "recovery_checkpoint"} {
		if !nonEmpty(script[field]) {
			return false
		}
	}
	steps, ok := script["steps"].([]any)
	if !ok || len(steps) == 0 {
		return false
	}
	for _, raw := range steps {
		step, ok := raw.(map[string]any)
		if !ok || len(step) != 3 || !nonEmpty(step["input"]) || !nonEmpty(step["action"]) || !nonEmpty(step["expected_feedback"]) {
			return false
		}
	}
	branches, ok := script["branches"].([]any)
	if !ok || len(branches) == 0 {
		return false
	}
	allowedConditions := map[string]bool{
		"success": true, "failure": true, "timeout": true, "cancel": true,
		"retry": true, "duplicate": true, "out_of_order": true,
	}
	seenConditions := map[string]bool{}
	for _, raw := range branches {
		branch, ok := raw.(map[string]any)
		if !ok || len(branch) != 7 || !isNonEmptyStringList(branch["conditions"], true) || !dataStateIDs[strings.TrimSpace(fmt.Sprint(branch["expected_state_id"]))] {
			return false
		}
		for _, condition := range stringList(branch["conditions"]) {
			if !allowedConditions[condition] || seenConditions[condition] {
				return false
			}
			seenConditions[condition] = true
		}
		for _, field := range []string{"setup", "expected_feedback", "focus_behavior", "announcement", "continuation"} {
			if !nonEmpty(branch[field]) {
				return false
			}
		}
	}
	if !seenConditions["success"] || !(seenConditions["failure"] || seenConditions["timeout"] || seenConditions["cancel"]) || !(seenConditions["retry"] || seenConditions["duplicate"] || seenConditions["out_of_order"]) {
		return false
	}
	return true
}

func validDesignDataScenarios(value any) bool {
	rows, ok := value.([]any)
	if !ok || len(rows) == 0 {
		return false
	}
	for _, raw := range rows {
		row, ok := raw.(map[string]any)
		if !ok || !nonEmpty(row["state"]) || !nonEmpty(row["data_condition"]) || !nonEmpty(row["expectation"]) {
			return false
		}
	}
	return true
}

func validDesignComponentAdoption(value any) bool {
	adoption, ok := value.(map[string]any)
	if !ok || !nonEmpty(adoption["resource_id"]) || !nonEmpty(adoption["source_ref"]) {
		return false
	}
	action := strings.TrimSpace(anyString(adoption["action"]))
	if action != "reuse" && action != "extend" && action != "add" && action != "custom" {
		return false
	}
	for _, field := range []string{"package", "version", "license", "source_ref"} {
		if value, ok := adoption[field].(string); !ok || strings.TrimSpace(value) == "" {
			return false
		}
	}
	for _, field := range []string{"component_refs", "reason_codes", "selection_basis_refs"} {
		if !isNonEmptyStringList(adoption[field], true) {
			return false
		}
	}
	gate := strings.TrimSpace(anyString(adoption["permission_gate"]))
	status := strings.TrimSpace(anyString(adoption["permission_status"]))
	if (gate != "required" && gate != "not-required") || (status != "authorized" && status != "not-authorized") {
		return false
	}
	return !(action == "add" && gate != "required") && !(gate == "not-required" && status != "authorized")
}

func validDesignProfessionalRow(field string, row map[string]any) bool {
	if !isNonEmptyStringList(row["decision_ids"], true) || !nonEmpty(row["surface"]) {
		return false
	}
	requiredStrings := map[string][]string{
		"interaction_matrix": {
			"input", "trigger", "event_sequence", "immediate_feedback", "focus_behavior",
			"repeat_behavior", "cancellation_behavior", "pending_behavior",
		},
		"editing_matrix": {
			"composition_behavior", "paste_autofill_behavior", "selection_caret_behavior", "formatting_behavior",
			"validation_timing", "validation_feedback", "dirty_state_behavior", "persistence_behavior",
			"undo_redo_behavior", "conflict_behavior", "read_only_disabled_behavior", "submission_behavior",
		},
		"data_state_matrix": {"state", "data_condition", "expectation"},
		"accessibility_matrix": {
			"reading_order", "focus_order", "target_size", "contrast", "zoom_reflow",
		},
		"navigation_matrix": {
			"entry", "destination", "trigger", "back_behavior", "deep_link_behavior", "interruption_recovery",
		},
		"content_matrix": {
			"state", "purpose", "copy", "primary_action", "trust_requirement", "localization",
		},
	}
	for _, key := range requiredStrings[field] {
		if !nonEmpty(row[key]) {
			return false
		}
	}
	switch field {
	case "interaction_matrix":
		expected := map[string]bool{
			"id": true, "surface": true, "input": true, "trigger": true,
			"event_sequence": true, "immediate_feedback": true, "focus_behavior": true,
			"repeat_behavior": true, "cancellation_behavior": true, "pending_behavior": true,
			"decision_ids": true,
		}
		if len(row) != len(expected) {
			return false
		}
		for key := range row {
			if !expected[key] {
				return false
			}
		}
	case "editing_matrix":
		if !isNonEmptyStringList(row["input_methods"], true) {
			return false
		}
		expected := map[string]bool{
			"id": true, "surface": true, "input_methods": true, "composition_behavior": true,
			"paste_autofill_behavior": true, "selection_caret_behavior": true, "formatting_behavior": true,
			"validation_timing": true, "validation_feedback": true, "dirty_state_behavior": true,
			"persistence_behavior": true, "undo_redo_behavior": true, "conflict_behavior": true,
			"read_only_disabled_behavior": true, "submission_behavior": true, "decision_ids": true,
		}
		if len(row) != len(expected) {
			return false
		}
		for key := range row {
			if !expected[key] {
				return false
			}
		}
	case "accessibility_matrix":
		for _, key := range []string{"semantics", "keyboard", "announcements", "alternatives"} {
			if !isNonEmptyStringList(row[key], true) {
				return false
			}
		}
	case "content_matrix":
		if !isNonEmptyStringList(row["content_limits"], true) {
			return false
		}
	}
	return true
}

func validDesignMotionTransition(transition map[string]any) bool {
	for _, field := range []string{"surface", "trigger", "response", "easing", "interrupt_behavior"} {
		if !nonEmpty(transition[field]) {
			return false
		}
	}
	duration, ok := designJSONInt(transition["duration_ms"])
	return ok && duration >= 0 && isNonEmptyStringList(transition["decision_ids"], true)
}

func validDesignMotionContract(contract map[string]any) bool {
	if !nonEmpty(contract["purpose"]) || !nonEmpty(contract["reduced_motion"]) {
		return false
	}
	transitions, ok := contract["transitions"].([]any)
	if !ok || len(transitions) == 0 {
		return false
	}
	timing, ok := contract["feedback_timing"].(map[string]any)
	if !ok {
		return false
	}
	immediate, immediateOK := designJSONInt(timing["immediate_ms"])
	progress, progressOK := designJSONInt(timing["progress_ms"])
	timeout, timeoutOK := designJSONInt(timing["timeout_ms"])
	return immediateOK && progressOK && timeoutOK && immediate >= 0 && progress > 0 && timeout > progress
}

func validDesignUsabilityValidation(value map[string]any) bool {
	risk := strings.TrimSpace(fmt.Sprint(value["risk_level"]))
	if risk != "low" && risk != "medium" && risk != "high" {
		return false
	}
	for _, field := range []string{"methods", "critical_tasks", "success_criteria"} {
		if !isNonEmptyStringList(value[field], true) {
			return false
		}
	}
	humanReview, ok := value["human_review_required"].(bool)
	if !ok || (risk == "high" && !humanReview) {
		return false
	}
	if rawIDs, exists := value["smoothness_acceptance_ids"]; exists {
		ids := stringList(rawIDs)
		if raw, ok := rawIDs.([]any); !ok || len(raw) != len(ids) || len(ids) != len(listToStringSet(rawIDs)) {
			return false
		}
	}
	if rawBudgets, exists := value["performance_budgets"]; exists {
		budgets, ok := rawBudgets.(map[string]any)
		if !ok || len(budgets) != 5 {
			return false
		}
		for _, field := range []string{"inp_ms", "long_task_ms", "cls", "animation_dropped_frame_pct", "bundle_delta_kb"} {
			if number, valid := designJSONFloat(budgets[field]); !valid || number < 0 {
				return false
			}
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
