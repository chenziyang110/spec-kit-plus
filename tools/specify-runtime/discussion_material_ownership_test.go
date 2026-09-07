package main

import "testing"

func TestDiscussionMaterialSnapshotsRejectGenericMutation(t *testing.T) {
	for _, path := range []string{
		".specify/discussions/intake/materials/MAT-001/content.txt",
		".specify/discussions/intake/materials/MAT-001/receipt.json",
		".specify/discussions/archive/intake/materials/MAT-001/content.txt",
	} {
		metadata, ok := LookupArtifactType(path)
		if !ok || metadata.TypeID != "discussion-material" {
			t.Fatalf("%s must be registered as runtime-owned material: %#v, %v", path, metadata, ok)
		}
		for _, operation := range metadata.Operations {
			if operation != "show" && operation != "list" {
				t.Fatalf("%s permits generic mutation %q", path, operation)
			}
		}
	}
}
