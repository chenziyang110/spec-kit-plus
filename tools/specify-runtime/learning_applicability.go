package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path"
	"sort"
	"strings"
)

const learningApplicabilityVersion = "learning-applicability.v1"

// Bindings establish byte consistency, not the semantic truth of a lesson or
// the identity of its author. The existing Learning owner retains lifecycle.
type learningApplicabilityFile struct {
	Path   string `json:"path"`
	SHA256 string `json:"sha256"`
	Bytes  int64  `json:"bytes"`
}

type learningApplicabilityBinding struct {
	Version         string                      `json:"version"`
	Component       string                      `json:"component"`
	EvidenceKind    string                      `json:"evidence_kind"`
	Sources         []learningApplicabilityFile `json:"sources"`
	Constraints     []learningApplicabilityFile `json:"constraints"`
	Counterevidence []learningApplicabilityFile `json:"counterevidence"`
	Digest          string                      `json:"digest"`
}

type learningApplicabilityRequest struct {
	component, evidenceKind               string
	sources, constraints, counterevidence []string
}

func learningApplicabilityRequestFromArgs(args []string) learningApplicabilityRequest {
	return learningApplicabilityRequest{
		component: optionValue(args, "--component", ""), evidenceKind: optionValue(args, "--evidence-kind", ""),
		sources: optionValues(args, "--source-file"), constraints: optionValues(args, "--constraint-file"),
		counterevidence: optionValues(args, "--counterevidence-file"),
	}
}

func (request learningApplicabilityRequest) provided() bool {
	return request.component != "" || request.evidenceKind != "" || len(request.sources)+len(request.constraints)+len(request.counterevidence) > 0
}

func learningApplicabilityDigest(binding learningApplicabilityBinding) string {
	binding.Digest = ""
	raw, _ := json.Marshal(binding)
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}

func learningApplicabilityMap(binding learningApplicabilityBinding) map[string]any {
	raw, _ := json.Marshal(binding)
	result := map[string]any{}
	_ = json.Unmarshal(raw, &result)
	return result
}

func learningApplicabilityRelative(raw string, policy learningPolicy) (string, error) {
	value := strings.TrimSpace(strings.ReplaceAll(raw, "\\", "/"))
	if value == "" || strings.ContainsAny(value, ":\x00\r\n\t") || strings.HasPrefix(value, "/") {
		return "", fmt.Errorf("Learning applicability requires project-relative paths")
	}
	clean := path.Clean(value)
	if clean == "." || clean == ".." || strings.HasPrefix(clean, "../") {
		return "", fmt.Errorf("Learning applicability path must name a bounded project surface")
	}
	for _, protected := range []string{".git", ".specify/memory", ".specify/project-cognition", ".specify/do", ".planning/learnings"} {
		if lower := strings.ToLower(clean); lower == protected || strings.HasPrefix(lower, protected+"/") {
			return "", fmt.Errorf("Learning applicability cannot use runtime storage as source evidence")
		}
	}
	if redactLearningReferenceTextWithPolicy(clean, policy).text != clean {
		return "", fmt.Errorf("Learning applicability path requires a safe abstract source reference")
	}
	return clean, nil
}

func (service learningService) learningApplicabilityFile(raw string, policy learningPolicy) (learningApplicabilityFile, error) {
	ref, err := learningApplicabilityRelative(raw, policy)
	if err != nil {
		return learningApplicabilityFile{}, err
	}
	target, err := secureProjectPath(service.projectRoot, ref)
	if err != nil {
		return learningApplicabilityFile{}, fmt.Errorf("Learning applicability source is unavailable or redirected")
	}
	file, err := os.Open(target)
	if err != nil {
		return learningApplicabilityFile{}, fmt.Errorf("Learning applicability source is unavailable")
	}
	defer file.Close()
	info, err := file.Stat()
	if err != nil || !info.Mode().IsRegular() || info.Size() > 8*1024*1024 {
		return learningApplicabilityFile{}, fmt.Errorf("Learning applicability source must be a regular file of at most 8 MiB")
	}
	bytes, err := io.ReadAll(io.LimitReader(file, 8*1024*1024+1))
	if err != nil || len(bytes) > 8*1024*1024 {
		return learningApplicabilityFile{}, fmt.Errorf("Learning applicability source read failed")
	}
	sum := sha256.Sum256(bytes)
	return learningApplicabilityFile{Path: ref, SHA256: hex.EncodeToString(sum[:]), Bytes: int64(len(bytes))}, nil
}

func (service learningService) bindLearningApplicability(entry map[string]any, request learningApplicabilityRequest, policy learningPolicy) error {
	if !request.provided() {
		return nil
	}
	request.sources = uniqueSortedTrimmed(request.sources)
	request.constraints = uniqueSortedTrimmed(request.constraints)
	request.counterevidence = uniqueSortedTrimmed(request.counterevidence)
	component, err := learningApplicabilityRelative(request.component, policy)
	if err != nil {
		return err
	}
	componentPath, err := secureProjectPath(service.projectRoot, component)
	if err != nil {
		return fmt.Errorf("Learning applicability component is unavailable or redirected")
	}
	info, err := os.Stat(componentPath)
	if err != nil || !info.IsDir() {
		return fmt.Errorf("Learning applicability component must be an existing source directory")
	}
	kind := strings.ToLower(strings.TrimSpace(request.evidenceKind))
	if kind != "failure" && kind != "recovery" && kind != "correction" && kind != "constraint" {
		return fmt.Errorf("Learning applicability evidence-kind must be failure, recovery, correction, or constraint")
	}
	if len(request.sources) == 0 || len(request.constraints) == 0 {
		return fmt.Errorf("Learning applicability requires source-file and constraint-file bindings")
	}
	if len(request.sources)+len(request.constraints)+len(request.counterevidence) > 32 {
		return fmt.Errorf("Learning applicability accepts at most 32 source references")
	}
	binding := learningApplicabilityBinding{Version: learningApplicabilityVersion, Component: component, EvidenceKind: kind, Sources: []learningApplicabilityFile{}, Constraints: []learningApplicabilityFile{}, Counterevidence: []learningApplicabilityFile{}}
	for _, lane := range []struct {
		refs []string
		out  *[]learningApplicabilityFile
		owns bool
	}{{request.sources, &binding.Sources, true}, {request.constraints, &binding.Constraints, false}, {request.counterevidence, &binding.Counterevidence, false}} {
		for _, ref := range uniqueSortedTrimmed(lane.refs) {
			file, err := service.learningApplicabilityFile(ref, policy)
			if err != nil {
				return err
			}
			if lane.owns && !strings.HasPrefix(file.Path, component+"/") {
				return fmt.Errorf("Learning applicability source-file is outside its component owner")
			}
			*lane.out = append(*lane.out, file)
		}
	}
	binding.Digest = learningApplicabilityDigest(binding)
	entry["applicability_binding"] = learningApplicabilityMap(binding)
	return nil
}

func decodeLearningApplicabilityBinding(value any) (learningApplicabilityBinding, bool) {
	raw, err := json.Marshal(value)
	if err != nil || value == nil {
		return learningApplicabilityBinding{}, false
	}
	var binding learningApplicabilityBinding
	decoder := json.NewDecoder(strings.NewReader(string(raw)))
	decoder.DisallowUnknownFields()
	if decoder.Decode(&binding) != nil || binding.Version != learningApplicabilityVersion || binding.Digest == "" || binding.Digest != learningApplicabilityDigest(binding) {
		return learningApplicabilityBinding{}, false
	}
	return binding, true
}

// A recurrence is not permission to union unrelated owners or erase a recorded
// counterexample. An unbound recurrence must not reuse an older guidance binding.
func mergeLearningApplicability(existing, incoming, merged map[string]any) {
	oldBinding, oldOK := decodeLearningApplicabilityBinding(existing["applicability_binding"])
	newBinding, newOK := decodeLearningApplicabilityBinding(incoming["applicability_binding"])
	history := cloneLearningMap(mapStringAny(existing["applicability_history"]))
	digests := anyStringSlice(history["superseded_digests"])
	if oldOK {
		digests = append(digests, oldBinding.Digest)
	}
	if oldOK && newOK && oldBinding.Component != newBinding.Component {
		history["component_conflict"] = true
	}
	if newOK {
		seen := map[string]bool{}
		for _, ref := range newBinding.Counterevidence {
			seen[ref.Path] = true
		}
		for _, ref := range oldBinding.Counterevidence {
			if !seen[ref.Path] {
				newBinding.Counterevidence = append(newBinding.Counterevidence, ref)
			}
		}
		sort.Slice(newBinding.Counterevidence, func(i, j int) bool { return newBinding.Counterevidence[i].Path < newBinding.Counterevidence[j].Path })
		newBinding.Digest = learningApplicabilityDigest(newBinding)
		merged["applicability_binding"] = learningApplicabilityMap(newBinding)
	} else {
		delete(merged, "applicability_binding")
	}
	if len(digests) > 0 || len(history) > 0 {
		history["superseded_digests"] = stringsToAny(uniqueSortedTrimmed(digests))
		merged["applicability_history"] = history
	}
}

func sanitizeLearningApplicabilityWithPolicy(entry map[string]any, policy learningPolicy) {
	if entry["applicability_binding"] == nil {
		delete(entry, "applicability_binding")
	}
	if entry["applicability_history"] == nil {
		delete(entry, "applicability_history")
	}
	if raw, exists := entry["applicability_binding"]; exists {
		binding, ok := decodeLearningApplicabilityBinding(raw)
		if ok {
			if _, err := learningApplicabilityRelative(binding.Component, policy); err != nil {
				ok = false
			}
			for _, refs := range [][]learningApplicabilityFile{binding.Sources, binding.Constraints, binding.Counterevidence} {
				for _, ref := range refs {
					if _, err := learningApplicabilityRelative(ref.Path, policy); err != nil {
						ok = false
					}
				}
			}
		}
		if ok {
			entry["applicability_binding"] = learningApplicabilityMap(binding)
		} else {
			// Retain the diagnostic without echoing untrusted nested raw values.
			entry["applicability_binding"] = map[string]any{"version": learningApplicabilityVersion, "invalid": true}
		}
	}
	if raw, exists := entry["applicability_history"]; exists {
		history := mapStringAny(raw)
		safe := map[string]any{"component_conflict": history["component_conflict"] == true}
		digests := []string{}
		for _, digest := range anyStringSlice(history["superseded_digests"]) {
			if decoded, err := hex.DecodeString(digest); err == nil && len(decoded) == sha256.Size {
				digests = append(digests, digest)
			}
		}
		safe["superseded_digests"] = stringsToAny(uniqueSortedTrimmed(digests))
		entry["applicability_history"] = safe
	}
}

func (service learningService) checkLearningApplicability(entry map[string]any, context map[string][]string, policy learningPolicy) map[string]any {
	reasons := []string{}
	checks := []any{}
	state := "applicable"
	add := func(reason, severity string) {
		reasons = append(reasons, reason)
		if severity == "rejected" || state == "applicable" {
			state = severity
		}
	}
	raw, present := entry["applicability_binding"]
	binding, valid := decodeLearningApplicabilityBinding(raw)
	if !present {
		add("binding_missing", "degraded")
	} else if !valid {
		add("binding_invalid", "degraded")
	}
	if mapStringAny(entry["applicability_history"])["component_conflict"] == true {
		add("recurrence_component_conflict", "rejected")
	}
	if valid {
		component, err := learningApplicabilityRelative(binding.Component, policy)
		componentPath, pathErr := secureProjectPath(service.projectRoot, component)
		info, statErr := os.Stat(componentPath)
		if err != nil || pathErr != nil || statErr != nil || !info.IsDir() {
			add("component_unavailable", "rejected")
		}
		if len(context["components"]) == 0 {
			add("task_component_missing", "degraded")
		} else if len(context["components"]) != 1 || context["components"][0] != binding.Component {
			add("component_mismatch", "rejected")
		}
		if len(binding.Sources) == 0 || len(binding.Constraints) == 0 || len(binding.Sources)+len(binding.Constraints)+len(binding.Counterevidence) > 32 || (binding.EvidenceKind != "failure" && binding.EvidenceKind != "recovery" && binding.EvidenceKind != "correction" && binding.EvidenceKind != "constraint") {
			add("binding_incomplete", "degraded")
		}
		for _, lane := range []struct {
			kind string
			refs []learningApplicabilityFile
		}{{"source", binding.Sources}, {"constraint", binding.Constraints}, {"counterevidence", binding.Counterevidence}} {
			if len(lane.refs) > 32 {
				continue
			}
			for _, captured := range lane.refs {
				if lane.kind == "source" && !strings.HasPrefix(captured.Path, binding.Component+"/") {
					add("source_owner_mismatch", "rejected")
				}
				current, err := service.learningApplicabilityFile(captured.Path, policy)
				check := map[string]any{"kind": lane.kind, "path": captured.Path, "captured_sha256": captured.SHA256, "captured_bytes": captured.Bytes, "matches": false}
				if err != nil {
					add(lane.kind+"_unavailable", "degraded")
				} else {
					matches := current.SHA256 == captured.SHA256 && current.Bytes == captured.Bytes
					check["current_sha256"], check["current_bytes"], check["matches"] = current.SHA256, current.Bytes, matches
					if !matches {
						add(lane.kind+"_changed", "rejected")
						if lane.kind == "source" && binding.EvidenceKind == "failure" {
							add("failed_evidence_source_changed", "rejected")
						}
					}
					if lane.kind == "counterevidence" {
						add("counterevidence_present", "rejected")
					}
				}
				checks = append(checks, check)
			}
		}
		if requested := uniqueSortedTrimmed(context["constraint_files"]); len(requested) > 0 {
			captured := []string{}
			for _, ref := range binding.Constraints {
				captured = append(captured, ref.Path)
			}
			if strings.Join(requested, "\n") != strings.Join(uniqueSortedTrimmed(captured), "\n") {
				add("constraint_context_mismatch", "rejected")
			}
		}
	}
	requestedCounterevidence := uniqueSortedTrimmed(context["counterevidence_files"])
	if len(requestedCounterevidence) > 32 {
		add("task_counterevidence_limit_exceeded", "degraded")
		requestedCounterevidence = requestedCounterevidence[:32]
	}
	for _, ref := range requestedCounterevidence {
		current, err := service.learningApplicabilityFile(ref, policy)
		if err != nil {
			add("task_counterevidence_unverifiable", "degraded")
		} else {
			add("task_counterevidence_present", "rejected")
			checks = append(checks, map[string]any{"kind": "task_counterevidence", "path": current.Path, "current_sha256": current.SHA256, "current_bytes": current.Bytes})
		}
	}
	return map[string]any{"version": learningApplicabilityVersion, "state": state, "applicable": state == "applicable", "reason_codes": stringsToAny(uniqueSortedTrimmed(reasons)), "binding_digest": binding.Digest, "checks": checks, "read_only": true}
}

func learningApplicabilityRank(card map[string]any) int {
	switch mapStringAny(card["applicability"])["state"] {
	case "applicable":
		return 0
	case "rejected":
		return 2
	default:
		return 1
	}
}

func compactLearningApplicability(proof map[string]any) map[string]any {
	compact := cloneLearningMap(proof)
	delete(compact, "checks")
	return compact
}

func degradeLearningApplicability(proof map[string]any, reason string) {
	if proof["state"] != "rejected" {
		proof["state"] = "degraded"
	}
	proof["applicable"] = false
	proof["reason_codes"] = stringsToAny(uniqueSortedTrimmed(append(anyStringSlice(proof["reason_codes"]), reason)))
}

func learningApplicabilityProjectionMatches(left, right map[string]any) bool {
	leftRaw, _ := json.Marshal([]any{left["applicability_binding"], left["applicability_history"]})
	rightRaw, _ := json.Marshal([]any{right["applicability_binding"], right["applicability_history"]})
	return string(leftRaw) == string(rightRaw)
}

func rejectLearningApplicability(proof map[string]any, reason string) {
	degradeLearningApplicability(proof, reason)
	proof["state"] = "rejected"
}

// Candidate annotations and expanded details may carry a different entry from
// the winning lifecycle layer. Every read must also honor that catalog join.
func (service learningService) catalogLearningApplicability(item learningCatalogItem, entry map[string]any, context map[string][]string, policy learningPolicy) map[string]any {
	proof := service.checkLearningApplicability(firstNonNilLearningEntry(entry, item.indexEntry), context, policy)
	if entry == nil || item.entry == nil {
		degradeLearningApplicability(proof, "record_evidence_missing")
	} else if !learningApplicabilityProjectionMatches(entry, item.indexEntry) || !learningApplicabilityProjectionMatches(entry, item.entry) {
		degradeLearningApplicability(proof, "binding_projection_mismatch")
	}
	if item.bindingConflict {
		rejectLearningApplicability(proof, "lifecycle_binding_conflict")
	}
	return proof
}
