package build

import (
	"testing"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scanartifacts"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

func TestAliasImportsDeriveRequiredNodeAliases(t *testing.T) {
	pkg := scanartifacts.Package{
		Nodes: []scanartifacts.NodeRow{{
			ID:          "N-gui",
			Type:        "capability",
			Title:       "GUI Shell",
			Confidence:  "verified",
			Paths:       []string{"src/gui/window.tsx"},
			EvidenceIDs: []string{"E-gui"},
			Attrs: map[string]any{
				"aliases":            []any{"GUI", "desktop UI"},
				"domain":             "desktop",
				"owner":              "frontend",
				"workflow":           "install",
				"route":              "gui route",
				"route_hints":        []any{"src/gui"},
				"verification_hints": []any{"npm test -- gui"},
			},
		}},
		Observations: []scanartifacts.ObservationRow{{
			ID:              "OBS-gui",
			ObservationType: "summary",
			Summary:         "GUI Shell owns frame rendering and input dispatch.",
			EvidenceIDs:     []string{"E-gui"},
		}},
	}

	aliases := aliasImports("GEN-alias-test", pkg)

	assertAliasImport(t, aliases, "GUI Shell", "node_title", "E-gui")
	assertAliasImport(t, aliases, "N-gui", "node_id", "")
	assertAliasImport(t, aliases, "capability", "node_type", "")
	assertAliasImport(t, aliases, "desktop UI", "scan_alias", "E-gui")
	assertAliasImport(t, aliases, "window", "path_material", "E-gui")
	assertAliasImport(t, aliases, "GUI", "observation_tag", "E-gui")
	assertNoAliasImport(t, aliases, "GUI Shell owns frame rendering and input dispatch.")
}

func TestAliasImportsDeduplicateByIdentity(t *testing.T) {
	pkg := scanartifacts.Package{
		Nodes: []scanartifacts.NodeRow{{
			ID:          "N-app",
			Type:        "capability",
			Title:       "Application",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-app"},
			Attrs: map[string]any{
				"aliases": []any{"App", "app"},
			},
		}},
	}

	aliases := aliasImports("GEN-alias-test", pkg)

	var count int
	for _, alias := range aliases {
		if alias.TargetID == "N-app" && alias.Source == "scan_alias" && alias.NormalizedAlias == "app" {
			count++
		}
	}
	if count != 1 {
		t.Fatalf("scan_alias app count = %d, want 1; aliases = %#v", count, aliases)
	}
}

func TestAliasImportsExcludeSpecifyPathLikeAliases(t *testing.T) {
	pkg := scanartifacts.Package{
		Nodes: []scanartifacts.NodeRow{{
			ID:          "N-runtime",
			Type:        "capability",
			Title:       "Runtime",
			Confidence:  "verified",
			Paths:       []string{".specify/project-cognition/status.json", "src/runtime/app.go"},
			EvidenceIDs: []string{"E-runtime"},
			Attrs: map[string]any{
				"route_hints":        []any{"./.specify/project-cognition/status.json", "src/runtime"},
				"verification_hints": []any{".specify", "go test ./internal/runtime"},
				"aliases":            []any{"runtime .specify note"},
			},
		}},
	}

	aliases := aliasImports("GEN-alias-test", pkg)

	assertNoAliasImport(t, aliases, ".specify/project-cognition/status.json")
	assertNoAliasImport(t, aliases, "./.specify/project-cognition/status.json")
	assertNoAliasImport(t, aliases, ".specify")
	assertAliasImport(t, aliases, "runtime .specify note", "scan_alias", "E-runtime")
	assertAliasImport(t, aliases, "app", "path_material", "E-runtime")
}

func TestAliasImportsObservationTagsRequireCodeSignal(t *testing.T) {
	pkg := scanartifacts.Package{
		Nodes: []scanartifacts.NodeRow{{
			ID:          "N-session",
			Type:        "capability",
			Title:       "Session",
			Confidence:  "verified",
			EvidenceIDs: []string{"E-session"},
		}},
		Observations: []scanartifacts.ObservationRow{{
			ID:              "OBS-session",
			ObservationType: "summary",
			Summary:         "Handles GUI ActiveSession and src/app.go flows.",
			EvidenceIDs:     []string{"E-session"},
		}},
	}

	aliases := aliasImports("GEN-alias-test", pkg)

	assertNoAliasImport(t, aliases, "Handles")
	assertAliasImport(t, aliases, "GUI", "observation_tag", "E-session")
	assertAliasImport(t, aliases, "ActiveSession", "observation_tag", "E-session")
	assertAliasImport(t, aliases, "src/app.go", "observation_tag", "E-session")
}

func assertAliasImport(t *testing.T, aliases []store.AliasImport, alias string, source string, evidenceID string) {
	t.Helper()
	for _, row := range aliases {
		if row.Alias == alias && row.Source == source && row.EvidenceID == evidenceID {
			return
		}
	}
	t.Fatalf("missing alias import alias=%q source=%q evidence_id=%q in %#v", alias, source, evidenceID, aliases)
}

func assertNoAliasImport(t *testing.T, aliases []store.AliasImport, alias string) {
	t.Helper()
	for _, row := range aliases {
		if row.Alias == alias {
			t.Fatalf("found unexpected alias import alias=%q in %#v", alias, aliases)
		}
	}
}
