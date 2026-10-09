package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func assetMigrationTestWrite(t *testing.T, root, relative, content string) {
	t.Helper()
	target := filepath.Join(root, filepath.FromSlash(relative))
	if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(target, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func assetMigrationTestPlan(t *testing.T, service *AssetService, request AssetMigrationPlanRequest) AssetMigrationPlan {
	t.Helper()
	result := service.MigrationPlan(request)
	if result.Status != "ok" {
		t.Fatalf("plan failed: %+v", result)
	}
	plan, ok := result.Data["plan"].(AssetMigrationPlan)
	if !ok {
		t.Fatalf("plan is missing: %+v", result)
	}
	return plan
}

func assetMigrationTestRead(t *testing.T, root, relative string) string {
	t.Helper()
	raw, err := os.ReadFile(filepath.Join(root, filepath.FromSlash(relative)))
	if err != nil {
		t.Fatal(err)
	}
	return string(raw)
}

func TestAssetMigrationPlansWithoutWritingAndAppliesReviewedMarkdownReferences(t *testing.T) {
	root := t.TempDir()
	assetMigrationTestWrite(t, root, "Draft.md", "# Draft\n\n![Visual](old-logo.png \"title\")\n[Guide](docs/other.md#section)\n")
	assetMigrationTestWrite(t, root, "old-logo.png", "unchanged-binary-bytes")
	assetMigrationTestWrite(t, root, "README.md", "# Project\n[Draft](Draft.md)\n\n[visual]: old-logo.png\n")
	assetMigrationTestWrite(t, root, "docs/other.md", "# Other\n")
	service := NewAssetService(root)
	request := AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "Draft.md", To: "docs/guides/draft.md"}, {From: "old-logo.png", To: "assets/brand/logo.png"}}, ReferencePaths: []string{"README.md"}, ReferenceScopeComplete: true}
	plan := assetMigrationTestPlan(t, service, request)
	if plan.Coverage.Mode != "explicit-references-only" || plan.Coverage.GlobalScanPerformed || len(plan.References) != 2 {
		t.Fatalf("reference scope was misstated: %+v", plan.Coverage)
	}
	if _, err := os.Stat(filepath.Join(root, ".specify")); !os.IsNotExist(err) {
		t.Fatal("read-only planning created runtime state")
	}
	if _, err := os.Stat(filepath.Join(root, "assets")); !os.IsNotExist(err) {
		t.Fatal("read-only planning created destination directories")
	}
	result := service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest})
	if result.Status != "ok" || result.Data["global_references_verified"] != false {
		t.Fatalf("apply failed or overstated coverage: %+v", result)
	}
	if got := assetMigrationTestRead(t, root, "assets/brand/logo.png"); got != "unchanged-binary-bytes" {
		t.Fatalf("media bytes changed: %q", got)
	}
	wantDraft := "# Draft\n\n![Visual](../../assets/brand/logo.png \"title\")\n[Guide](../other.md#section)\n"
	if got := assetMigrationTestRead(t, root, "docs/guides/draft.md"); got != wantDraft {
		t.Fatalf("outgoing links were not preserved: %q", got)
	}
	if got := assetMigrationTestRead(t, root, "README.md"); got != "# Project\n[Draft](docs/guides/draft.md)\n\n[visual]: assets/brand/logo.png\n" {
		t.Fatalf("incoming links were not updated: %q", got)
	}
	for _, source := range []string{"Draft.md", "old-logo.png"} {
		if _, err := os.Stat(filepath.Join(root, source)); !os.IsNotExist(err) {
			t.Fatalf("migration silently copied rather than moved %s", source)
		}
	}
	journalRef := strings.TrimSuffix(result.Data["journal_ref"].(string), "/journal.json")
	journal, err := readAssetMigrationJournal(root, journalRef)
	if err != nil {
		t.Fatal(err)
	}
	if err := validateAssetMigrationJournal(plan, journal); err != nil {
		t.Fatal(err)
	}
	for index, entry := range journal.Entries {
		if entry.Existed {
			backup, _, err := assetMigrationRead(root, fmt.Sprintf("%s/backup-%04d", journalRef, index), assetMigrationMaxFileBytes)
			if err != nil || fileContentSHA256(backup) != entry.BeforeSHA256 {
				t.Fatalf("original bytes were not backed up for %s: %v", entry.Path, err)
			}
		}
	}
	result = service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest})
	if result.Status != "ok" || result.Data["already_applied"] != true {
		t.Fatalf("identical apply did not return idempotent completion: %+v", result)
	}
}

func TestAssetMigrationRejectsChangedContentReferencesPolicyAndDestinations(t *testing.T) {
	for _, scenario := range []string{"source", "reference", "policy", "target", "case", "plan"} {
		t.Run(scenario, func(t *testing.T) {
			root := t.TempDir()
			assetMigrationTestWrite(t, root, "old.png", "original")
			assetMigrationTestWrite(t, root, "README.md", "![x](old.png)\n")
			service := NewAssetService(root)
			plan := assetMigrationTestPlan(t, service, AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "old.png", To: "assets/hero.png"}}, ReferencePaths: []string{"README.md"}, ReferenceScopeComplete: true})
			switch scenario {
			case "source":
				assetMigrationTestWrite(t, root, "old.png", "changed-by-another-task")
			case "reference":
				assetMigrationTestWrite(t, root, "README.md", "other task changed the document\n")
			case "policy":
				assetMigrationTestWrite(t, root, ".asset-policy.json", `{"schema_version":1,"roots":{"guide":"docs/manual"}}`)
			case "target":
				assetMigrationTestWrite(t, root, "assets/hero.png", "other-user-content")
			case "case":
				assetMigrationTestWrite(t, root, "assets/HERO.png", "case-collision")
			case "plan":
				plan.Moves[0].To = "assets/tampered.png"
			}
			result := service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest})
			if result.Status != "blocked" {
				t.Fatalf("stale/tampered migration applied: %+v", result)
			}
			if _, err := os.Stat(filepath.Join(root, "old.png")); err != nil {
				t.Fatal("rejected apply removed the source")
			}
			if _, err := os.Stat(filepath.Join(root, ".specify")); !os.IsNotExist(err) {
				t.Fatal("rejected preflight wrote runtime state")
			}
		})
	}
}

func TestAssetMigrationProtectsCanonicalControlSourceAndEngineResources(t *testing.T) {
	paths := []string{
		".specify/features/2026-10-08-test/spec.md", ".specify/design/changes/test/previews/approval.png",
		".specify/memory/project-cognition.db", ".specify/runtime/asset-migrations/old/journal.json",
		".planning/report.md", "specs/001-test/plan.md", "templates/report.md", "src/screenshot.png",
		"README.md", "AGENTS.md", "Assets/hero.png", "public/paired.png", "public/density.png", "assets/model.gltf",
	}
	for _, relative := range paths {
		t.Run(relative, func(t *testing.T) {
			root := t.TempDir()
			assetMigrationTestWrite(t, root, relative, "original")
			if relative == "public/paired.png" {
				assetMigrationTestWrite(t, root, relative+".meta", "engine-guid")
			}
			if relative == "public/density.png" {
				assetMigrationTestWrite(t, root, "public/density@2x.png", "resolution-variant")
			}
			destination := "assets/moved" + filepath.Ext(relative)
			if strings.HasSuffix(relative, ".md") {
				destination = "docs/guides/moved.md"
			}
			result := NewAssetService(root).MigrationPlan(AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: relative, To: destination}}, ReferenceScopeComplete: true})
			if result.Status != "blocked" {
				t.Fatalf("owned source was accepted: %+v", result)
			}
			if got := assetMigrationTestRead(t, root, relative); got != "original" {
				t.Fatal("planner changed a protected source")
			}
		})
	}
}

func TestAssetMigrationReferencesRespectSourceTemplateAndFixtureOwners(t *testing.T) {
	for _, reference := range []string{"src/templates/fixture.md", "templates/guide.md", "docs/fixtures/example.md", "tests/__snapshots__/page.md", "Assets/readme.md"} {
		t.Run(reference, func(t *testing.T) {
			root := t.TempDir()
			assetMigrationTestWrite(t, root, "old.png", "original-image")
			relative, err := filepath.Rel(filepath.Dir(reference), "old.png")
			if err != nil {
				t.Fatal(err)
			}
			before := "![logo](" + filepath.ToSlash(relative) + ")\n"
			assetMigrationTestWrite(t, root, reference, before)
			service := NewAssetService(root)
			result := service.MigrationPlan(AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "old.png", To: "public/hero.png"}}, ReferencePaths: []string{reference}, ReferenceScopeComplete: true})
			plan, ok := result.Data["plan"].(AssetMigrationPlan)
			if result.Status != "blocked" || !ok || len(plan.Coverage.Unsupported) != 1 || plan.Coverage.Unsupported[0].Path != reference {
				t.Fatalf("owned reference was not explicitly blocked: %+v", result)
			}
			if result := service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest}); result.Status != "blocked" {
				t.Fatalf("owned reference applied: %+v", result)
			}
			if assetMigrationTestRead(t, root, reference) != before || assetMigrationTestRead(t, root, "old.png") != "original-image" {
				t.Fatal("blocked migration changed an owner-managed reference or source")
			}
			if _, err := os.Stat(filepath.Join(root, ".specify")); !os.IsNotExist(err) {
				t.Fatal("blocked owner reference created transaction state")
			}
		})
	}
}

func TestAssetMigrationRejectsNativeTargetGroupsAtPlanAndApply(t *testing.T) {
	for _, companion := range []string{"public/logo.png.meta", "public/logo.png.import", "public/logo.png.uid", "public/logo@2x.png"} {
		t.Run(companion, func(t *testing.T) {
			root := t.TempDir()
			assetMigrationTestWrite(t, root, "old.png", "source-image")
			service := NewAssetService(root)
			request := AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "old.png", To: "public/logo.png"}}, ReferenceScopeComplete: true}
			plan := assetMigrationTestPlan(t, service, request)
			assetMigrationTestWrite(t, root, companion, "platform-owned-companion")
			if result := service.MigrationPlan(request); result.Status != "blocked" {
				t.Fatalf("target group was accepted by plan: %+v", result)
			}
			if result := service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest}); result.Status != "blocked" {
				t.Fatalf("target group introduced after planning was accepted: %+v", result)
			}
			if assetMigrationTestRead(t, root, companion) != "platform-owned-companion" || assetMigrationTestRead(t, root, "old.png") != "source-image" {
				t.Fatal("native group refusal changed source or companion")
			}
			if _, err := os.Stat(filepath.Join(root, "public", "logo.png")); !os.IsNotExist(err) {
				t.Fatal("native target was published")
			}
		})
	}
}

func TestAssetMigrationCapturePreservesRacingEditsAndRecreatedPaths(t *testing.T) {
	for _, kind := range []string{"source", "reference"} {
		for _, timing := range []string{"before-capture", "after-capture-recreate"} {
			t.Run(kind+"/"+timing, func(t *testing.T) {
				root := t.TempDir()
				assetMigrationTestWrite(t, root, "old.png", "original-image")
				assetMigrationTestWrite(t, root, "README.md", "![logo](old.png)\n")
				service := NewAssetService(root)
				plan := assetMigrationTestPlan(t, service, AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "old.png", To: "assets/hero.png"}}, ReferencePaths: []string{"README.md"}, ReferenceScopeComplete: true})
				target := "old.png"
				if kind == "reference" {
					target = "README.md"
				}
				originalCapture := assetMigrationCapture
				t.Cleanup(func() { assetMigrationCapture = originalCapture })
				injected := false
				assetMigrationCapture = func(root, journalRoot string, index int, entry assetMigrationEntry) error {
					if entry.Path == target && !injected && timing == "before-capture" {
						injected = true
						assetMigrationTestWrite(t, root, target, "concurrent-actual-version")
					}
					if err := originalCapture(root, journalRoot, index, entry); err != nil {
						return err
					}
					if entry.Path == target && !injected && timing == "after-capture-recreate" {
						injected = true
						assetMigrationTestWrite(t, root, target, "concurrent-actual-version")
					}
					return nil
				}
				result := service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest})
				assetMigrationCapture = originalCapture
				if !injected || result.Status != "blocked" || result.Data["rollback_complete"] != false {
					t.Fatalf("capture conflict was hidden: %+v", result)
				}
				if assetMigrationTestRead(t, root, target) != "concurrent-actual-version" {
					t.Fatal("migration or recovery lost the concurrent version")
				}
				journalRef := ".specify/runtime/asset-migrations/" + plan.Digest
				journal, err := readAssetMigrationJournal(root, journalRef)
				if err != nil {
					t.Fatal(err)
				}
				for index, entry := range journal.Entries {
					if entry.Path != target {
						continue
					}
					captured := assetMigrationTestRead(t, root, journalRef+"/"+entry.CaptureRef)
					backup := assetMigrationTestRead(t, root, fmt.Sprintf("%s/backup-%04d", journalRef, index))
					if timing == "before-capture" && captured != "concurrent-actual-version" {
						t.Fatal("actual captured version was not retained")
					}
					if fileContentSHA256([]byte(backup)) != entry.BeforeSHA256 {
						t.Fatal("independent original backup was changed")
					}
				}
				if repeated := service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest}); repeated.Status != "blocked" {
					t.Fatalf("conflicting recovery replay was accepted: %+v", repeated)
				}
				if assetMigrationTestRead(t, root, target) != "concurrent-actual-version" {
					t.Fatal("repeated recovery overwrote concurrent content")
				}
			})
		}
	}
}

func TestAssetMigrationRecoversInterruptionImmediatelyAfterCapture(t *testing.T) {
	for _, target := range []string{"old.png", "README.md"} {
		t.Run(target, func(t *testing.T) {
			root := t.TempDir()
			assetMigrationTestWrite(t, root, "old.png", "original-image")
			assetMigrationTestWrite(t, root, "README.md", "![logo](old.png)\n")
			service := NewAssetService(root)
			plan := assetMigrationTestPlan(t, service, AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "old.png", To: "assets/hero.png"}}, ReferencePaths: []string{"README.md"}, ReferenceScopeComplete: true})
			originalCapture := assetMigrationCapture
			t.Cleanup(func() { assetMigrationCapture = originalCapture })
			assetMigrationCapture = func(root, journalRoot string, index int, entry assetMigrationEntry) error {
				if err := originalCapture(root, journalRoot, index, entry); err != nil {
					return err
				}
				if entry.Path == target {
					panic("simulated interruption between capture and validation/publication")
				}
				return nil
			}
			interrupted := false
			func() {
				defer func() { interrupted = recover() != nil }()
				service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest})
			}()
			assetMigrationCapture = originalCapture
			if !interrupted {
				t.Fatal("fixture did not interrupt the capture phase")
			}
			result := service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest})
			if result.Status != "ok" || assetMigrationTestRead(t, root, "assets/hero.png") != "original-image" || assetMigrationTestRead(t, root, "README.md") != "![logo](assets/hero.png)\n" {
				t.Fatalf("capture-phase recovery failed: %+v", result)
			}
			retained, err := os.ReadDir(filepath.Join(root, ".specify/runtime/asset-migrations/.retained"))
			if err != nil || len(retained) != 1 {
				t.Fatalf("recovery discarded the interrupted journal's captured inodes: %v (%v)", retained, err)
			}
		})
	}
}

func TestAssetMigrationReportsUnsupportedReferencesAndNeverClaimsGlobalCoverage(t *testing.T) {
	root := t.TempDir()
	assetMigrationTestWrite(t, root, "old.png", "original")
	assetMigrationTestWrite(t, root, "src/page.tsx", `const image = "old.png";`)
	assetMigrationTestWrite(t, root, "README.md", "Use `old.png` in the code example.\n")
	service := NewAssetService(root)
	for _, references := range [][]string{{"src/page.tsx"}, {"README.md"}, {".specify/design/changes/test/design-change.md"}} {
		result := service.MigrationPlan(AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "old.png", To: "assets/hero.png"}}, ReferencePaths: references, ReferenceScopeComplete: true})
		if result.Status != "blocked" {
			t.Fatalf("unsupported references were silently skipped: %+v", result)
		}
		plan := result.Data["plan"].(AssetMigrationPlan)
		if len(plan.Coverage.Unsupported) == 0 || plan.Coverage.GlobalScanPerformed || plan.Coverage.Mode != "explicit-references-only" {
			t.Fatalf("coverage overstated: %+v", plan.Coverage)
		}
		if applied := service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest}); applied.Status != "blocked" {
			t.Fatalf("unsupported plan applied: %+v", applied)
		}
	}
	result := service.MigrationPlan(AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "old.png", To: "assets/hero.png"}}})
	if result.Status != "warn" {
		t.Fatalf("missing scope declaration was not reported: %+v", result)
	}
	plan := result.Data["plan"].(AssetMigrationPlan)
	if applied := service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest}); applied.Status != "blocked" {
		t.Fatalf("undeclared reference scope applied: %+v", applied)
	}
}

func TestAssetMigrationRollbackRestoresDeletedSourceAndEveryReference(t *testing.T) {
	root := t.TempDir()
	assetMigrationTestWrite(t, root, "old.png", "source-bytes")
	assetMigrationTestWrite(t, root, "README.md", "![x](old.png)\n")
	service := NewAssetService(root)
	plan := assetMigrationTestPlan(t, service, AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "old.png", To: "assets/brand/hero.png"}}, ReferencePaths: []string{"README.md"}, ReferenceScopeComplete: true})
	originalPublisher := assetMigrationPublish
	t.Cleanup(func() { assetMigrationPublish = originalPublisher })
	assetMigrationPublish = func(root, journalRoot string, index int, entry assetMigrationEntry) error {
		if err := originalPublisher(root, journalRoot, index, entry); err != nil {
			return err
		}
		if entry.Delete {
			return errors.New("injected failure after source removal")
		}
		return nil
	}
	result := service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest})
	if result.Status != "blocked" || result.Data["rollback_complete"] != true {
		t.Fatalf("failed migration was not rolled back: %+v", result)
	}
	if assetMigrationTestRead(t, root, "old.png") != "source-bytes" || assetMigrationTestRead(t, root, "README.md") != "![x](old.png)\n" {
		t.Fatal("rollback lost original source or reference bytes")
	}
	if _, err := os.Stat(filepath.Join(root, "assets")); !os.IsNotExist(err) {
		t.Fatal("rollback left new destination directories behind")
	}
	assetMigrationPublish = originalPublisher
	if retry := service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest}); retry.Status != "ok" {
		t.Fatalf("reviewed plan could not be retried after a complete rollback: %+v", retry)
	}
}

func TestAssetMigrationCrashRecoveryUsesExactJournalAndPreservesConcurrentEdits(t *testing.T) {
	for _, changed := range []bool{false, true} {
		t.Run(map[bool]string{false: "recover", true: "preserve-concurrent-edit"}[changed], func(t *testing.T) {
			root := t.TempDir()
			assetMigrationTestWrite(t, root, "old.png", "source-bytes")
			service := NewAssetService(root)
			plan := assetMigrationTestPlan(t, service, AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "old.png", To: "assets/hero.png"}}, ReferenceScopeComplete: true})
			originalPublisher := assetMigrationPublish
			t.Cleanup(func() { assetMigrationPublish = originalPublisher })
			assetMigrationPublish = func(root, journalRoot string, index int, entry assetMigrationEntry) error {
				if err := originalPublisher(root, journalRoot, index, entry); err != nil {
					return err
				}
				if entry.Delete {
					panic("simulated interruption after deletion")
				}
				return nil
			}
			interrupted := false
			func() {
				defer func() { interrupted = recover() != nil }()
				service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest})
			}()
			assetMigrationPublish = originalPublisher
			if !interrupted {
				t.Fatal("crash fixture did not reach the destructive step")
			}
			if changed {
				assetMigrationTestWrite(t, root, "assets/hero.png", "user-edit-after-interruption")
			}
			result := service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest})
			if changed {
				if result.Status != "blocked" || result.Data["rollback_complete"] != false {
					t.Fatalf("concurrent edit was not protected: %+v", result)
				}
				if assetMigrationTestRead(t, root, "assets/hero.png") != "user-edit-after-interruption" || assetMigrationTestRead(t, root, "old.png") != "source-bytes" {
					t.Fatal("recovery overwrote user content or lost the source")
				}
			} else if result.Status != "ok" {
				t.Fatalf("exact-plan crash recovery failed: %+v", result)
			}
		})
	}
}

func TestAssetMigrationRejectsPathEscapeSymlinkCaseOnlyAndOversizedInput(t *testing.T) {
	root := t.TempDir()
	assetMigrationTestWrite(t, root, "old.png", "source")
	service := NewAssetService(root)
	for _, move := range []AssetMigrationMove{{From: "old.png", To: "../outside.png"}, {From: "old.png", To: "OLD.png"}, {From: "old.png", To: ".specify/design/approved.png"}, {From: "old.png", To: "assets/Bad Name.png"}} {
		if result := service.MigrationPlan(AssetMigrationPlanRequest{Moves: []AssetMigrationMove{move}, ReferenceScopeComplete: true}); result.Status != "blocked" {
			t.Fatalf("invalid path accepted: %+v", result)
		}
	}
	huge := filepath.Join(root, "large.png")
	file, err := os.Create(huge)
	if err != nil {
		t.Fatal(err)
	}
	if err := file.Truncate(assetMigrationMaxFileBytes + 1); err != nil {
		_ = file.Close()
		t.Fatal(err)
	}
	_ = file.Close()
	if result := service.MigrationPlan(AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "large.png", To: "assets/large.png"}}, ReferenceScopeComplete: true}); result.Status != "blocked" {
		t.Fatalf("oversized source accepted: %+v", result)
	}
	external := t.TempDir()
	if err := os.Symlink(external, filepath.Join(root, "assets")); err != nil {
		t.Skipf("symlink creation unavailable: %v", err)
	}
	if result := service.MigrationPlan(AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "old.png", To: "assets/hero.png"}}, ReferenceScopeComplete: true}); result.Status != "blocked" {
		t.Fatalf("symlink destination accepted: %+v", result)
	}
	entries, _ := os.ReadDir(external)
	if len(entries) != 0 {
		t.Fatal("planner followed a symlink and wrote outside the project")
	}
}

func TestAssetMigrationMarkdownSubsetPreservesQueriesFragmentsAndCode(t *testing.T) {
	input := []byte("![x](<../old image.png?download=1#preview> \"title\")\n\n[ref]: ../old%20image.png#part\n[remote](https://example.com/old-image.png)\n")
	output, changes, err := assetMigrationRewriteMarkdown("docs/page.md", "docs/guides/page.md", input, map[string]string{"old image.png": "assets/new-image.png"})
	if err != nil {
		t.Fatal(err)
	}
	if len(changes) != 2 || !bytes.Contains(output, []byte("../../assets/new-image.png?download=1#preview")) || !bytes.Contains(output, []byte("../../assets/new-image.png#part")) || !bytes.Contains(output, []byte("https://example.com/old-image.png")) {
		t.Fatalf("Markdown URL components changed incorrectly: %s (%+v)", output, changes)
	}
	for _, unsupported := range []string{"`[x](../old.png)`\n", "```md\n[x](../old.png)\n```\n", "<img src='../old.png'>\n"} {
		_, _, err := assetMigrationRewriteMarkdown("docs/page.md", "docs/page.md", []byte(unsupported), map[string]string{"old.png": "assets/new.png"})
		if err == nil {
			t.Fatalf("unsupported reference was silently changed or ignored: %q", unsupported)
		}
	}
}

func TestAssetMigrationRejectsLiteralMarkdownLinksWithoutWrites(t *testing.T) {
	for _, scenario := range []struct{ name, content string }{
		{"tab-indented-code", "\t[x](old.png)\n"},
		{"multiline-code-span", "`sample\n[x](old.png)\n`\n"},
		{"unequal-backtick-run", "`sample `` [x](old.png) `` end`\n"},
		{"escaped-link", "\\[x](old.png)\n"},
		{"invalid-fence-close", "```\n```not-a-close\n[x](old.png)\n```\n"},
		{"html-comment", "<!-- [x](old.png) -->\n"},
		{"html-attribute", "<img src='other.png' alt='[x](old.png)'>\n"},
		{"quoted-html-delimiter", "<img src='other.png' alt='> [x](old.png)'>\n"},
		{"raw-html-block", "<div>\n[x](old.png)\n</div>\n"},
		{"blockquote-code", "> ```md\n> [x](old.png)\n> ```\n"},
		{"image-alt-text", "![See [x](old.png)](other.png)\n"},
		{"image-alt-and-target", "![See [x](old.png)](old.png)\n"},
		{"escaped-compound-label", "[See \\[x\\](old.png)](old.png)\n"},
		{"literal-definition-continuation", "intro\n[x]: old.png\n"},
	} {
		t.Run(scenario.name, func(t *testing.T) {
			root := t.TempDir()
			assetMigrationTestWrite(t, root, "old.png", "original-image")
			assetMigrationTestWrite(t, root, "README.md", scenario.content)
			service := NewAssetService(root)
			result := service.MigrationPlan(AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "old.png", To: "assets/hero.png"}}, ReferencePaths: []string{"README.md"}, ReferenceScopeComplete: true})
			plan, ok := result.Data["plan"].(AssetMigrationPlan)
			if result.Status != "blocked" || !ok || len(plan.Coverage.Unsupported) == 0 {
				t.Fatalf("literal Markdown was treated as a rewritable reference: %+v", result)
			}
			if apply := service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest}); apply.Status != "blocked" {
				t.Fatalf("unsupported literal reference was applied: %+v", apply)
			}
			if assetMigrationTestRead(t, root, "README.md") != scenario.content || assetMigrationTestRead(t, root, "old.png") != "original-image" {
				t.Fatal("unsupported reference refusal changed project files")
			}
			if _, err := os.Stat(filepath.Join(root, ".specify")); !os.IsNotExist(err) {
				t.Fatal("unsupported reference refusal created transaction state")
			}
		})
	}
}

func TestAssetMigrationRewritesRealLinksBesideLiteralMarkdown(t *testing.T) {
	for _, content := range []string{
		"\t[x](unrelated.png)\n[x](old.png)\n",
		"`sample\n[x](unrelated.png)\n`\n[x](old.png)\n",
		"```\n[x](unrelated.png)\n```  \n[x](old.png)\n",
		"\\\\[x](old.png)\n",
		"[`sample`](old.png)\n",
		"`sample\n\n[x](old.png)\n\nend`\n",
		"[x](<old.png>)\n",
		"```html\n<div>sample</div>\n```\n[x](old.png)\n",
		"\\<div>\n[x](old.png)\n",
		"intro\n\n[x]: old.png\n",
		"   [x]: <old.png> \"title\"\n",
		"[other]: unrelated.png\n[x]: old.png\n",
	} {
		updated, edits, err := assetMigrationRewriteMarkdown("README.md", "README.md", []byte(content), map[string]string{"old.png": "assets/hero.png"})
		if err != nil || len(edits) != 1 || string(updated) != strings.Replace(content, "old.png", "assets/hero.png", 1) {
			t.Fatalf("real link beside literal text was mishandled: %q -> %q (%+v, %v)", content, updated, edits, err)
		}
	}
}

func TestAssetMigrationCaptureRejectsReplacedInodeWithIdenticalBytes(t *testing.T) {
	root := t.TempDir()
	assetMigrationTestWrite(t, root, "old.png", "original-image")
	service := NewAssetService(root)
	plan := assetMigrationTestPlan(t, service, AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "old.png", To: "assets/hero.png"}}, ReferenceScopeComplete: true})
	originalCapture := assetMigrationCapture
	t.Cleanup(func() { assetMigrationCapture = originalCapture })
	injected := false
	assetMigrationCapture = func(root, journalRoot string, index int, entry assetMigrationEntry) error {
		if entry.Path == "old.png" && !injected {
			injected = true
			if err := os.Rename(filepath.Join(root, "old.png"), filepath.Join(root, "external-original.png")); err != nil {
				return err
			}
			assetMigrationTestWrite(t, root, "old.png", "original-image")
		}
		return originalCapture(root, journalRoot, index, entry)
	}
	result := service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest})
	if !injected || result.Status != "blocked" || !strings.Contains(result.Summary, "drifted at publication") {
		t.Fatalf("identical-byte inode replacement was accepted: %+v", result)
	}
	if assetMigrationTestRead(t, root, "old.png") != "original-image" || assetMigrationTestRead(t, root, "external-original.png") != "original-image" {
		t.Fatal("refusal lost the replacement or independently preserved original")
	}
	if _, err := os.Stat(filepath.Join(root, "assets", "hero.png")); !os.IsNotExist(err) {
		t.Fatal("refusal did not roll back destination publication")
	}
}

func TestAssetMigrationPlanRoundTripAndStableDigest(t *testing.T) {
	root := t.TempDir()
	assetMigrationTestWrite(t, root, "old.png", "original")
	service := NewAssetService(root)
	plan := assetMigrationTestPlan(t, service, AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "old.png", To: "assets/hero.png"}}, ReferenceScopeComplete: true})
	raw, err := json.Marshal(plan)
	if err != nil {
		t.Fatal(err)
	}
	var decoded AssetMigrationPlan
	if err := json.Unmarshal(raw, &decoded); err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(plan, decoded) {
		t.Fatalf("reviewable JSON plan lost fields: %#v != %#v", plan, decoded)
	}
	if digest, err := assetMigrationPlanDigest(decoded); err != nil || digest != plan.Digest {
		t.Fatalf("JSON plan digest did not survive round trip: %s %v", digest, err)
	}
}

func assetMigrationTestGit(t *testing.T, root string) {
	t.Helper()
	git, err := exec.LookPath("git")
	if err != nil {
		t.Skip("bounded incoming-reference probe requires Git")
	}
	command := exec.Command(git, "init", "--quiet", root)
	if output, err := command.CombinedOutput(); err != nil {
		t.Fatalf("initialize isolated Git fixture: %s (%v)", output, err)
	}
}

func TestAssetMigrationGitProbeBlocksUnlistedMarkdownCodeAndCatalogReferences(t *testing.T) {
	for _, scenario := range []struct{ path, content string }{
		{"docs/guide.md", "![hero](../public/old.png)\n"},
		{"src/page.tsx", `const image = "/old.png";`},
		{".assets/records/existing.json", `{"files":[{"path":"public/old.png"}]}`},
	} {
		t.Run(scenario.path, func(t *testing.T) {
			root := t.TempDir()
			assetMigrationTestGit(t, root)
			assetMigrationTestWrite(t, root, "public/old.png", "original")
			assetMigrationTestWrite(t, root, scenario.path, scenario.content)
			result := NewAssetService(root).MigrationPlan(AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "public/old.png", To: "public/hero.png"}}, ReferenceScopeComplete: true})
			if result.Status != "blocked" {
				t.Fatalf("caller assertion bypassed omitted incoming reference: %+v", result)
			}
			plan := result.Data["plan"].(AssetMigrationPlan)
			found := false
			for _, issue := range plan.Coverage.Unsupported {
				found = found || issue.Path == scenario.path
			}
			if !found || plan.Coverage.ReferenceProbe.Status != "bounded-git-text-inspection" || plan.Coverage.GlobalScanPerformed {
				t.Fatalf("omitted-reference evidence is incomplete: %+v", plan.Coverage)
			}
			if _, err := os.Stat(filepath.Join(root, ".specify")); !os.IsNotExist(err) {
				t.Fatal("reference detection wrote runtime state")
			}
		})
	}
}

func TestAssetMigrationGitProbeBindsIncomingReferenceInventoryAtApply(t *testing.T) {
	root := t.TempDir()
	assetMigrationTestGit(t, root)
	assetMigrationTestWrite(t, root, "old.png", "original")
	assetMigrationTestWrite(t, root, "README.md", "![hero](old.png)\n")
	service := NewAssetService(root)
	request := AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "old.png", To: "assets/hero.png"}}, ReferencePaths: []string{"README.md"}, ReferenceScopeComplete: true}
	plan := assetMigrationTestPlan(t, service, request)
	if plan.Coverage.ReferenceProbe.Fingerprint == "" {
		t.Fatal("Git probe has no source-bound fingerprint")
	}
	assetMigrationTestWrite(t, root, "src/page.tsx", `const path = "old.png";`)
	result := service.MigrationApply(AssetMigrationApplyRequest{Plan: plan, ExpectedDigest: plan.Digest})
	if result.Status != "blocked" {
		t.Fatalf("new incoming reference was missed at apply: %+v", result)
	}
	if assetMigrationTestRead(t, root, "old.png") != "original" {
		t.Fatal("stale-reference rejection lost the source")
	}
	if _, err := os.Stat(filepath.Join(root, "assets")); !os.IsNotExist(err) {
		t.Fatal("stale-reference rejection published a destination")
	}
}

func TestAssetMigrationBlocksFrameworkURLsEvenInExplicitMarkdownReferences(t *testing.T) {
	for _, content := range []string{"![hero](/old.png)\n", "<img src=\"/old.png\">\n"} {
		root := t.TempDir()
		assetMigrationTestWrite(t, root, "public/old.png", "original")
		assetMigrationTestWrite(t, root, "README.md", content)
		result := NewAssetService(root).MigrationPlan(AssetMigrationPlanRequest{Moves: []AssetMigrationMove{{From: "public/old.png", To: "public/hero.png"}}, ReferencePaths: []string{"README.md"}, ReferenceScopeComplete: true})
		if result.Status != "blocked" {
			t.Fatalf("framework URL was silently left broken: %+v", result)
		}
		plan := result.Data["plan"].(AssetMigrationPlan)
		if len(plan.Coverage.Unsupported) == 0 || plan.Coverage.Unsupported[0].Path != "README.md" {
			t.Fatalf("framework URL boundary is missing: %+v", plan.Coverage)
		}
	}
}
