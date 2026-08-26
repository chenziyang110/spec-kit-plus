package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scanartifacts"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/update"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/validation"
)

const identityRepairPlanVersion = 1

type identityRepairDiff struct {
	MissingScan  []string `json:"missing_scan"`
	UnexpectedDB []string `json:"unexpected_db"`
}

type identityPathRepair struct {
	Path       string `json:"path"`
	NodeID     string `json:"node_id"`
	EvidenceID string `json:"evidence_id"`
	Relation   string `json:"relation"`
	Confidence string `json:"confidence"`
}

type identityRepairPlan struct {
	Version          int                  `json:"version"`
	ID               string               `json:"id"`
	GenerationID     string               `json:"generation_id"`
	Repairability    string               `json:"repairability"`
	ValidationDigest string               `json:"validation_digest"`
	Repairs          []identityPathRepair `json:"repairs"`
	CreatedAt        string               `json:"created_at"`
}

func runCognitionIdentityRepairCLI(args []string, stdout io.Writer) int {
	if len(args) == 0 {
		return writeEnvelope(stdout, usageEnvelope("cognition identity-repair requires plan or apply"))
	}
	switch strings.ToLower(strings.TrimSpace(args[0])) {
	case "plan":
		return runCognitionIdentityRepairPlan(args[1:], stdout)
	case "apply":
		return runCognitionIdentityRepairApply(args[1:], stdout)
	default:
		return writeEnvelope(stdout, usageEnvelope("cognition identity-repair requires plan or apply"))
	}
}

func runCognitionIdentityRepairPlan(args []string, stdout io.Writer) int {
	paths, err := rt.ResolvePaths(optionValue(args, "--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	gate := validation.ValidateBuild(paths)
	repairability := strings.TrimSpace(fmt.Sprint(gate.Details["identity_repairability"]))
	if repairability != "bounded_path_repair" && repairability != "bounded_path_identity_review" {
		return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("identity repair is not bounded: %s", repairability)))
	}
	diffs, digest, err := identityRepairDiffs(gate)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	repairs, err := identityPathRepairsFromGate(paths, gate, diffs)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	if len(repairs) == 0 {
		return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("identity repair plan has no supported repairs")))
	}
	generationID := strings.TrimSpace(fmt.Sprint(gate.Details["active_generation_id"]))
	planIDSum := sha256.Sum256([]byte(generationID + "\x00" + digest))
	plan := identityRepairPlan{
		Version: identityRepairPlanVersion, ID: fmt.Sprintf("identity-repair-%x", planIDSum[:10]), GenerationID: generationID,
		Repairability: repairability, ValidationDigest: digest, Repairs: repairs, CreatedAt: time.Now().UTC().Format(time.RFC3339Nano),
	}
	planPath := filepath.Join(paths.RuntimeDir, "identity-repair", "plans", plan.ID+".json")
	if err := writeScriptJSONFile(planPath, plan); err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	raw, err := os.ReadFile(planPath)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	planSHA := fmt.Sprintf("%x", sha256.Sum256(raw))
	planRef := closeoutIntentRef(paths, planPath)
	env := NewEnvelope("ok", "bounded project cognition identity repair planned")
	env.Data = map[string]any{
		"status": "planned", "repairability": repairability, "repair_count": len(repairs), "plan_ref": planRef, "plan_sha256": planSHA,
		"apply_argv": []string{"specify-runtime", "cognition", "identity-repair", "apply", "--plan-ref", planRef, "--plan-sha256", planSHA, "--format", "json"},
	}
	return writeEnvelope(stdout, env)
}

func runCognitionIdentityRepairApply(args []string, stdout io.Writer) int {
	paths, err := rt.ResolvePaths(optionValue(args, "--project-root", "."))
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	planPath, err := resolveIdentityRepairPlanPath(paths, optionValue(args, "--plan-ref", ""))
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	raw, err := os.ReadFile(planPath)
	if err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	wantSHA := strings.TrimSpace(optionValue(args, "--plan-sha256", ""))
	gotSHA := fmt.Sprintf("%x", sha256.Sum256(raw))
	if len(wantSHA) != 64 || gotSHA != wantSHA {
		return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("identity repair plan digest mismatch")))
	}
	var plan identityRepairPlan
	if err := json.Unmarshal(raw, &plan); err != nil || plan.Version != identityRepairPlanVersion || len(plan.Repairs) == 0 {
		return writeEnvelope(stdout, scriptDomainError("cognition", fmt.Errorf("identity repair plan is invalid")))
	}
	var after validation.GatePayload
	if err := update.WithLockedRuntime(paths, func(_ *update.LockedRuntime) error {
		gate := validation.ValidateBuild(paths)
		diffs, currentDigest, err := identityRepairDiffs(gate)
		if err != nil || currentDigest != plan.ValidationDigest || strings.TrimSpace(fmt.Sprint(gate.Details["active_generation_id"])) != plan.GenerationID {
			return fmt.Errorf("identity repair plan is stale; rerun plan")
		}
		expectedRepairs, err := identityPathRepairsFromGate(paths, gate, diffs)
		if err != nil {
			return err
		}
		expectedRaw, _ := json.Marshal(expectedRepairs)
		actualRaw, _ := json.Marshal(plan.Repairs)
		if !bytes.Equal(expectedRaw, actualRaw) {
			return fmt.Errorf("identity repair plan contents do not match current scan-backed repair")
		}
		st, err := store.OpenExisting(paths)
		if err != nil {
			return err
		}
		defer st.Close()
		repairs := make([]store.PathCoverageRestore, 0, len(plan.Repairs))
		for _, repair := range plan.Repairs {
			repairs = append(repairs, store.PathCoverageRestore{
				Path: repair.Path, NodeID: repair.NodeID, EvidenceID: repair.EvidenceID, Relation: repair.Relation, Confidence: repair.Confidence,
			})
		}
		if err := st.RestorePathCoverageBatch(context.Background(), plan.GenerationID, repairs); err != nil {
			return err
		}
		after = validation.ValidateBuild(paths)
		if after.Status != "ok" || after.Readiness != rt.ReadyReadiness {
			return fmt.Errorf("identity repair did not restore query readiness: %s", strings.Join(after.Errors, "; "))
		}
		return nil
	}); err != nil {
		return writeEnvelope(stdout, scriptDomainError("cognition", err))
	}
	env := NewEnvelope("ok", "bounded project cognition identity repair applied")
	env.Data = map[string]any{"status": "repaired", "readiness": after.Readiness, "repair_count": len(plan.Repairs), "plan_ref": closeoutIntentRef(paths, planPath)}
	return writeEnvelope(stdout, env)
}

func identityRepairDiffs(gate validation.GatePayload) (map[string]identityRepairDiff, string, error) {
	raw, err := json.Marshal(gate.Details["identity_diffs"])
	if err != nil {
		return nil, "", err
	}
	diffs := map[string]identityRepairDiff{}
	if err := json.Unmarshal(raw, &diffs); err != nil {
		return nil, "", err
	}
	digest := sha256.Sum256(raw)
	return diffs, fmt.Sprintf("%x", digest[:]), nil
}

func identityPathRepairsFromGate(paths rt.Paths, gate validation.GatePayload, diffs map[string]identityRepairDiff) ([]identityPathRepair, error) {
	for category, diff := range diffs {
		if len(diff.UnexpectedDB) > 0 || (category != "coverage_path" && len(diff.MissingScan) > 0) {
			return nil, fmt.Errorf("bounded automatic repair supports only missing coverage_path identities; category %s requires review", category)
		}
	}
	pkg, scanResult := scanartifacts.Load(paths, scanartifacts.ValidateOptions{RequireStatusJSON: false})
	if scanResult.Status != "ok" {
		return nil, fmt.Errorf("scan package is not repairable: %s", strings.Join(scanResult.Errors, "; "))
	}
	repairs := []identityPathRepair{}
	for _, path := range diffs["coverage_path"].MissingScan {
		candidates := []scanartifacts.NodeRow{}
		for _, node := range pkg.Nodes {
			if containsIdentityRepairPath(node.Paths, path) || containsIdentityRepairPath(node.CanonicalPaths, path) || containsIdentityRepairPath(node.CompatibilityPaths, path) {
				candidates = append(candidates, node)
			}
		}
		if len(candidates) != 1 || len(candidates[0].EvidenceIDs) == 0 {
			return nil, fmt.Errorf("coverage path %s does not have one scan-backed node/evidence identity", path)
		}
		repairs = append(repairs, identityPathRepair{
			Path: path, NodeID: candidates[0].ID, EvidenceID: candidates[0].EvidenceIDs[0], Relation: "owns", Confidence: "partial",
		})
	}
	sort.Slice(repairs, func(i, j int) bool { return repairs[i].Path < repairs[j].Path })
	return repairs, nil
}

func resolveIdentityRepairPlanPath(paths rt.Paths, ref string) (string, error) {
	ref = strings.TrimSpace(ref)
	if ref == "" {
		return "", fmt.Errorf("--plan-ref is required")
	}
	path := ref
	if !filepath.IsAbs(path) {
		path = filepath.Join(paths.Root, filepath.FromSlash(ref))
	}
	path = filepath.Clean(path)
	rel, err := filepath.Rel(paths.Root, path)
	if err != nil || rel == ".." || strings.HasPrefix(filepath.ToSlash(rel), "../") {
		return "", fmt.Errorf("identity repair plan must stay within project root")
	}
	return path, nil
}

func containsIdentityRepairPath(values []string, want string) bool {
	want = filepath.ToSlash(strings.TrimSpace(want))
	for _, value := range values {
		if filepath.ToSlash(strings.TrimSpace(value)) == want {
			return true
		}
	}
	return false
}
