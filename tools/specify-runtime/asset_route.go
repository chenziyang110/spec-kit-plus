package main

import (
	"fmt"
	"os"
	"path"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

type AssetRouteRequest struct {
	Purpose    string
	Path       string
	Slug       string
	TaskID     string
	WorkerID   string
	Date       string
	Retention  string
	FeatureID  string
	ChangeID   string
	PolicyPath string
}

func (service *AssetService) Route(request AssetRouteRequest) Envelope {
	policy, err := service.LoadPolicy(request.PolicyPath)
	if err != nil {
		return assetFailure("invalid", "asset policy is invalid", err)
	}
	if request.Path != "" {
		classification, err := service.ClassifyPath(request.Path, policy)
		if err != nil {
			return assetFailure("blocked", "asset path is unsafe", err)
		}
		if classification.Protected {
			return assetOwnedEnvelope(classification, policy)
		}
		if request.Purpose != "" && !assetValidPurpose(request.Purpose) {
			return assetFailure("invalid", "unknown asset purpose", fmt.Errorf("use architecture, decision, guide, reference, report, asset, temporary, or source"))
		}
		if request.Purpose == "source" && classification.Kind != "source" && classification.Kind != "other" {
			return assetFailure("blocked", "source purpose cannot override document placement rules", fmt.Errorf("%s is classified as %s", classification.Path, classification.Kind))
		}
		if request.Purpose == "temporary" && !classification.Temporary {
			return assetFailure("blocked", "temporary assets need an isolated temporary path", fmt.Errorf("use %s/<task-id>/<worker-id>/<name>", policy.TemporaryRoot))
		}
		if !classification.Compliant {
			env := assetRouteEnvelope("blocked", "conflict", "asset path conflicts with placement policy", classification, policy)
			for _, issue := range classification.Issues {
				env.Items = append(env.Items, issue)
			}
			return env
		}
		return service.assetRouteExistingOrNew(classification, policy, request)
	}
	if request.FeatureID != "" || request.ChangeID != "" {
		classification := AssetClassification{Kind: "workflow-artifact", Protected: true, Owner: "specify-runtime artifact/state owner", RuleID: "explicit-workflow-scope", Issues: []AssetIssue{}}
		env := assetOwnedEnvelope(classification, policy)
		env.Data["feature_id"] = request.FeatureID
		env.Data["change_id"] = request.ChangeID
		return env
	}
	if !assetValidPurpose(request.Purpose) {
		return assetFailure("invalid", "asset purpose is required", fmt.Errorf("use architecture, decision, guide, reference, report, asset, temporary, or source"))
	}
	if request.Purpose == "source" {
		return assetFailure("invalid", "source assets need an explicit native path", fmt.Errorf("provide --path inside the project's source/template/fixture directory"))
	}
	stem, extension, err := assetRouteName(request.Slug, request.Purpose)
	if err != nil {
		return assetFailure("invalid", "asset name is invalid", err)
	}
	if request.TaskID != "" && !safeSegment(request.TaskID) {
		return assetFailure("invalid", "invalid task id", fmt.Errorf("task id must be a safe path segment"))
	}
	if request.WorkerID != "" && (!safeSegment(request.WorkerID) || request.TaskID == "") {
		return assetFailure("invalid", "invalid worker scope", fmt.Errorf("worker id must be safe and accompanied by a task id"))
	}
	root := ""
	if request.Purpose == "temporary" {
		if request.TaskID == "" || request.WorkerID == "" {
			return assetFailure("invalid", "temporary asset scope is required", fmt.Errorf("provide both task-id and worker-id"))
		}
		root = path.Join(policy.TemporaryRoot, request.TaskID, request.WorkerID)
	} else {
		root, err = service.assetRouteRoot(request.Purpose, policy)
		if err != nil {
			return assetFailure("blocked", "asset destination is unavailable", err)
		}
	}
	if request.Purpose == "report" {
		date := request.Date
		if date == "" {
			date = nowUTC().Format("2006-01-02")
		}
		if parsed, err := time.Parse("2006-01-02", date); err != nil || parsed.Format("2006-01-02") != date {
			return assetFailure("invalid", "report date is invalid", fmt.Errorf("date must use YYYY-MM-DD"))
		}
		if !assetDatePrefix.MatchString(stem) {
			stem = date + "-" + stem
		}
		if request.TaskID != "" {
			root = path.Join(root, request.TaskID)
		}
		if request.WorkerID != "" {
			root = path.Join(root, request.WorkerID)
		}
	}
	if request.Purpose == "decision" && !assetADRName.MatchString(stem) {
		stem, err = service.assetDecisionName(root, stem)
		if err != nil {
			return assetFailure("blocked", "decision name cannot be resolved", err)
		}
	}
	candidate := path.Join(root, stem+extension)
	// Search only bounded known document locations for an exact filename. This
	// recommends reusing a document; it never treats a semantic match as consent
	// to overwrite or merges two existing documents automatically.
	if request.Purpose != "temporary" && request.Purpose != "report" && request.Purpose != "decision" && policy.Roots[request.Purpose] == "" {
		candidate, err = service.assetPreferExisting(request.Purpose, stem+extension, candidate)
		if err != nil {
			return assetFailure("blocked", "multiple existing assets need disambiguation", err)
		}
	}
	classification, err := service.ClassifyPath(candidate, policy)
	if err != nil {
		return assetFailure("blocked", "asset destination is unsafe", err)
	}
	if classification.Protected {
		return assetOwnedEnvelope(classification, policy)
	}
	if !classification.Compliant {
		env := assetRouteEnvelope("blocked", "conflict", "asset destination conflicts with policy", classification, policy)
		for _, issue := range classification.Issues {
			env.Items = append(env.Items, issue)
		}
		return env
	}
	classification.Purpose = request.Purpose
	return service.assetRouteExistingOrNew(classification, policy, request)
}

func (service *AssetService) Explain(request AssetRouteRequest) Envelope {
	env := service.Route(request)
	env.Data["precedence"] = []string{"artifact-registry", "protected-and-control-paths", "native-source-and-fixtures", "explicit-project-roots", "existing-native-directories", "built-in-defaults"}
	env.Data["side_effects"] = "none"
	env.Data["reservation"] = "none; recheck the path immediately before writing"
	env.Data["workflow_activation"] = "none"
	return env
}

func assetValidPurpose(purpose string) bool {
	_, known := assetPurposeRoots[purpose]
	return known || purpose == "temporary" || purpose == "source"
}

func assetRouteName(slug, purpose string) (string, string, error) {
	if slug == "" || strings.ContainsAny(slug, "/\\") {
		return "", "", fmt.Errorf("provide a lower-case kebab-case slug, with an extension for media")
	}
	extension := path.Ext(slug)
	stem := strings.TrimSuffix(slug, extension)
	if extension == "" {
		if purpose == "asset" {
			return "", "", fmt.Errorf("asset slug must include its actual file extension")
		}
		extension = ".md"
	}
	if !assetKebabName.MatchString(stem) || extension != strings.ToLower(extension) || len(extension) > 20 {
		return "", "", fmt.Errorf("slug must use lower-case kebab-case and a lower-case extension")
	}
	if _, err := assetNormalizePath(stem + extension); err != nil {
		return "", "", err
	}
	return stem, extension, nil
}

func (service *AssetService) assetRouteRoot(purpose string, policy AssetPolicy) (string, error) {
	if root := policy.Roots[purpose]; root != "" {
		if _, err := secureProjectPath(service.projectRoot, root); err != nil {
			return "", err
		}
		return root, nil
	}
	for _, root := range assetPurposeRoots[purpose] {
		absolute, err := secureProjectPath(service.projectRoot, root)
		if err != nil {
			return "", err
		}
		info, err := os.Stat(absolute)
		if os.IsNotExist(err) {
			continue
		}
		if err != nil {
			return "", err
		}
		if !info.IsDir() {
			return "", fmt.Errorf("asset root %s exists and is not a directory", root)
		}
		return root, nil
	}
	return assetPurposeRoots[purpose][0], nil
}

func (service *AssetService) assetPreferExisting(purpose, basename, candidate string) (string, error) {
	roots := append([]string{}, assetPurposeRoots[purpose]...)
	if purpose != "asset" {
		roots = append(roots, "docs", "doc", "documentation")
	}
	seen := map[string]bool{}
	existing := []string{}
	for _, root := range roots {
		relative := path.Join(root, basename)
		if seen[relative] {
			continue
		}
		seen[relative] = true
		absolute, err := secureProjectPath(service.projectRoot, relative)
		if err != nil {
			return "", err
		}
		info, err := os.Stat(absolute)
		if os.IsNotExist(err) {
			continue
		}
		if err != nil {
			return "", err
		}
		if info.Mode().IsRegular() {
			existing = append(existing, relative)
		}
	}
	if len(existing) > 1 {
		sort.Strings(existing)
		return "", fmt.Errorf("choose an explicit existing path: %s", strings.Join(existing, ", "))
	}
	if len(existing) == 1 {
		return existing[0], nil
	}
	return candidate, nil
}

var assetDecisionPrefix = regexp.MustCompile(`^([0-9]{4})-(.+)\.md$`)

func (service *AssetService) assetDecisionName(root, slug string) (string, error) {
	absolute, err := secureProjectPath(service.projectRoot, root)
	if err != nil {
		return "", err
	}
	entries, err := assetReadDirectory(absolute, 10000)
	if os.IsNotExist(err) {
		return "0001-" + slug, nil
	}
	if err != nil {
		return "", err
	}
	maximum := 0
	existing := []string{}
	for _, entry := range entries {
		match := assetDecisionPrefix.FindStringSubmatch(entry.Name())
		if len(match) == 0 {
			continue
		}
		number, _ := strconv.Atoi(match[1])
		if number > maximum {
			maximum = number
		}
		if match[2] == slug {
			existing = append(existing, strings.TrimSuffix(entry.Name(), ".md"))
		}
	}
	if len(existing) > 1 {
		return "", fmt.Errorf("multiple decision records already use slug %q; select an explicit path", slug)
	}
	if len(existing) == 1 {
		return existing[0], nil
	}
	if maximum >= 9999 {
		return "", fmt.Errorf("decision sequence is exhausted; select an explicit project convention")
	}
	return fmt.Sprintf("%04d-%s", maximum+1, slug), nil
}

func (service *AssetService) assetRouteExistingOrNew(classification AssetClassification, policy AssetPolicy, request AssetRouteRequest) Envelope {
	absolute, err := secureProjectPath(service.projectRoot, classification.Path)
	if err != nil {
		return assetFailure("blocked", "asset path is unsafe", err)
	}
	action := "create-new"
	info, err := os.Stat(absolute)
	if err == nil {
		if !info.Mode().IsRegular() {
			return assetFailure("blocked", "asset destination is not a regular file", fmt.Errorf("%s is not a file", classification.Path))
		}
		action = "reuse-existing"
	} else if !os.IsNotExist(err) {
		return assetFailure("blocked", "asset destination cannot be inspected", err)
	}
	env := assetRouteEnvelope("ok", action, "asset destination resolved", classification, policy)
	if classification.Temporary {
		retention := request.Retention
		if retention == "" {
			retention = policy.TemporaryRetention
		}
		if retention != "session" && !assetRetention.MatchString(retention) {
			return assetFailure("invalid", "invalid temporary retention", fmt.Errorf("retention must be session or a positive number of days such as 7d"))
		}
		env.Data["retention"] = retention
		env.Data["tracked"] = false
	} else {
		env.Data["retention"] = "persistent"
	}
	if request.TaskID != "" {
		env.Data["task_id"] = request.TaskID
	}
	if request.WorkerID != "" {
		env.Data["worker_id"] = request.WorkerID
	}
	return env
}

func assetRouteEnvelope(status, action, summary string, classification AssetClassification, policy AssetPolicy) Envelope {
	env := NewEnvelope(status, summary)
	env.Data["action"] = action
	env.Data["path"] = classification.Path
	env.Data["purpose"] = classification.Purpose
	env.Data["classification"] = classification.Kind
	env.Data["rule_id"] = classification.RuleID
	env.Data["policy_path"] = policy.PolicyPath
	env.Data["allowed"] = status == "ok"
	if classification.Owner != "" {
		env.Data["owner"] = classification.Owner
	}
	if classification.TypeID != "" {
		env.Data["type_id"] = classification.TypeID
	}
	return env
}

func assetOwnedEnvelope(classification AssetClassification, policy AssetPolicy) Envelope {
	env := assetRouteEnvelope("blocked", "owner-required", "asset is governed by an existing owner", classification, policy)
	env.Blockers = append(env.Blockers, "preserve the existing path and owner contract; asset governance does not start or bypass a workflow")
	return env
}

func assetFailure(status, summary string, err error) Envelope {
	env := NewEnvelope(status, summary)
	env.Data["action"] = "conflict"
	if err != nil {
		env.Blockers = append(env.Blockers, err.Error())
	}
	return env
}
