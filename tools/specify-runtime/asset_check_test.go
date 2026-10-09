package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

func assetTestGit(t *testing.T, root string, args ...string) string {
	t.Helper()
	command := exec.Command("git", append([]string{"-C", root, "-c", "commit.gpgsign=false", "-c", "user.name=Asset Tests", "-c", "user.email=asset-tests@example.invalid"}, args...)...)
	for _, setting := range os.Environ() {
		if !strings.HasPrefix(setting, "GIT_") {
			command.Env = append(command.Env, setting)
		}
	}
	raw, err := command.CombinedOutput()
	if err != nil {
		t.Fatalf("git %v: %s: %v", args, raw, err)
	}
	return strings.TrimSpace(string(raw))
}

func assetTestRepository(t *testing.T) string {
	t.Helper()
	root := t.TempDir()
	assetTestGit(t, root, "init", "-q")
	assetTestWrite(t, root, "README.md", "# Project\n")
	assetTestGit(t, root, "add", "README.md")
	assetTestGit(t, root, "commit", "-qm", "initial fixture")
	return root
}

func assetEnvelopeHasIssue(env Envelope, code string) bool {
	for _, item := range env.Items {
		if issue, ok := item.(AssetIssue); ok && issue.Code == code {
			return true
		}
	}
	return false
}

func TestAssetCheckPathOnlyDoesNotClaimContentValidation(t *testing.T) {
	root := t.TempDir()
	service := NewAssetService(root)
	env := service.Check(AssetCheckRequest{Paths: []string{"docs/guides/new-guide.md"}, PathOnly: true})
	if env.Status != "ok" || env.Data["content_checked"] != 0 || env.Data["path_only"] != true {
		t.Fatalf("candidate path failed: %#v", env)
	}
	if got := service.Check(AssetCheckRequest{Paths: []string{"docs/guides/new-guide.md"}}); got.Status != "blocked" {
		t.Fatalf("missing file silently passed full check: %#v", got)
	}
	for _, relative := range []string{"README.md", "AGENTS.md", "SKILL.md", "package.json", ".asset-policy.json", ".github/workflows/CI.yml", ".vscode/settings.json", "src/Native_Name.md", "src/build/Native_Name.md", "templates/commands/UPPER.md"} {
		if got := service.Check(AssetCheckRequest{Paths: []string{relative}, PathOnly: true}); got.Status != "ok" {
			t.Fatalf("native/project fixed file was blocked: %s %#v", relative, got)
		}
	}
	for _, relative := range []string{".specify/features/f/spec.md", ".specify/features/f/unknown.md", ".assets/catalog.json", ".git/config"} {
		if got := service.Check(AssetCheckRequest{Paths: []string{relative}, PathOnly: true}); got.Status != "blocked" || !assetEnvelopeHasIssue(got, "owner-required") {
			t.Fatalf("direct owner write accepted: %s %#v", relative, got)
		}
	}
	entries, _ := os.ReadDir(root)
	if len(entries) != 0 {
		t.Fatal("path check created state")
	}
}

func TestAssetCheckMarkdownDependenciesAndCodeExamples(t *testing.T) {
	root := t.TempDir()
	assetTestWrite(t, root, "assets/diagram.svg", "<svg/>")
	assetTestWrite(t, root, "assets/with(parens).svg", "<svg/>")
	assetTestWrite(t, root, "docs/guides/reference.md", "# Reference\n")
	assetTestWrite(t, root, "docs/guides/guide.md", `# Guide
![diagram](../../assets/diagram.svg "diagram")
[reference](reference.md#details)
![parentheses](../../assets/with(parens).svg)
[web](https://example.invalid/absent.md)
[mail](mailto:team@example.invalid)
`+"`[example](absent-inline.md)`\n```md\n[example](absent-code.md)\n```\n"+`    [indented example](absent-indented.md)
`)
	service := NewAssetService(root)
	env := service.Check(AssetCheckRequest{Paths: []string{"docs/guides/guide.md"}})
	if env.Status != "ok" {
		t.Fatalf("valid local links or code examples failed: %#v", env)
	}
	assetTestWrite(t, root, "docs/guides/guide.md", `# Invalid
[missing][ref]
[ref]: ../missing.md "Missing reference"
<img src="../../assets/missing.svg">
[temporary](../../.specify/tmp/assets/task/worker/evidence.md)
[escape](../../../outside.md)
`)
	env = service.Check(AssetCheckRequest{Paths: []string{"docs/guides/guide.md"}})
	for _, code := range []string{"missing-dependency", "ephemeral-dependency", "unsafe-dependency"} {
		if !assetEnvelopeHasIssue(env, code) {
			t.Fatalf("missing %s: %#v", code, env)
		}
	}
}

func TestAssetCheckStagedReadsIndexContentAndDependencies(t *testing.T) {
	root := assetTestRepository(t)
	assetTestWrite(t, root, "docs/guides/test.md", "# Guide\n[missing](missing.md)\n")
	assetTestGit(t, root, "add", "docs/guides/test.md")
	assetTestWrite(t, root, "docs/guides/test.md", "# Fixed only in worktree\n")
	service := NewAssetService(root)
	env := service.Check(AssetCheckRequest{Staged: true})
	if env.Status != "blocked" || !assetEnvelopeHasIssue(env, "missing-dependency") || env.Data["scope"] != "index" {
		t.Fatalf("staged check read working file: %#v", env)
	}
	assetTestGit(t, root, "add", "docs/guides/test.md")
	assetTestWrite(t, root, "docs/guides/test.md", "# Broken only in worktree\n[missing](missing.md)\n")
	env = service.Check(AssetCheckRequest{Staged: true})
	if env.Status != "ok" {
		t.Fatalf("worktree contaminated index validation: %#v", env)
	}
	assetTestWrite(t, root, "docs/guides/test.md", "# Guide\n![asset](../../assets/staged-only.png)\n")
	assetTestWrite(t, root, "assets/staged-only.png", "image")
	assetTestGit(t, root, "add", "docs/guides/test.md", "assets/staged-only.png")
	if err := os.Remove(filepath.Join(root, "assets/staged-only.png")); err != nil {
		t.Fatal(err)
	}
	env = service.Check(AssetCheckRequest{Staged: true})
	if env.Status != "ok" {
		t.Fatalf("index dependency incorrectly checked in worktree: %#v", env)
	}
}

func TestAssetCheckStagedUsesIndexPolicy(t *testing.T) {
	root := assetTestRepository(t)
	assetTestWrite(t, root, "report.md", "# Root report\n")
	assetTestGit(t, root, "add", "report.md")
	assetTestWrite(t, root, assetDefaultPolicyPath, `{"schema_version":1,"allowed_root_files":["report.md"]}`)
	service := NewAssetService(root)
	env := service.Check(AssetCheckRequest{Staged: true})
	if env.Status != "blocked" || !assetEnvelopeHasIssue(env, "root-artifact") {
		t.Fatalf("unstaged policy bypassed staged rules: %#v", env)
	}
	assetTestGit(t, root, "add", assetDefaultPolicyPath)
	assetTestWrite(t, root, assetDefaultPolicyPath, `{"schema_version":999}`)
	env = service.Check(AssetCheckRequest{Staged: true})
	if env.Status != "ok" {
		t.Fatalf("working policy contaminated staged check: %#v", env)
	}
}

func TestAssetCheckTwoRefsReadTargetTree(t *testing.T) {
	root := assetTestRepository(t)
	base := assetTestGit(t, root, "rev-parse", "HEAD")
	assetTestWrite(t, root, "docs/guides/change.md", "# Valid committed guide\n")
	assetTestGit(t, root, "add", "docs/guides/change.md")
	assetTestGit(t, root, "commit", "-qm", "add valid guide")
	head := assetTestGit(t, root, "rev-parse", "HEAD")
	assetTestWrite(t, root, "docs/guides/change.md", "# Broken worktree\n[missing](absent.md)\n")
	service := NewAssetService(root)
	env := service.Check(AssetCheckRequest{Base: base, Head: head})
	if env.Status != "ok" || env.Data["scope"] != "tree" || env.Data["revision"] != head {
		t.Fatalf("tree check read worktree: %#v", env)
	}
	assetTestGit(t, root, "add", "docs/guides/change.md")
	assetTestGit(t, root, "commit", "-qm", "broken target fixture")
	badHead := assetTestGit(t, root, "rev-parse", "HEAD")
	assetTestWrite(t, root, "docs/guides/change.md", "# Now fixed only in worktree\n")
	env = service.Check(AssetCheckRequest{Base: head, Head: badHead})
	if env.Status != "blocked" || !assetEnvelopeHasIssue(env, "missing-dependency") {
		t.Fatalf("fixed worktree masked broken target tree: %#v", env)
	}
	for _, request := range []AssetCheckRequest{{Base: "not-a-ref", Head: head}, {Base: base}, {Staged: true, Base: base, Head: head}, {Staged: true, IncludeUntracked: true}} {
		if got := service.Check(request); got.Status == "ok" {
			t.Fatalf("invalid baseline/scope silently passed: %#v => %#v", request, got)
		}
	}
}

func TestAssetCheckWorktreeDirtyAndExplicitIgnoredFiles(t *testing.T) {
	root := assetTestRepository(t)
	assetTestWrite(t, root, "docs/guides/kept.md", "# Initial\n")
	assetTestWrite(t, root, ".gitignore", "ignored-report.md\n")
	assetTestGit(t, root, "add", "docs/guides/kept.md", ".gitignore")
	assetTestGit(t, root, "commit", "-qm", "baseline")
	assetTestWrite(t, root, "docs/guides/kept.md", "# Dirty before checking\n[missing](missing.md)\n")
	assetTestWrite(t, root, "report.md", "# Untracked root litter\n")
	assetTestWrite(t, root, "ignored-report.md", "# Explicit ignored root litter\n")
	service := NewAssetService(root)
	env := service.Check(AssetCheckRequest{})
	if env.Status != "blocked" || !assetEnvelopeHasIssue(env, "missing-dependency") || assetEnvelopeHasIssue(env, "root-artifact") {
		t.Fatalf("tracked dirty semantics incorrect: %#v", env)
	}
	env = service.Check(AssetCheckRequest{IncludeUntracked: true})
	if !assetEnvelopeHasIssue(env, "root-artifact") {
		t.Fatalf("untracked root litter missed: %#v", env)
	}
	env = service.Check(AssetCheckRequest{Paths: []string{"ignored-report.md"}})
	if !assetEnvelopeHasIssue(env, "root-artifact") {
		t.Fatalf("explicit ignored path was silently excluded: %#v", env)
	}
}

func TestAssetCheckDeletionFindsUnchangedInboundDocument(t *testing.T) {
	root := assetTestRepository(t)
	assetTestWrite(t, root, "assets/diagram.svg", "<svg/>")
	assetTestWrite(t, root, "docs/guides/kept.md", "# Stable guide\n![diagram](../../assets/diagram.svg)\n")
	assetTestGit(t, root, "add", "assets/diagram.svg", "docs/guides/kept.md")
	assetTestGit(t, root, "commit", "-qm", "linked asset")
	base := assetTestGit(t, root, "rev-parse", "HEAD")
	if err := os.Remove(filepath.Join(root, "assets/diagram.svg")); err != nil {
		t.Fatal(err)
	}
	service := NewAssetService(root)
	for _, request := range []AssetCheckRequest{{}, {DeletedPaths: []string{"assets/diagram.svg"}}} {
		env := service.Check(request)
		if env.Status != "blocked" || !assetEnvelopeHasIssue(env, "missing-dependency") || env.Data["inbound_documents_checked"].(int) < 1 {
			t.Fatalf("deleted asset broke an unchecked document: %#v", env)
		}
	}
	assetTestGit(t, root, "add", "assets/diagram.svg")
	env := service.Check(AssetCheckRequest{Staged: true})
	if !assetEnvelopeHasIssue(env, "missing-dependency") {
		t.Fatalf("staged deletion missed inbound link: %#v", env)
	}
	assetTestGit(t, root, "commit", "-qm", "remove asset")
	head := assetTestGit(t, root, "rev-parse", "HEAD")
	assetTestWrite(t, root, "assets/diagram.svg", "<svg>restored only in worktree</svg>")
	env = service.Check(AssetCheckRequest{Base: base, Head: head})
	if !assetEnvelopeHasIssue(env, "missing-dependency") {
		t.Fatalf("worktree restoration masked deleted tree dependency: %#v", env)
	}
}

func TestAssetCheckCleanAndUnbornRepositoriesDoNotCreateState(t *testing.T) {
	root := assetTestRepository(t)
	service := NewAssetService(root)
	before, _ := os.ReadDir(root)
	env := service.Check(AssetCheckRequest{IncludeUntracked: true})
	if env.Status != "ok" || env.Data["checked"] != 0 {
		t.Fatalf("clean check failed: %#v", env)
	}
	after, _ := os.ReadDir(root)
	if len(before) != len(after) {
		t.Fatal("clean check created state")
	}
	unborn := t.TempDir()
	assetTestGit(t, unborn, "init", "-q")
	assetTestWrite(t, unborn, "report.md", "# Initial litter\n")
	assetTestGit(t, unborn, "add", "report.md")
	env = NewAssetService(unborn).Check(AssetCheckRequest{})
	if env.Status != "blocked" || !assetEnvelopeHasIssue(env, "root-artifact") {
		t.Fatalf("unborn staged file was not checked: %#v", env)
	}
}

func TestAssetCheckCorruptHeadIsNotAnUnbornBaseline(t *testing.T) {
	root := assetTestRepository(t)
	branch := assetTestGit(t, root, "symbolic-ref", "--quiet", "HEAD")
	assetTestWrite(t, root, ".git/"+branch, "not-a-valid-object-id\n")
	env := NewAssetService(root).Check(AssetCheckRequest{})
	if env.Status == "ok" {
		t.Fatalf("corrupt HEAD was treated as an empty unborn baseline: %#v", env)
	}
}

func TestAssetCheckWorktreeFiltersNeverExecuteDuringReadOnlyChecks(t *testing.T) {
	for _, driver := range []string{"clean", "process"} {
		t.Run(driver, func(t *testing.T) {
			root := assetTestRepository(t)
			base := assetTestGit(t, root, "rev-parse", "HEAD")
			assetTestWrite(t, root, ".gitattributes", "docs/guides/guide.md filter=review\n")
			assetTestWrite(t, root, "docs/guides/guide.md", "# Committed guide\n")
			assetTestGit(t, root, "add", ".gitattributes", "docs/guides/guide.md")
			assetTestGit(t, root, "commit", "-qm", "add attributed document")
			head := assetTestGit(t, root, "rev-parse", "HEAD")
			assetTestWrite(t, root, "docs/guides/guide.md", "# Staged guide\n")
			assetTestGit(t, root, "add", "docs/guides/guide.md")
			command := "printf observed > filter-marker.txt; cat"
			if driver == "process" {
				command = "printf observed > filter-marker.txt; exit 1"
			}
			assetTestGit(t, root, "config", "filter.review."+driver, command)
			assetTestWrite(t, root, "docs/guides/guide.md", "# Current working guide has changed\n")
			service := NewAssetService(root)
			marker := filepath.Join(root, "filter-marker.txt")
			// Establish the real Git behavior behind the regression: disabling
			// external diff/textconv alone still starts the configured filter.
			_, _ = service.assetGit("diff", "--name-only", "--no-ext-diff", "--no-textconv", "--ignore-submodules=all", "HEAD", "--")
			if _, err := os.Stat(marker); err != nil {
				t.Fatalf("fixture did not exercise Git %s conversion: %v", driver, err)
			}
			if err := os.Remove(marker); err != nil {
				t.Fatal(err)
			}
			for _, request := range []AssetCheckRequest{{}, {IncludeUntracked: true}} {
				result := service.Check(request)
				if result.Status != "blocked" || !strings.Contains(result.Summary, "scope could not be read") {
					t.Fatalf("automatic worktree filter scope was accepted: %+v", result)
				}
			}
			for _, request := range []AssetCheckRequest{
				{Paths: []string{"docs/guides/guide.md"}},
				{Paths: []string{"docs/guides/guide.md"}, PathOnly: true},
				{Staged: true},
				{Base: base, Head: head},
			} {
				if result := service.Check(request); result.Status != "ok" {
					t.Fatalf("conversion-free check was blocked: request=%+v result=%+v", request, result)
				}
			}
			if _, err := os.Stat(marker); !os.IsNotExist(err) {
				t.Fatalf("read-only asset check executed the Git %s filter: %v", driver, err)
			}
		})
	}
}

func TestAssetCheckUnusedConfiguredFiltersAllowWorktreeInspection(t *testing.T) {
	root := assetTestRepository(t)
	assetTestWrite(t, root, "docs/guides/guide.md", "# Original guide\n")
	assetTestGit(t, root, "add", "docs/guides/guide.md")
	assetTestGit(t, root, "commit", "-qm", "add guide without conversion")
	for _, driver := range []string{"clean", "process"} {
		assetTestGit(t, root, "config", "filter.unused."+driver, "printf observed > filter-marker.txt; exit 1")
	}
	assetTestWrite(t, root, "docs/guides/guide.md", "# Edited guide without conversion\n")
	service := NewAssetService(root)
	for _, request := range []AssetCheckRequest{{}, {IncludeUntracked: true}} {
		result := service.Check(request)
		if result.Status != "ok" || result.Data["checked"] != 1 {
			t.Fatalf("an unused configured filter blocked worktree inspection: %+v", result)
		}
	}
	if _, err := os.Stat(filepath.Join(root, "filter-marker.txt")); !os.IsNotExist(err) {
		t.Fatalf("an unused filter was executed: %v", err)
	}
}

func TestAssetCheckSnapshotSymlinkAndCaseBoundaries(t *testing.T) {
	root := assetTestRepository(t)
	assetTestWrite(t, root, "docs/guides/Case.md", "# Case one\n")
	assetTestWrite(t, root, "docs/guides/case.md", "# Case two\n")
	assetTestGit(t, root, "add", "docs/guides")
	service := NewAssetService(root)
	env := service.Check(AssetCheckRequest{Staged: true})
	if runtime.GOOS != "windows" && !assetEnvelopeHasIssue(env, "case-conflict") {
		t.Fatalf("snapshot case collision missed: %#v", env)
	}
	if runtime.GOOS == "windows" {
		return
	}
	outside := filepath.Join(t.TempDir(), "private.md")
	if err := os.WriteFile(outside, []byte("private"), 0o600); err != nil {
		t.Fatal(err)
	}
	link := filepath.Join(root, "docs/guides/linked.md")
	if err := os.Symlink(outside, link); err != nil {
		t.Fatal(err)
	}
	assetTestGit(t, root, "add", "docs/guides/linked.md")
	if err := os.Remove(link); err != nil {
		t.Fatal(err)
	}
	assetTestWrite(t, root, "docs/guides/linked.md", "# Harmless working file\n")
	env = service.Check(AssetCheckRequest{Staged: true, Paths: []string{"docs/guides/linked.md"}})
	if env.Status != "blocked" || !assetEnvelopeHasIssue(env, "unsafe-path") {
		t.Fatalf("index symlink was followed/replaced with working content: %#v", env)
	}
}

func TestAssetCheckDoesNotInspectSourceMarkdownOrRuntimeMetadata(t *testing.T) {
	root := t.TempDir()
	assetTestWrite(t, root, "templates/guides/Expected_Bad.md", "[template](MISSING_TEMPLATE.md)\n")
	assetTestWrite(t, root, "src/build/Native_Name.md", "[source](MISSING_SOURCE.md)\n")
	assetTestWrite(t, root, ".specify/runtime/asset-governance/cache.json", "{}")
	env := NewAssetService(root).Check(AssetCheckRequest{Paths: []string{"templates/guides/Expected_Bad.md", "src/build/Native_Name.md", ".specify/runtime/asset-governance/cache.json"}})
	if env.Status != "ok" || env.Data["content_checked"] != 0 {
		t.Fatalf("source/metadata was misclassified as prose: %#v", env)
	}
}

func TestAssetCheckPersistentRootGuidanceCannotLinkToTemporaryState(t *testing.T) {
	root := t.TempDir()
	assetTestWrite(t, root, "AGENTS.md", "# Guidance\n[unsafe](/.specify/tmp/assets/task/worker/note.md)\n")
	env := NewAssetService(root).Check(AssetCheckRequest{Paths: []string{"AGENTS.md"}})
	if env.Status != "blocked" || !assetEnvelopeHasIssue(env, "ephemeral-dependency") {
		t.Fatalf("persistent project guidance escaped dependency checks: %#v", env)
	}
}

func TestAssetCheckMultilineLinksAndNestedFenceExamples(t *testing.T) {
	root := t.TempDir()
	assetTestWrite(t, root, "docs/guides/guide.md", "# Guide\n````markdown\n```md\n[example](missing-example.md)\n```\n````\n[real](\nmissing-real.md\n)\n")
	env := NewAssetService(root).Check(AssetCheckRequest{Paths: []string{"docs/guides/guide.md"}})
	if len(env.Items) != 1 {
		t.Fatalf("nested fences or multiline links were parsed incorrectly: %#v", env)
	}
	issue, ok := env.Items[0].(AssetIssue)
	if !ok || issue.Code != "missing-dependency" || issue.Dependency != "docs/guides/missing-real.md" {
		t.Fatalf("wrong Markdown dependency: %#v", env)
	}
}

func TestAssetCheckPersistentDependenciesCannotUseNativeCaches(t *testing.T) {
	root := t.TempDir()
	assetTestWrite(t, root, "src/.cache/evidence.svg", "<svg/>")
	assetTestWrite(t, root, "templates/node_modules/package/evidence.svg", "<svg/>")
	for _, target := range []string{"src/.cache/evidence.svg", "templates/node_modules/package/evidence.svg"} {
		assetTestWrite(t, root, "docs/guides/guide.md", "# Guide\n![evidence](/"+target+")\n")
		env := NewAssetService(root).Check(AssetCheckRequest{Paths: []string{"docs/guides/guide.md"}})
		if env.Status != "blocked" || !assetEnvelopeHasIssue(env, "ephemeral-dependency") {
			t.Fatalf("persistent document consumed a native cache: %s %#v", target, env)
		}
	}
}

func TestAssetCheckSnapshotDependenciesRejectSubmoduleBoundaries(t *testing.T) {
	root := assetTestRepository(t)
	base := assetTestGit(t, root, "rev-parse", "HEAD")
	assetTestGit(t, root, "update-index", "--add", "--cacheinfo", "160000,"+base+",assets/external")
	assetTestWrite(t, root, "docs/guides/guide.md", "# Guide\n[external](/assets/external)\n")
	assetTestGit(t, root, "add", "docs/guides/guide.md")
	service := NewAssetService(root)
	requests := []AssetCheckRequest{{Staged: true, Paths: []string{"docs/guides/guide.md"}}}
	assetTestGit(t, root, "commit", "-qm", "external asset fixture")
	requests = append(requests, AssetCheckRequest{Base: base, Head: "HEAD", Paths: []string{"docs/guides/guide.md"}})
	for _, request := range requests {
		env := service.Check(request)
		if env.Status != "blocked" || !assetEnvelopeHasIssue(env, "unsafe-dependency") {
			t.Fatalf("snapshot dependency crossed a submodule boundary: %#v %#v", request, env)
		}
	}
}

func TestAssetCheckRenderedIndentedDependencies(t *testing.T) {
	root := t.TempDir()
	cases := map[string]string{
		"list":        "1. Evidence\n\n    ![capture](missing.svg)\n",
		"nested-list": "- Evidence\n  - Capture\n\n      ![capture](missing.svg)\n",
		"paragraph":   "Evidence: ![capture](\n    missing.svg\n)\n",
	}
	for name, markdown := range cases {
		t.Run(name, func(t *testing.T) {
			assetTestWrite(t, root, "docs/guides/guide.md", markdown)
			env := NewAssetService(root).Check(AssetCheckRequest{Paths: []string{"docs/guides/guide.md"}})
			if env.Status != "blocked" || !assetEnvelopeHasIssue(env, "missing-dependency") {
				t.Fatalf("rendered indented dependency silently passed: %#v", env)
			}
		})
	}
}

func TestAssetCheckIgnoresActualCodeAndEscapedLinkSyntax(t *testing.T) {
	root := t.TempDir()
	cases := map[string]string{
		"tab-code":                  "# Guide\n\n\t[code](missing.md)\n",
		"list-code":                 "1. Example\n\n       [code](missing.md)\n",
		"multiline-code":            "# Guide\n\n``before\n[code](missing.md)\nafter``\n",
		"unequal-code-delimiters":   "# Guide\n\n``before ` [code](missing.md) after``\n",
		"escaped-link":              "# Guide\n\\[literal](missing.md)\n",
		"blockquote-code":           "> ```md\n> [code](missing.md)\n> ```\n",
		"blockquote-multiline-code": "> ``before\n> [code](missing.md)\n> after``\n",
	}
	for name, markdown := range cases {
		t.Run(name, func(t *testing.T) {
			assetTestWrite(t, root, "docs/guides/guide.md", markdown)
			env := NewAssetService(root).Check(AssetCheckRequest{Paths: []string{"docs/guides/guide.md"}})
			if env.Status != "ok" {
				t.Fatalf("literal example was interpreted as a dependency: %#v", env)
			}
		})
	}
}

func TestAssetCheckUnmatchedCodeDelimiterCannotHideNextParagraph(t *testing.T) {
	root := t.TempDir()
	assetTestWrite(t, root, "docs/guides/guide.md", "# Guide\n\n`literal\n\n![real](missing.svg) followed by `literal\n")
	env := NewAssetService(root).Check(AssetCheckRequest{Paths: []string{"docs/guides/guide.md"}})
	if env.Status != "blocked" || !assetEnvelopeHasIssue(env, "missing-dependency") {
		t.Fatalf("unmatched delimiter hid a later rendered paragraph: %#v", env)
	}
}

func TestAssetCheckCodeDelimitersCannotCrossRenderedBlockBoundaries(t *testing.T) {
	root := t.TempDir()
	cases := map[string]string{
		"atx-heading": "# `Heading\n![real](missing.svg) followed by `literal\n",
		"list-items":  "- `First item\n- ![real](missing.svg) followed by `literal\n",
		"non-heading": "#not-a-heading\n    ![real](missing.svg)\n",
	}
	for name, markdown := range cases {
		t.Run(name, func(t *testing.T) {
			assetTestWrite(t, root, "docs/guides/guide.md", markdown)
			env := NewAssetService(root).Check(AssetCheckRequest{Paths: []string{"docs/guides/guide.md"}})
			if env.Status != "blocked" || !assetEnvelopeHasIssue(env, "missing-dependency") {
				t.Fatalf("code masking hid a rendered block dependency: %#v", env)
			}
		})
	}
}

func TestAssetCheckASTPreservesHTMLAndDecodedDependencies(t *testing.T) {
	root := t.TempDir()
	for name, markdown := range map[string]string{
		"html-quoted":                         "# Guide\n\n<img src='missing.svg'>\n",
		"html-multiline-unquoted":             "# Guide\n\n<img\n src=missing.svg>\n",
		"html-ephemeral-entity":               "# Guide\n\n<img src='/.specify&#47;tmp&#47;assets/task/worker/preview.svg'>\n",
		"markdown-ephemeral-entity":           "# Guide\n\n![preview](/.specify&#47;tmp&#47;assets/task/worker/preview.svg)\n",
		"script-ephemeral-source":             "# Guide\n\n<script src='/.specify/tmp/assets/task/worker/preview.js'></script>\n",
		"script-ephemeral-quoted-closing-tag": "# Guide\n\n<script title='</script>' src='/.specify/tmp/assets/task/worker/preview.js'></script>\n",
	} {
		t.Run(name, func(t *testing.T) {
			assetTestWrite(t, root, "docs/guides/guide.md", markdown)
			env := NewAssetService(root).Check(AssetCheckRequest{Paths: []string{"docs/guides/guide.md"}})
			code := "missing-dependency"
			if strings.Contains(name, "ephemeral") {
				code = "ephemeral-dependency"
			}
			if env.Status != "blocked" || !assetEnvelopeHasIssue(env, code) {
				t.Fatalf("rendered HTML/entity dependency was lost: %#v", env)
			}
		})
	}
	assetTestWrite(t, root, "assets/present.svg", "<svg/>")
	for name, markdown := range map[string]string{
		"html-attribute-text":    "# Guide\n\n<span title=\"src='missing.svg' [literal](missing.md)\">Text</span>\n",
		"html-comment":           "# Guide\n\n<!-- <img src='missing.svg'> -->\n",
		"unused-reference":       "# Guide\n\n[unused]: missing.svg\n",
		"image-alt-link":         "# Guide\n\n![[literal](missing.md)](/assets/present.svg)\n",
		"script-body-text":       "# Guide\n\n<script>var example = \"<img src='missing.svg'>\";</script>\n",
		"style-body-text":        "# Guide\n\n<style>/* <img src='missing.svg'> */</style>\n",
		"comment-like-attribute": "# Guide\n\n<img title='<!-- an attribute -->' src='/assets/present.svg'>\n",
	} {
		t.Run(name, func(t *testing.T) {
			assetTestWrite(t, root, "docs/guides/guide.md", markdown)
			env := NewAssetService(root).Check(AssetCheckRequest{Paths: []string{"docs/guides/guide.md"}})
			if env.Status != "ok" {
				t.Fatalf("unrendered example became a dependency: %#v", env)
			}
		})
	}
}

func TestAssetCheckWorktreeCannotSilentlySkipHiddenTrackedChanges(t *testing.T) {
	for _, flag := range []string{"--assume-unchanged", "--skip-worktree"} {
		t.Run(flag, func(t *testing.T) {
			root := assetTestRepository(t)
			assetTestWrite(t, root, "docs/guides/guide.md", "# Valid guide\n")
			assetTestGit(t, root, "add", "docs/guides/guide.md")
			assetTestGit(t, root, "commit", "-qm", "tracked guide fixture")
			assetTestGit(t, root, "update-index", flag, "docs/guides/guide.md")
			assetTestWrite(t, root, "docs/guides/guide.md", "# Changed guide\n![missing](missing.svg)\n")
			service := NewAssetService(root)
			if env := service.Check(AssetCheckRequest{}); env.Status == "ok" {
				t.Fatalf("automatic worktree check silently skipped a hidden changed path: %#v", env)
			}
			if env := service.Check(AssetCheckRequest{Paths: []string{"docs/guides/guide.md"}}); env.Status != "blocked" || !assetEnvelopeHasIssue(env, "missing-dependency") {
				t.Fatalf("explicit read did not recover hidden tracked verification: %#v", env)
			}
			if env := service.Check(AssetCheckRequest{Staged: true}); env.Status != "ok" {
				t.Fatalf("hidden worktree state contaminated an immutable index check: %#v", env)
			}
		})
	}
}

func TestAssetGitEnvironmentOverridesCannotRedirectWindowsSnapshots(t *testing.T) {
	if runtime.GOOS != "windows" {
		t.Skip("Windows environment names are case-insensitive")
	}
	root := assetTestRepository(t)
	other := assetTestRepository(t)
	assetTestWrite(t, root, "docs/guides/guide.md", "# Broken staged guide\n[missing](missing.md)\n")
	assetTestGit(t, root, "add", "docs/guides/guide.md")
	t.Setenv("git_dir", filepath.Join(other, ".git"))
	env := NewAssetService(root).Check(AssetCheckRequest{Staged: true})
	if env.Status != "blocked" || !assetEnvelopeHasIssue(env, "missing-dependency") {
		t.Fatalf("case-aliased Git environment redirected the selected snapshot: %#v", env)
	}
}
