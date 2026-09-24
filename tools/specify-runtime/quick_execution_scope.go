package main

import (
	"fmt"
	"path"
	"strings"
	"unicode"
	"unicode/utf8"
)

// Validate reported result paths before accepting worker proof. An empty scope
// denotes no-write work, not unrestricted authority. This is a lexical gate;
// fenced Work claims and the actual-delta audit remain separate requirements.
func validateQuickChangedFilesInScope(changedFiles, writeScope []string) error {
	scopes, err := normalizeQuickResultScopes(writeScope)
	if err != nil {
		return err
	}
	for index, file := range changedFiles {
		normalized, err := normalizeQuickResultPath(file)
		if err != nil {
			return fmt.Errorf("invalid changed_files[%d]: %w", index, err)
		}
		if !quickResultPathAllowed(normalized, scopes) {
			return fmt.Errorf("changed_files outside packet write_scope: %q", file)
		}
	}
	return nil
}

func quickPathInWriteScope(file string, writeScope []string) bool {
	scopes, err := normalizeQuickResultScopes(writeScope)
	if err != nil {
		return false
	}
	normalized, err := normalizeQuickResultPath(file)
	return err == nil && quickResultPathAllowed(normalized, scopes)
}

func normalizeQuickResultScopes(writeScope []string) ([]string, error) {
	scopes := make([]string, 0, len(writeScope))
	for index, scope := range writeScope {
		scope = strings.ReplaceAll(strings.TrimSpace(scope), "\\", "/")
		// Retain the existing recursive semantics of final /** and legacy /*.
		// Do not introduce a general glob matcher or enlarge the claimed scope.
		if strings.HasSuffix(scope, "/**") {
			scope = strings.TrimSuffix(scope, "/**")
		} else if strings.HasSuffix(scope, "/*") {
			scope = strings.TrimSuffix(scope, "/*")
		}
		normalized, err := normalizeQuickResultPath(scope)
		if err != nil {
			return nil, fmt.Errorf("invalid write_scope[%d]: %w", index, err)
		}
		scopes = append(scopes, normalized)
	}
	return scopes, nil
}

func normalizeQuickResultPath(raw string) (string, error) {
	if !utf8.ValidString(raw) || strings.IndexFunc(raw, unicode.IsControl) >= 0 {
		return "", fmt.Errorf("path must be valid UTF-8 without control characters")
	}
	normalized := strings.ReplaceAll(strings.TrimSpace(raw), "\\", "/")
	if normalized == "" || strings.HasPrefix(normalized, "/") || strings.Contains(normalized, ":") {
		return "", fmt.Errorf("path must be non-empty and project-relative without a drive, stream, or absolute prefix")
	}
	if strings.Contains(normalized, "*") {
		return "", fmt.Errorf("path must be concrete; only scope entries may use final /** or /*")
	}
	for _, segment := range strings.Split(normalized, "/") {
		if segment == ".." {
			return "", fmt.Errorf("path must not contain parent traversal")
		}
	}
	normalized = path.Clean(normalized)
	if normalized == "." {
		return "", fmt.Errorf("path must not select the project root")
	}
	return normalized, nil
}

func quickResultPathAllowed(file string, scopes []string) bool {
	for _, scope := range scopes {
		if file == scope || strings.HasPrefix(file, scope+"/") {
			return true
		}
	}
	return false
}
