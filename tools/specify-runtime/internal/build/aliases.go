package build

import (
	"crypto/sha256"
	"encoding/hex"
	"path"
	"path/filepath"
	"sort"
	"strings"
	"unicode"

	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/scanartifacts"
	"github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/internal/store"
)

type aliasSeed struct {
	alias      string
	targetID   string
	source     string
	confidence string
	evidenceID string
	language   string
}

func aliasImports(generationID string, pkg scanartifacts.Package) []store.AliasImport {
	tagsByEvidenceID := observationTagsByEvidenceID(pkg.Observations)
	byIdentity := map[string]store.AliasImport{}
	for _, node := range pkg.Nodes {
		firstEvidenceID := firstString(node.EvidenceIDs)
		seeds := []aliasSeed{
			{
				alias:      node.Title,
				targetID:   node.ID,
				source:     "node_title",
				confidence: defaultConfidence(node.Confidence),
				evidenceID: firstEvidenceID,
				language:   "unknown",
			},
			{
				alias:      node.ID,
				targetID:   node.ID,
				source:     "node_id",
				confidence: "high",
				language:   "code",
			},
			{
				alias:      node.Type,
				targetID:   node.ID,
				source:     "node_type",
				confidence: "medium",
				language:   "unknown",
			},
		}
		seeds = append(seeds, attrAliasSeeds(node, firstEvidenceID)...)
		for _, alias := range pathAliasValues(node.Paths) {
			seeds = append(seeds, aliasSeed{
				alias:      alias,
				targetID:   node.ID,
				source:     "path_material",
				confidence: defaultConfidence(node.Confidence),
				evidenceID: firstEvidenceID,
				language:   "code",
			})
		}
		for _, evidenceID := range node.EvidenceIDs {
			for _, alias := range tagsByEvidenceID[evidenceID] {
				seeds = append(seeds, aliasSeed{
					alias:      alias,
					targetID:   node.ID,
					source:     "observation_tag",
					confidence: "medium",
					evidenceID: evidenceID,
					language:   "unknown",
				})
			}
		}
		for _, seed := range seeds {
			alias, ok := aliasImportFromSeed(generationID, seed)
			if !ok {
				continue
			}
			key := strings.Join([]string{generationID, alias.TargetType, alias.TargetID, alias.NormalizedAlias, alias.Source}, "\x00")
			if existing, exists := byIdentity[key]; exists {
				byIdentity[key] = strongerAlias(existing, alias)
				continue
			}
			byIdentity[key] = alias
		}
	}

	out := make([]store.AliasImport, 0, len(byIdentity))
	for _, alias := range byIdentity {
		out = append(out, alias)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].TargetID != out[j].TargetID {
			return out[i].TargetID < out[j].TargetID
		}
		if out[i].Source != out[j].Source {
			return out[i].Source < out[j].Source
		}
		if out[i].NormalizedAlias != out[j].NormalizedAlias {
			return out[i].NormalizedAlias < out[j].NormalizedAlias
		}
		return out[i].ID < out[j].ID
	})
	return out
}

func attrAliasSeeds(node scanartifacts.NodeRow, evidenceID string) []aliasSeed {
	seeds := []aliasSeed{}
	for _, alias := range attrStrings(node.Attrs, "aliases") {
		seeds = append(seeds, aliasSeed{
			alias:      alias,
			targetID:   node.ID,
			source:     "scan_alias",
			confidence: defaultConfidence(node.Confidence),
			evidenceID: evidenceID,
			language:   "unknown",
		})
	}
	for _, key := range []string{"domain", "owner", "workflow", "route"} {
		if alias := attrString(node.Attrs, key); alias != "" {
			seeds = append(seeds, aliasSeed{
				alias:      alias,
				targetID:   node.ID,
				source:     "node_attr",
				confidence: "medium",
				evidenceID: evidenceID,
				language:   "unknown",
			})
		}
	}
	for _, alias := range attrStrings(node.Attrs, "route_hints") {
		seeds = append(seeds, aliasSeed{
			alias:      alias,
			targetID:   node.ID,
			source:     "route_hint",
			confidence: "medium",
			evidenceID: evidenceID,
			language:   "unknown",
		})
	}
	for _, alias := range attrStrings(node.Attrs, "verification_hints") {
		seeds = append(seeds, aliasSeed{
			alias:      alias,
			targetID:   node.ID,
			source:     "verification_hint",
			confidence: "medium",
			evidenceID: evidenceID,
			language:   "unknown",
		})
	}
	return seeds
}

func aliasImportFromSeed(generationID string, seed aliasSeed) (store.AliasImport, bool) {
	alias := strings.TrimSpace(seed.alias)
	normalized := normalizeAlias(alias)
	if alias == "" || normalized == "" || excludedAliasPath(alias) {
		return store.AliasImport{}, false
	}
	return store.AliasImport{
		ID:              stableAliasID(generationID, "node", seed.targetID, normalized, seed.source),
		Alias:           alias,
		NormalizedAlias: normalized,
		TargetType:      "node",
		TargetID:        seed.targetID,
		Language:        defaultString(seed.language, "unknown"),
		Source:          defaultString(seed.source, "scan_alias"),
		Confidence:      defaultString(seed.confidence, "medium"),
		EvidenceID:      seed.evidenceID,
	}, true
}

func stableAliasID(generationID string, targetType string, targetID string, normalizedAlias string, source string) string {
	seed := strings.Join([]string{generationID, targetType, targetID, normalizedAlias, source}, "\x00")
	hash := sha256.Sum256([]byte(seed))
	return "ALIAS-" + sanitizeIDPart(targetID) + "-" + hex.EncodeToString(hash[:])[:16]
}

func normalizeAlias(value string) string {
	value = strings.ToLower(strings.TrimSpace(value))
	var b strings.Builder
	previousSplit := true
	for _, r := range value {
		if unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_' || r == '-' || r == '/' || r == '.' {
			b.WriteRune(r)
			previousSplit = false
			continue
		}
		if !previousSplit {
			b.WriteByte(' ')
			previousSplit = true
		}
	}
	return strings.TrimSpace(b.String())
}

func pathAliasValues(paths []string) []string {
	values := []string{}
	for _, rawPath := range paths {
		normalizedPath := filepath.ToSlash(strings.TrimSpace(rawPath))
		normalizedPath = strings.TrimPrefix(normalizedPath, "./")
		if normalizedPath == "" || excludedAliasPath(normalizedPath) {
			continue
		}
		withoutExt := strings.TrimSuffix(normalizedPath, filepath.Ext(normalizedPath))
		for _, part := range strings.FieldsFunc(withoutExt, func(r rune) bool {
			return r == '/' || r == '\\' || r == '-' || r == '_' || r == '.'
		}) {
			part = strings.TrimSpace(part)
			if len(part) >= 3 {
				values = append(values, part)
			}
		}
		if base := strings.TrimSuffix(path.Base(normalizedPath), path.Ext(normalizedPath)); len(base) >= 3 {
			values = append(values, base)
		}
	}
	return uniqueAliasStrings(values)
}

func excludedAliasPath(value string) bool {
	normalizedPath := filepath.ToSlash(strings.TrimSpace(value))
	normalizedPath = strings.TrimPrefix(normalizedPath, "./")
	return normalizedPath == ".specify" || strings.HasPrefix(normalizedPath, ".specify/")
}

func observationTagsByEvidenceID(observations []scanartifacts.ObservationRow) map[string][]string {
	byEvidenceID := map[string][]string{}
	for _, observation := range observations {
		tags := boundedObservationTags(observation.Summary)
		if len(tags) == 0 {
			continue
		}
		for _, evidenceID := range observation.EvidenceIDs {
			byEvidenceID[evidenceID] = uniqueAliasStrings(append(byEvidenceID[evidenceID], tags...))
		}
	}
	return byEvidenceID
}

func boundedObservationTags(summary string) []string {
	if strings.TrimSpace(summary) == "" {
		return []string{}
	}
	tags := []string{}
	for _, raw := range strings.FieldsFunc(summary, func(r rune) bool {
		return !(unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_' || r == '-' || r == '/' || r == '.')
	}) {
		token := strings.Trim(raw, "._-/")
		if len(token) < 3 || len(token) > 40 || observationStopwords[strings.ToLower(token)] {
			continue
		}
		if !hasCodeSignal(token) {
			continue
		}
		tags = append(tags, token)
		if len(tags) >= 8 {
			break
		}
	}
	return uniqueAliasStrings(tags)
}

func hasCodeSignal(value string) bool {
	if strings.ContainsAny(value, "_-/.") {
		return true
	}
	letterCount := 0
	upperCount := 0
	hasUpperAfterFirstLetter := false
	for _, r := range value {
		if unicode.IsDigit(r) {
			return true
		}
		if !unicode.IsLetter(r) {
			continue
		}
		if unicode.IsUpper(r) {
			upperCount++
			if letterCount > 0 {
				hasUpperAfterFirstLetter = true
			}
		}
		letterCount++
	}
	return letterCount >= 2 && (upperCount == letterCount || hasUpperAfterFirstLetter)
}

func attrString(attrs map[string]any, key string) string {
	return toString(attrs[key])
}

func attrStrings(attrs map[string]any, key string) []string {
	value, ok := attrs[key]
	if !ok {
		return []string{}
	}
	switch typed := value.(type) {
	case []any:
		values := make([]string, 0, len(typed))
		for _, item := range typed {
			if text := toString(item); text != "" {
				values = append(values, text)
			}
		}
		return uniqueAliasStrings(values)
	case []string:
		return uniqueAliasStrings(typed)
	default:
		if text := toString(typed); text != "" {
			return []string{text}
		}
		return []string{}
	}
}

func toString(value any) string {
	text, ok := value.(string)
	if !ok {
		return ""
	}
	return strings.TrimSpace(text)
}

func uniqueAliasStrings(values []string) []string {
	seen := map[string]bool{}
	out := make([]string, 0, len(values))
	for _, value := range values {
		value = strings.TrimSpace(value)
		normalized := normalizeAlias(value)
		if value == "" || normalized == "" || seen[normalized] {
			continue
		}
		seen[normalized] = true
		out = append(out, value)
	}
	return out
}

func firstString(values []string) string {
	for _, value := range values {
		value = strings.TrimSpace(value)
		if value != "" {
			return value
		}
	}
	return ""
}

func defaultConfidence(value string) string {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "verified", "high":
		return "high"
	case "medium":
		return "medium"
	case "low":
		return "low"
	case "provisional":
		return "provisional"
	default:
		return "medium"
	}
}

func strongerAlias(existing store.AliasImport, candidate store.AliasImport) store.AliasImport {
	if confidenceRank(candidate.Confidence) > confidenceRank(existing.Confidence) {
		if candidate.EvidenceID == "" && existing.EvidenceID != "" {
			candidate.EvidenceID = existing.EvidenceID
		}
		return candidate
	}
	if existing.EvidenceID == "" && candidate.EvidenceID != "" {
		existing.EvidenceID = candidate.EvidenceID
	}
	return existing
}

func confidenceRank(value string) int {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "high", "verified":
		return 4
	case "medium":
		return 3
	case "low":
		return 2
	case "provisional":
		return 1
	default:
		return 0
	}
}

func defaultString(value string, fallback string) string {
	value = strings.TrimSpace(value)
	if value == "" {
		return fallback
	}
	return value
}

var observationStopwords = map[string]bool{
	"and":       true,
	"are":       true,
	"for":       true,
	"from":      true,
	"has":       true,
	"into":      true,
	"its":       true,
	"own":       true,
	"owns":      true,
	"the":       true,
	"this":      true,
	"that":      true,
	"with":      true,
	"observed":  true,
	"summary":   true,
	"rendering": true,
	"dispatch":  true,
}
