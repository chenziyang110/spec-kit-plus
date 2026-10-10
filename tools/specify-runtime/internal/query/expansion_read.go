package query

import (
	"encoding/json"
	"fmt"
	"strconv"
	"strings"
)

// expansionReadBundle retains unrequested sections as raw JSON. Unmarshal still
// validates the complete document and the typed envelope, but does not allocate
// every nested candidate/evidence object just to return one small section.
// The shallower SectionPayloads field intentionally shadows the embedded field.
type expansionReadBundle struct {
	ExpansionBundle
	SectionPayloads map[string]expansionRawSection `json:"section_payloads"`
}

func decodeExpansionReadBundle(data []byte) (ExpansionBundle, map[string]json.RawMessage, map[string]ExpansionSectionMeta, error) {
	var wire expansionReadBundle
	if err := json.Unmarshal(data, &wire); err != nil {
		return ExpansionBundle{}, nil, nil, err
	}
	meta := make(map[string]ExpansionSectionMeta, len(wire.SectionPayloads))
	sections := make(map[string]json.RawMessage, len(wire.SectionPayloads))
	for section, raw := range wire.SectionPayloads {
		sections[section] = raw.data
		// Match expansionSectionMeta, including its treatment of blank keys.
		if strings.TrimSpace(section) == "" {
			continue
		}
		meta[section] = ExpansionSectionMeta{State: "available", EstimatedItems: raw.count}
	}
	return wire.ExpansionBundle, sections, meta, nil
}

// Validate every value as it is encountered, including values overwritten by
// duplicate keys or later null maps. Keeping only the final raw map would hide
// numeric overflow that the eager decoder previously rejected.
type expansionRawSection struct {
	data  json.RawMessage
	count int
}

func (section *expansionRawSection) UnmarshalJSON(data []byte) error {
	count, err := expansionRawItemCount(data)
	if err != nil {
		return err
	}
	section.data = append(section.data[:0], data...)
	section.count = count
	return nil
}

// expansionRawItemCount is a projection over already syntax-validated JSON,
// not a JSON parser. It counts only outermost array members and skips quoted
// strings/escapes so nested commas cannot inflate the public item count. A
// scalar/object counts as one; null and an empty array count as zero.
// Reject numbers that the previous float64-backed generic decoder rejected,
// even in an unrequested section. Ordinary small numbers need no conversion.
func expansionRawItemCount(raw json.RawMessage) (int, error) {
	start := 0
	for start < len(raw) && expansionJSONSpace(raw[start]) {
		start++
	}
	if start == len(raw) || raw[start] == 'n' {
		return 0, nil
	}
	array := raw[start] == '['
	count := 1
	if array {
		next := start + 1
		for next < len(raw) && expansionJSONSpace(raw[next]) {
			next++
		}
		if next < len(raw) && raw[next] == ']' {
			count = 0
		}
	}
	depth := 0
	for i := start; i < len(raw); i++ {
		switch c := raw[i]; c {
		case '"':
			for i++; i < len(raw); i++ {
				if raw[i] == '\\' {
					i++
				} else if raw[i] == '"' {
					break
				}
			}
		case '[', '{':
			depth++
		case ']', '}':
			depth--
		case ',':
			if array && depth == 1 {
				count++
			}
		default:
			if c != '-' && (c < '0' || c > '9') {
				continue
			}
			end := i + 1
			hasExponent := false
			for end < len(raw) {
				b := raw[end]
				if b == 'e' || b == 'E' {
					hasExponent = true
				} else if b != '+' && b != '-' && b != '.' && (b < '0' || b > '9') {
					break
				}
				end++
			}
			if hasExponent || end-i >= 309 {
				if _, err := strconv.ParseFloat(string(raw[i:end]), 64); err != nil {
					return 0, fmt.Errorf("number is not representable as float64: %w", err)
				}
			}
			i = end - 1
		}
	}
	return count, nil
}

func expansionJSONSpace(b byte) bool {
	return b == ' ' || b == '\t' || b == '\n' || b == '\r'
}
