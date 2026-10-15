package main

// This opt-in test helper bootstraps an isolated evaluation fixture through the
// native import/publication owners. It is not a new production CLI or evidence
// that any user's existing map has been repaired.

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/claim"
	rt "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/runtime"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

type cognitionLoopFixtureMarker struct {
	Schema          string                             `json:"schema"`
	Root            string                             `json:"root"`
	Nonce           string                             `json:"nonce"`
	ManagedSources  []string                           `json:"managed_sources"`
	OriginalSources map[string]cognitionLoopSourceFact `json:"original_sources"`
}

type cognitionLoopSourceFact struct {
	SHA256 string `json:"sha256"`
	Bytes  int    `json:"bytes"`
}

func cognitionLoopSourceFactOf(data []byte) cognitionLoopSourceFact {
	hash := sha256.Sum256(data)
	return cognitionLoopSourceFact{hex.EncodeToString(hash[:]), len(data)}
}

func cognitionLoopFixtureRoot(raw string) (string, cognitionLoopFixtureMarker, error) {
	var marker cognitionLoopFixtureMarker
	root, err := filepath.Abs(raw)
	if err != nil || raw == "" || !strings.HasPrefix(filepath.Base(root), "loop-fixture-") {
		return "", marker, fmt.Errorf("only a dedicated loop-fixture target is allowed")
	}
	resolved, err := filepath.EvalSymlinks(root)
	if err != nil || resolved != root {
		return "", marker, fmt.Errorf("fixture target missing or redirected")
	}
	data, err := os.ReadFile(filepath.Join(root, ".cognition-loop-fixture.json"))
	if err != nil {
		return "", marker, fmt.Errorf("fixture marker required: %w", err)
	}
	if err := json.Unmarshal(data, &marker); err != nil {
		return "", marker, err
	}
	if marker.Schema != "cognition-loop-isolated-fixture.v1" || marker.Root != root || len(marker.Nonce) != 32 || len(marker.ManagedSources) == 0 {
		return "", marker, fmt.Errorf("fixture marker identity mismatch")
	}
	if _, err := hex.DecodeString(marker.Nonce); err != nil {
		return "", marker, fmt.Errorf("invalid fixture nonce")
	}
	if _, err := os.Lstat(filepath.Join(root, ".specify", "project-cognition")); !os.IsNotExist(err) {
		return "", marker, fmt.Errorf("existing cognition target is protected; create a fresh fixture")
	}
	return root, marker, nil
}

func TestCognitionLoopFixtureNativeImport(t *testing.T) {
	requested := os.Getenv("SPECIFY_COGNITION_LOOP_FIXTURE")
	batch := os.Getenv("SPECIFY_COGNITION_LOOP_FIXTURES_JSON")
	if requested == "" && batch == "" {
		t.Skip("opt-in fixture bootstrap only; not a product acceptance row")
	}
	if requested != "" && batch != "" {
		t.Fatal("select one explicit fixture or a bounded explicit fixture batch")
	}
	if batch != "" {
		var roots []string
		if err := json.Unmarshal([]byte(batch), &roots); err != nil || len(roots) == 0 || len(roots) > 128 {
			t.Fatal("fixture batch must be a bounded JSON array of at most 128 explicit roots")
		}
		seen := map[string]bool{}
		for index, root := range roots {
			if seen[root] {
				t.Fatal("duplicate fixture root in native bootstrap batch")
			}
			seen[root] = true
			t.Run(fmt.Sprintf("fixture-%03d", index), func(t *testing.T) { seedCognitionLoopFixture(t, root) })
		}
		return
	}
	seedCognitionLoopFixture(t, requested)
}

func seedCognitionLoopFixture(t *testing.T, requested string) {
	t.Helper()
	root, marker, err := cognitionLoopFixtureRoot(requested)
	if err != nil {
		t.Fatal(err)
	}
	python := os.Getenv("SPECIFY_COGNITION_LOOP_PYTHON")
	if !filepath.IsAbs(python) {
		t.Fatal("an explicit absolute Python executable is required for actual baseline verification")
	}
	proofDir := filepath.Join(root, ".cognition-loop-bootstrap")
	if err := os.Mkdir(proofDir, 0o755); err != nil {
		t.Fatal(err)
	}
	nativeCalls := []map[string]any{}
	run := func(argv []string) []byte {
		index := len(nativeCalls)
		started := time.Now()
		cmd := exec.Command(argv[0], argv[1:]...)
		cmd.Dir = root
		var stdout, stderr strings.Builder
		cmd.Stdout, cmd.Stderr = &stdout, &stderr
		callErr := cmd.Run()
		ended := time.Now()
		stdoutName, stderrName := fmt.Sprintf("call-%02d.stdout", index), fmt.Sprintf("call-%02d.stderr", index)
		for name, content := range map[string]string{stdoutName: stdout.String(), stderrName: stderr.String()} {
			if err := os.WriteFile(filepath.Join(proofDir, name), []byte(content), 0o644); err != nil {
				t.Fatal(err)
			}
		}
		exitCode := -1
		if cmd.ProcessState != nil {
			exitCode = cmd.ProcessState.ExitCode()
		}
		nativeCalls = append(nativeCalls, map[string]any{"argv": argv, "cwd": root, "started_at": started.UTC().Format(time.RFC3339Nano), "ended_at": ended.UTC().Format(time.RFC3339Nano), "exit_code": exitCode, "stdout": filepath.Join(proofDir, stdoutName), "stderr": filepath.Join(proofDir, stderrName), "error": fmt.Sprint(callErr)})
		if callErr != nil {
			t.Fatalf("actual baseline verification %v failed: %v; %s", argv, callErr, stderr.String())
		}
		return []byte(stdout.String())
	}
	commit := strings.TrimSpace(string(run([]string{"git", "rev-parse", "HEAD"})))
	input := store.ImportInput{GenerationID: "GEN-loop-" + marker.Nonce, Kind: "full", SourceCommit: commit}
	required := []string{"build.py", "src/__init__.py", "src/config.json", "src/consumer.py", "src/generated.txt", "src/legacy.py", "src/service.py", "templates/service.txt", "tests/test_service.py", "tools/generate.py"}
	if strings.Join(marker.ManagedSources, "\n") != strings.Join(required, "\n") || len(marker.OriginalSources) != len(required) {
		t.Fatal("native seed requires all ten frozen original source facts")
	}
	readSources := func() map[string]cognitionLoopSourceFact {
		facts := map[string]cognitionLoopSourceFact{}
		for _, name := range required {
			path := filepath.Join(root, filepath.FromSlash(name))
			resolved, resolveErr := filepath.EvalSymlinks(path)
			if resolveErr != nil || resolved != path {
				t.Fatalf("source missing or redirected: %s", name)
			}
			data, readErr := os.ReadFile(path)
			if readErr != nil {
				t.Fatal(readErr)
			}
			facts[name] = cognitionLoopSourceFactOf(data)
			if facts[name] != marker.OriginalSources[name] {
				t.Fatalf("source differs from frozen original byte facts: %s", name)
			}
		}
		return facts
	}
	beforeSources := readSources()
	committedSources := map[string]cognitionLoopSourceFact{}
	for _, name := range required {
		committedSources[name] = cognitionLoopSourceFactOf(run([]string{"git", "cat-file", "blob", commit + ":" + name}))
		if committedSources[name] != beforeSources[name] {
			t.Fatalf("committed source differs from original fixture bytes: %s", name)
		}
	}
	for _, argv := range [][]string{{python, "-m", "unittest", "discover", "-s", "tests", "-p", "test_service.py"}, {python, "tools/generate.py"}, {python, "build.py"}} {
		run(argv)
	}
	afterSources := readSources()
	if current := strings.TrimSpace(string(run([]string{"git", "rev-parse", "HEAD"}))); current != commit {
		t.Fatal("native verification changed the frozen source commit")
	}
	for _, name := range required {
		if current := cognitionLoopSourceFactOf(run([]string{"git", "cat-file", "blob", "HEAD:" + name})); current != afterSources[name] {
			t.Fatalf("post-generator source is not exactly bound to current committed bytes: %s", name)
		}
	}
	nodeIDs, evidenceIDs := map[string]string{}, map[string]string{}
	coverage := []map[string]string{}
	for index, name := range marker.ManagedSources {
		if name == "" || strings.Contains(name, "\\") || strings.Contains(name, ":") || filepath.IsAbs(name) || strings.HasPrefix(name, ".") || strings.Contains("/"+name+"/", "/../") {
			t.Fatalf("managed source outside explicit fixture boundary: %q", name)
		}
		path := filepath.Join(root, filepath.FromSlash(name))
		resolved, resolveErr := filepath.EvalSymlinks(path)
		if resolveErr != nil || resolved != path {
			t.Fatalf("managed source missing or redirected: %s", name)
		}
		data, readErr := os.ReadFile(path)
		if readErr != nil {
			t.Fatal(readErr)
		}
		digest := sha256.Sum256(data)
		evidenceID, nodeID := fmt.Sprintf("E-loop-%03d", index), fmt.Sprintf("N-loop-%03d", index)
		nodeIDs[name], evidenceIDs[name] = nodeID, evidenceID
		input.Evidence = append(input.Evidence, store.EvidenceImport{ID: evidenceID, SourceKind: "file", SourcePath: name, CommitSHA: input.SourceCommit, ContentHash: hex.EncodeToString(digest[:]), Extractor: "cognition-loop-fixture-test.v2"})
		input.Nodes = append(input.Nodes, store.NodeImport{ID: nodeID, Type: "component", Title: "Loop fixture " + name, Confidence: "supported", EvidenceIDs: []string{evidenceID}})
		input.PathIndex = append(input.PathIndex, store.PathIndexImport{ID: fmt.Sprintf("P-loop-%03d", index), Path: name, NodeID: nodeID, Relation: "owns", Confidence: "supported", EvidenceID: evidenceID})
		input.Aliases = append(input.Aliases, store.AliasImport{ID: fmt.Sprintf("A-loop-%03d", index), Alias: name, NormalizedAlias: strings.ToLower(name), TargetType: "node", TargetID: nodeID, Source: "node_path", Confidence: "supported", EvidenceID: evidenceID})
		coverage = append(coverage, map[string]string{"path": name, "status": "covered"})
	}
	for index, relation := range [][3]string{
		{"calls", "src/consumer.py", "src/service.py"}, {"reads_config", "src/consumer.py", "src/config.json"},
		{"calls", "src/consumer.py", "src/legacy.py"}, {"calls", "src/legacy.py", "src/service.py"},
		{"verifies", "tests/test_service.py", "src/service.py"}, {"verifies", "tests/test_service.py", "src/consumer.py"},
		{"reads_template", "tools/generate.py", "templates/service.txt"}, {"generates", "tools/generate.py", "src/generated.txt"},
		{"packages", "build.py", "src/service.py"},
	} {
		if nodeIDs[relation[1]] == "" || nodeIDs[relation[2]] == "" {
			t.Fatal("fixture is missing an actual relationship endpoint")
		}
		input.Edges = append(input.Edges, store.EdgeImport{ID: fmt.Sprintf("EDGE-loop-%02d", index), Type: relation[0], SourceID: nodeIDs[relation[1]], TargetID: nodeIDs[relation[2]], Confidence: "supported", EvidenceIDs: []string{evidenceIDs[relation[1]], evidenceIDs[relation[2]]}})
	}
	verificationData, err := json.Marshal(nativeCalls)
	if err != nil {
		t.Fatal(err)
	}
	verificationPath := filepath.Join(proofDir, "verification.json")
	if err := os.WriteFile(verificationPath, append(verificationData, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
	verificationHash := sha256.Sum256(append(verificationData, '\n'))
	input.Evidence = append(input.Evidence, store.EvidenceImport{ID: "E-loop-baseline-verification", SourceKind: "command_result", SourcePath: ".cognition-loop-bootstrap/verification.json", ContentHash: hex.EncodeToString(verificationHash[:]), Extractor: "actual_python_test_generate_build"})
	for _, fact := range []struct {
		id, path, kind, summary string
		sources                 []string
		verified                bool
	}{
		{"C-loop-service-positive", "src/service.py", "interface", "charge(amount, rate=0.1) rounds the fee; charge(100)=10. Negative rejection is not claimed.", []string{"src/service.py", "tests/test_service.py"}, true},
		{"C-loop-consumer-config", "src/consumer.py", "consumer", "invoice reads config.json rate and calls charge(amount, configured_rate).", []string{"src/consumer.py", "src/config.json", "tests/test_service.py"}, true},
		{"C-loop-legacy-call", "src/legacy.py", "consumer", "legacy_invoice calls old_charge in legacy.py, which calls service.charge.", []string{"src/consumer.py", "src/legacy.py", "tests/test_service.py"}, true},
		{"C-loop-generated-chain", "tools/generate.py", "generation", "generate.py reads service.txt and writes generated.txt with identical content.", []string{"tools/generate.py", "templates/service.txt", "src/generated.txt"}, false},
		{"C-loop-test-route", "tests/test_service.py", "verification", "unittest discovery runs positive service, invoice and legacy_invoice regressions.", []string{"tests/test_service.py", "src/service.py", "src/consumer.py", "src/legacy.py"}, true},
		{"C-loop-build-route", "build.py", "packaging", "build.py packages src files and verifies the resulting ZIP.", []string{"build.py", "src/service.py"}, true},
		{"C-loop-legacy-path", "src/legacy.py", "owner", "src/legacy.py currently owns old_charge and its path alias; callers depend on this live path.", []string{"src/legacy.py", "src/consumer.py"}, false},
	} {
		support := []string{}
		for _, name := range fact.sources {
			support = append(support, evidenceIDs[name])
		}
		item := store.ClaimImport{ID: fact.id, NodeID: nodeIDs[fact.path], GraphClaimType: fact.kind, Summary: fact.summary, State: claim.StateSupported, Freshness: claim.FreshnessFresh, StateReason: "source_bound_fixture_baseline", SupportingEvidenceIDs: support}
		if fact.verified {
			item.State = claim.StateVerified
			item.Verifications = []store.ClaimVerificationImport{{ID: "V-" + fact.id, Result: claim.VerificationPassed, Command: "native fixture baseline test/generate/build; inspect exact argv in verification evidence", EvidenceID: "E-loop-baseline-verification", ObservedAt: time.Now().UTC().Format(time.RFC3339Nano)}}
		}
		input.Claims = append(input.Claims, item)
	}
	if err := os.MkdirAll(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	st, err := store.Open(paths)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	if _, err := st.ImportGeneration(context.Background(), input); err != nil {
		t.Fatal(err)
	}
	if _, _, err := st.PublishRuntimeMetadata(context.Background(), input.GenerationID, rt.BaselineKindBrownfieldFull); err != nil {
		t.Fatal(err)
	}
	claimRows, err := st.ClaimsForNodeIDs(context.Background(), func() []string {
		ids := []string{}
		for _, node := range input.Nodes {
			ids = append(ids, node.ID)
		}
		return ids
	}())
	if err != nil || len(claimRows) != 7 {
		t.Fatalf("native imported claims missing: %v, rows=%d", err, len(claimRows))
	}
	status := rt.DefaultStatus(paths)
	status.Status, status.Freshness, status.Readiness = "ok", rt.ReadyFreshness, rt.ReadyReadiness
	status.GraphReady, status.ActiveGenerationID, status.BaselineKind = true, input.GenerationID, rt.BaselineKindBrownfieldFull
	status.RecommendedNextAction = "use_project_cognition"
	if err := rt.WriteStatus(paths, status); err != nil {
		t.Fatal(err)
	}
	for name, value := range map[string]any{
		"capability-ledger.json": map[string]any{"rows": []any{}},
		"control-ledger.json":    map[string]any{"rows": []any{}},
		"coverage-ledger.json":   map[string]any{"rows": coverage, "open_gaps": []any{}},
	} {
		target := filepath.Join(paths.RuntimeDir, "workbench", name)
		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			t.Fatal(err)
		}
		raw, marshalErr := json.Marshal(value)
		if marshalErr != nil {
			t.Fatal(marshalErr)
		}
		if err := os.WriteFile(target, append(raw, '\n'), 0o644); err != nil {
			t.Fatal(err)
		}
	}
	proof, err := json.Marshal(map[string]any{"schema": "cognition-loop-native-seed.v3", "root": root, "generation": input.GenerationID, "source_commit": input.SourceCommit, "original_sources": marker.OriginalSources, "source_before": beforeSources, "source_after_generator_build": afterSources, "committed_sources": committedSources, "input": input, "claims_read_back": claimRows, "native_calls": nativeCalls, "status": status, "restriction": "bootstrap only; actors/candidate closeout must not use full import as local semantic registration"})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(proofDir, "seed-proof.json"), append(proof, '\n'), 0o644); err != nil {
		t.Fatal(err)
	}
	fmt.Printf("COGNITION_LOOP_FIXTURE={\"root\":%q,\"generation\":%q,\"managed_sources\":%d,\"edges\":%d,\"claims\":%d,\"bootstrap_owner\":\"native_store_import_and_runtime_metadata\",\"semantic_truth\":\"independent_live_source_required\"}\n", root, input.GenerationID, len(marker.ManagedSources), len(input.Edges), len(input.Claims))
}

func TestCognitionLoopFixtureRefusesSourceRepositoryAndExistingTargets(t *testing.T) {
	for _, root := range []string{"", ".", "..", t.TempDir()} {
		if _, _, err := cognitionLoopFixtureRoot(root); err == nil {
			t.Fatalf("unsafe fixture target accepted: %q", root)
		}
	}
	root := filepath.Join(t.TempDir(), "loop-fixture-protected")
	if err := os.MkdirAll(filepath.Join(root, ".specify", "project-cognition"), 0o755); err != nil {
		t.Fatal(err)
	}
	raw, err := json.Marshal(cognitionLoopFixtureMarker{Schema: "cognition-loop-isolated-fixture.v1", Root: root, Nonce: strings.Repeat("a", 32), ManagedSources: []string{"src/app.py"}})
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(root, ".cognition-loop-fixture.json"), raw, 0o644); err != nil {
		t.Fatal(err)
	}
	if _, _, err := cognitionLoopFixtureRoot(root); err == nil {
		t.Fatal("existing cognition store target was accepted")
	}
}
