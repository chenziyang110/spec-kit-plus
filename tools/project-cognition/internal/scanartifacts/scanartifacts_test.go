package scanartifacts

import (
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"testing"

	rt "github.com/chenziyang110/spec-kit-plus/tools/project-cognition/internal/runtime"
)

func TestValidateArtifactsDoesNotRequireStatusJSON(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
	if !containsString(result.CheckedPaths, ".specify/project-cognition/workbench/repository-universe.json") {
		t.Fatalf("CheckedPaths = %#v, want repository-universe.json", result.CheckedPaths)
	}
	for _, checked := range result.CheckedPaths {
		if strings.Contains(checked, ".specify/project-map") {
			t.Fatalf("CheckedPaths = %#v, must not include .specify/project-map", result.CheckedPaths)
		}
	}
}

func TestValidateArtifactsReportsUTF8BOM(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "coverage.json"), append([]byte{0xEF, 0xBB, 0xBF}, []byte(`{"rows":[{"path":"src/app.go"}]}`)...))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "coverage.json contains UTF-8 BOM") {
		t.Fatalf("Errors = %#v, want UTF-8 BOM error", result.Errors)
	}
}

func TestValidateArtifactsRequiresStatusJSONObjectWhenRequested(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "status.json"), []byte("[]\n"))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: true})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "status.json must contain a top-level JSON object") {
		t.Fatalf("Errors = %#v, want status object error", result.Errors)
	}
}

func TestLoadExtractsIdentitySets(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)

	pkg, result := Load(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
	assertIdentity(t, pkg.Identities.Evidence, "E-001|src/app.go|hash-app")
	assertIdentity(t, pkg.Identities.Nodes, "N-app")
	assertIdentity(t, pkg.Identities.Edges, "EDGE-app-self|N-app|N-app|owns")
	assertIdentity(t, pkg.Identities.Observations, "OBS-app")
	assertIdentity(t, pkg.Identities.CoveragePaths, "src/app.go")
}

func TestValidateArtifactsBlocksOpenGapForAnyOwner(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go"}],
		"open_gaps":[{"owner":"other","status":"blocked"}]
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "coverage gap must be resolved") {
		t.Fatalf("Errors = %#v, want blocked coverage gap error", result.Errors)
	}
}

func TestLoadFallbackContentHashUsesNormalizedEvidenceObject(t *testing.T) {
	first := fallbackEvidenceIdentityForSourcePath(t, `./src\app.go`)
	second := fallbackEvidenceIdentityForSourcePath(t, `src/app.go`)

	if first != second {
		t.Fatalf("fallback evidence identities differ:\nfirst:  %s\nsecond: %s", first, second)
	}
}

func scanArtifactTestPaths(t *testing.T) rt.Paths {
	t.Helper()
	root := t.TempDir()
	if err := os.Mkdir(filepath.Join(root, ".specify"), 0o755); err != nil {
		t.Fatal(err)
	}
	paths, err := rt.ResolvePaths(root)
	if err != nil {
		t.Fatal(err)
	}
	return paths
}

func fallbackEvidenceIdentityForSourcePath(t *testing.T, sourcePath string) string {
	t.Helper()
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "evidence", "E-001.json"), []byte(`{
		"id":"E-001",
		"source_kind":" file ",
		"source_path":`+strconv.Quote(sourcePath)+`,
		"commit_sha":" abc123 ",
		"span":" L1-L5 ",
		"extractor":" test ",
		"attrs":{"language":"go"}
	}`))

	pkg, result := Load(paths, ValidateOptions{RequireStatusJSON: false})
	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
	for identity := range pkg.Identities.Evidence {
		return identity
	}
	t.Fatal("missing evidence identity")
	return ""
}

func writeMinimalScanPackage(t *testing.T, paths rt.Paths) {
	t.Helper()
	files := map[string]string{
		filepath.Join(paths.RuntimeDir, "evidence", "E-001.json"): `{
			"id":"E-001",
			"source_kind":"file",
			"source_path":"src/app.go",
			"commit_sha":"abc123",
			"span":"L1-L5",
			"extractor":"test",
			"content_hash":"hash-app",
			"attrs":{"language":"go"}
		}`,
		filepath.Join(paths.RuntimeDir, "provisional", "nodes.json"): `{"nodes":[{
			"id":"N-app",
			"type":"capability",
			"title":"App",
			"confidence":"verified",
			"paths":["src/app.go"],
			"evidence_ids":["E-001"],
			"attrs":{"owner":"app"}
		}]}`,
		filepath.Join(paths.RuntimeDir, "provisional", "edges.json"): `{"edges":[{
			"id":"EDGE-app-self",
			"type":"owns",
			"source_id":"N-app",
			"target_id":"N-app",
			"confidence":"verified",
			"evidence_ids":["E-001"],
			"attrs":{"relation":"self"}
		}]}`,
		filepath.Join(paths.RuntimeDir, "provisional", "observations.json"): `{"observations":[{
			"id":"OBS-app",
			"observation_type":"implementation",
			"summary":"App exists",
			"evidence_ids":["E-001"],
			"attrs":{"source":"test"}
		}]}`,
		filepath.Join(paths.RuntimeDir, "coverage.json"):                          `{"rows":[{"path":"src/app.go"}]}`,
		filepath.Join(paths.RuntimeDir, "workbench", "map-scan.md"):               `# Map Scan`,
		filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.md"):        `# Coverage Ledger`,
		filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"):      `{"rows":[{"path":"src/app.go"}],"open_gaps":[]}`,
		filepath.Join(paths.RuntimeDir, "workbench", "scan-packets", "lane-1.md"): `# Lane 1`,
		filepath.Join(paths.RuntimeDir, "workbench", "map-state.md"):              `# Map State`,
		filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"):  `{"rows":[{"path":"src/app.go"}]}`,
		filepath.Join(paths.RuntimeDir, "workbench", "capability-ledger.json"):    `{"rows":[]}`,
		filepath.Join(paths.RuntimeDir, "workbench", "control-ledger.json"):       `{"rows":[]}`,
	}
	for path, content := range files {
		writeFileBytes(t, path, []byte(content+"\n"))
	}
}

func writeFileBytes(t *testing.T, path string, content []byte) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, content, 0o644); err != nil {
		t.Fatal(err)
	}
}

func assertIdentity(t *testing.T, identities map[string]bool, key string) {
	t.Helper()
	if !identities[key] {
		t.Fatalf("identities = %#v, want %q", identities, key)
	}
}

func containsString(values []string, want string) bool {
	for _, value := range values {
		if value == want {
			return true
		}
	}
	return false
}

func containsError(errors []string, want string) bool {
	for _, err := range errors {
		if strings.Contains(err, want) {
			return true
		}
	}
	return false
}
