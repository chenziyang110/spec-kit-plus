package main

import (
	"testing"
)

func TestPlaybookProtectedOwnerCaseAliasesAreRejected(t *testing.T) {
	root, input := playbookFixture(t)
	for _, source := range []string{".GIT/config", "nested/.Git/config", ".SPECIFY/DO/session.json", ".specify/PLAYBOOKS/method.json", ".Specify/RUNTIME/pin.json"} {
		t.Run("source:"+source, func(t *testing.T) {
			definition := input.Definition
			definition.SourceFiles = []string{source}
			if err := validatePlaybookDefinition(root, definition); err == nil {
				t.Fatalf("protected owner alias was accepted as live source: %s", source)
			}
		})
	}
	for _, target := range []string{".SPECIFY/memory/project-rules.md", ".PLANNING/e2e/run.json", ".GIT/config", "nested/.Git/config"} {
		t.Run("write:"+target, func(t *testing.T) {
			definition := playbookNormalizeDefinition(input.Definition)
			definition.Steps[0].SideEffect = "local_write"
			definition.Steps[0].SourceWrites = []string{target}
			if err := validatePlaybookDefinition(root, definition); err == nil {
				t.Fatalf("protected owner alias was accepted as ordinary source mutation: %s", target)
			}
		})
	}
}
