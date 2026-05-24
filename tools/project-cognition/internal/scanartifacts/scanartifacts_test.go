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

func TestValidateBlocksIncludedCandidateWithoutCoverageOrGap(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"src/missing.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":["src/app.go","src/missing.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","src/missing.go":"deep_read"},
		"classification_reasons":{"src/app.go":"source","src/missing.go":"source"},
		"decision_source":{"src/app.go":"git","src/missing.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe included path src/missing.go has no coverage row or accepted gap") {
		t.Fatalf("Errors = %#v, want missing included path coverage error", result.Errors)
	}
}

func TestValidateBlocksExcludedPathInCoverage(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "coverage.json"), []byte(`{"rows":[{"path":"src/app.go"},{"path":"vendor/lib.go"}]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"vendor/lib.go","disposition":"excluded","decision_source":".cognitionignore"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[{"path":"vendor/lib.go","reason":"vendor","decision_source":".cognitionignore"}],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","vendor/lib.go":"excluded"},
		"classification_reasons":{"src/app.go":"source","vendor/lib.go":"vendor"},
		"decision_source":{"src/app.go":"git","vendor/lib.go":".cognitionignore"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "excluded path vendor/lib.go must not appear in coverage.json") {
		t.Fatalf("Errors = %#v, want excluded coverage error", result.Errors)
	}
}

func TestValidateAcceptsBoundaryExcludedPathOutsideCoverage(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"vendor/lib.go","disposition":"excluded","decision_source":".cognitionignore"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[{"path":"vendor/lib.go","reason":"vendor","decision_source":".cognitionignore"}],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","vendor/lib.go":"excluded"},
		"classification_reasons":{"src/app.go":"source","vendor/lib.go":"vendor"},
		"decision_source":{"src/app.go":"git","vendor/lib.go":".cognitionignore"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
}

func TestValidateAcceptsLegacyRowsUniverseWithoutStrictCoverageMatch(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "coverage.json"), []byte(`{"rows":[{"path":"src/renamed.go"}]}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
}

func TestValidateAcceptsIncludedPathCoveredByAcceptedGapPath(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go"}],
		"open_gaps":[{"path":"src/missing.go","status":"low_risk_open_gap","owner":"scan","reason":"deferred","evidence_expectation":"non-critical path","revisit_condition":"next scan"}]
	}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"src/missing.go","disposition":"sampled","decision_source":"git"}],
		"included_paths":["src/app.go","src/missing.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","src/missing.go":"sampled"},
		"classification_reasons":{"src/app.go":"source","src/missing.go":"source"},
		"decision_source":{"src/app.go":"git","src/missing.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
}

func TestValidateAcceptsIncludedPathCoveredByAcceptedGapPathsArray(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go"}],
		"open_gaps":[{"paths":["src/missing.go"],"status":"low_risk_open_gap","owner":"scan","reason":"deferred","evidence_expectation":"non-critical path","revisit_condition":"next scan"}]
	}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"src/missing.go","disposition":"sampled","decision_source":"git"}],
		"included_paths":["src/app.go","src/missing.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","src/missing.go":"sampled"},
		"classification_reasons":{"src/app.go":"source","src/missing.go":"source"},
		"decision_source":{"src/app.go":"git","src/missing.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
}

func TestValidateBlocksDeepReadCandidateOmittedFromIncludedPaths(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"src/missing.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","src/missing.go":"deep_read"},
		"classification_reasons":{"src/app.go":"source","src/missing.go":"source"},
		"decision_source":{"src/app.go":"git","src/missing.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe candidate path src/missing.go with disposition deep_read must be listed in included_paths") {
		t.Fatalf("Errors = %#v, want missing included membership error", result.Errors)
	}
	if !containsError(result.Errors, "repository-universe included path src/missing.go has no coverage row or accepted gap") {
		t.Fatalf("Errors = %#v, want missing candidate coverage error", result.Errors)
	}
}

func TestValidateBlocksExcludedCandidateOmittedFromExcludedPathsInCoverage(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "coverage.json"), []byte(`{"rows":[{"path":"src/app.go"},{"path":"vendor/lib.go"}]}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"vendor/lib.go","disposition":"excluded","decision_source":".cognitionignore"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","vendor/lib.go":"excluded"},
		"classification_reasons":{"src/app.go":"source","vendor/lib.go":"vendor"},
		"decision_source":{"src/app.go":"git","vendor/lib.go":".cognitionignore"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe candidate path vendor/lib.go with excluded disposition must be listed in excluded_paths") {
		t.Fatalf("Errors = %#v, want missing excluded membership error", result.Errors)
	}
	if !containsError(result.Errors, "excluded path vendor/lib.go must not appear in coverage.json") {
		t.Fatalf("Errors = %#v, want excluded candidate coverage error", result.Errors)
	}
}

func TestValidateBlocksPathInIncludedAndExcludedPaths(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":["src/app.go"],
		"excluded_paths":["src/app.go"],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read"},
		"classification_reasons":{"src/app.go":"source"},
		"decision_source":{"src/app.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe path src/app.go must not appear in both included_paths and excluded_paths") {
		t.Fatalf("Errors = %#v, want conflicting boundary list error", result.Errors)
	}
}

func TestValidateBlocksMetadataIncompleteGapForBoundaryCoverage(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go"}],
		"open_gaps":[{"path":"src/missing.go","status":"low_risk_open_gap","reason":"deferred","evidence_expectation":"non-critical path","revisit_condition":"next scan"}]
	}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"src/missing.go","disposition":"sampled","decision_source":"git"}],
		"included_paths":["src/app.go","src/missing.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","src/missing.go":"sampled"},
		"classification_reasons":{"src/app.go":"source","src/missing.go":"source"},
		"decision_source":{"src/app.go":"git","src/missing.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe included path src/missing.go has no coverage row or accepted gap") {
		t.Fatalf("Errors = %#v, want incomplete gap ignored for coverage", result.Errors)
	}
}

func TestValidateAcceptsLowRiskGapPathsArrayWithRequiredMetadata(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "coverage-ledger.json"), []byte(`{
		"rows":[{"path":"src/app.go"}],
		"open_gaps":[{"paths":["src/missing.go"],"coverage_state":"low_risk_open_gap","owner":"scan","reason":"deferred","evidence_expectation":"non-critical path","revisit_condition":"next scan"}]
	}`))
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"src/missing.go","disposition":"sampled","decision_source":"git"}],
		"included_paths":["src/app.go","src/missing.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","src/missing.go":"sampled"},
		"classification_reasons":{"src/app.go":"source","src/missing.go":"source"},
		"decision_source":{"src/app.go":"git","src/missing.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "ok" {
		t.Fatalf("Status = %q, want ok; errors=%#v", result.Status, result.Errors)
	}
}

func TestValidateBlocksMalformedVersionedBoundaryFieldShape(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":{"path":"src/app.go"},
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read"},
		"classification_reasons":{"src/app.go":"source"},
		"decision_source":{"src/app.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe included_paths must be an array") {
		t.Fatalf("Errors = %#v, want malformed included_paths error", result.Errors)
	}
}

func TestValidateBlocksVersionedBoundaryMissingSchemaVersion(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read"},
		"classification_reasons":{"src/app.go":"source"},
		"decision_source":{"src/app.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe schema_version is required") {
		t.Fatalf("Errors = %#v, want missing schema_version error", result.Errors)
	}
}

func TestValidateBlocksVersionedBoundaryNonNumericSchemaVersion(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":"1",
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read"},
		"classification_reasons":{"src/app.go":"source"},
		"decision_source":{"src/app.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe schema_version must be a number") {
		t.Fatalf("Errors = %#v, want non-numeric schema_version error", result.Errors)
	}
}

func TestValidateBlocksIncludedPathWithoutDisposition(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","decision_source":"git"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[],
		"ambiguous_paths":[],
		"dispositions":{},
		"classification_reasons":{"src/app.go":"source"},
		"decision_source":{"src/app.go":"git"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe candidate path src/app.go has no disposition") {
		t.Fatalf("Errors = %#v, want missing candidate disposition error", result.Errors)
	}
}

func TestValidateBlocksExcludedPathWithDeepReadDisposition(t *testing.T) {
	paths := scanArtifactTestPaths(t)
	writeMinimalScanPackage(t, paths)
	writeFileBytes(t, filepath.Join(paths.RuntimeDir, "workbench", "repository-universe.json"), []byte(`{
		"schema_version":1,
		"candidate_universe":[{"path":"src/app.go","disposition":"deep_read","decision_source":"git"},{"path":"vendor/lib.go","disposition":"deep_read","decision_source":".cognitionignore"}],
		"included_paths":["src/app.go"],
		"excluded_paths":[{"path":"vendor/lib.go","reason":"vendor","decision_source":".cognitionignore"}],
		"ambiguous_paths":[],
		"dispositions":{"src/app.go":"deep_read","vendor/lib.go":"deep_read"},
		"classification_reasons":{"src/app.go":"source","vendor/lib.go":"vendor"},
		"decision_source":{"src/app.go":"git","vendor/lib.go":".cognitionignore"}
	}`))

	result := Validate(paths, ValidateOptions{RequireStatusJSON: false})

	if result.Status != "blocked" {
		t.Fatalf("Status = %q, want blocked; errors=%#v", result.Status, result.Errors)
	}
	if !containsError(result.Errors, "repository-universe excluded path vendor/lib.go must have excluded disposition") {
		t.Fatalf("Errors = %#v, want excluded disposition mismatch error", result.Errors)
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
