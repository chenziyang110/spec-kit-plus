package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// Checks source/producer alignment, not model instruction following or install.
func TestQuickCompactConsumerSourceMatchesProducer(t *testing.T) {
	root := filepath.Join("..", "..", "templates", "advanced-skills", "spx-quick")
	raw, err := os.ReadFile(filepath.Join(root, "references", "task-contract.md"))
	if err != nil {
		t.Fatal(err)
	}
	text := strings.Join(strings.Fields(string(raw)), " ")
	for _, mode := range []string{"item-start", "allow-inline", "item-accept", "item-status"} {
		t.Run(mode, func(t *testing.T) {
			id := "quick." + mode
			contract := quickCompactOutputContract(id)
			if contract == nil || !strings.Contains(text, id) {
				t.Fatalf("missing source or producer support for %s", id)
			}
			for _, key := range []string{"response_schema", "flag", "flag_type", "scope", "default", "fallback", "requires_full_intake", "mutates_canonical_state", "binding_kind"} {
				anchor := fmt.Sprintf("%s: %v", key, contract[key])
				if !strings.Contains(text, anchor) {
					t.Errorf("source does not match producer: %s", anchor)
				}
			}
			omitted := contract["omitted_fields"].([]string)
			if !strings.Contains(text, "omitted_fields: ["+strings.Join(omitted, ", ")+"]") {
				t.Fatal("source/producer omitted-field contract drift")
			}
		})
	}
	for _, anchor := range []string{
		"At entry/resume, read the complete current confirmation",
		"Missing, null, unknown or conflicting support means omit the flag",
		"compact output never authorizes leader-direct",
		"always consume the fresh packet",
		"not current write scope, execution state or authority",
		"A staged checkpoint still needs its normal confirmation",
		"never automatic replay of item-start, allow-inline or item-accept",
		"do not fetch a full pulse after every compact response",
	} {
		if !strings.Contains(strings.ToLower(text), strings.ToLower(anchor)) {
			t.Errorf("missing consumer boundary: %s", anchor)
		}
	}
	skill, err := os.ReadFile(filepath.Join(root, "SKILL.md"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(skill), "Read `references/human-confirmation.md`, then `references/task-contract.md`.") {
		t.Fatal("owning skill no longer requires the consumer reference")
	}
}
