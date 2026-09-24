package context

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"reflect"
	"strconv"
	"strings"
	"unicode/utf8"
)

// DecodeBound is the strict wire boundary for persisted or transported packets.
// It rejects ambiguous/lossy JSON before Go can coerce it. A decoded packet is
// not permission or current evidence: call VerifyAgainst with fresh inputs
// resolved by the owning runtime before consumption, then retain its gates.
func DecodeBound(data []byte) (Packet, error) {
	if len(data) == 0 || len(data) > defaultMaxBytes {
		return Packet{}, fmt.Errorf("context_budget_exceeded: input must contain 1..%d bytes", defaultMaxBytes)
	}
	if !utf8.Valid(data) || !json.Valid(data) {
		return Packet{}, fmt.Errorf("context_json_invalid: require one valid UTF-8 JSON value")
	}
	if err := unicodeEscapes(data); err != nil {
		return Packet{}, err
	}
	decoder := json.NewDecoder(bytes.NewReader(data))
	decoder.UseNumber()
	value, err := uniqueJSONValue(decoder, 0)
	if err != nil {
		return Packet{}, fmt.Errorf("context_json_invalid: %w", err)
	}
	if _, err := decoder.Token(); err != io.EOF {
		return Packet{}, fmt.Errorf("context_json_invalid: trailing input")
	}
	if err := checkWireType(value, reflect.TypeOf(Packet{})); err != nil {
		return Packet{}, fmt.Errorf("context_json_invalid: %w", err)
	}
	var packet Packet
	if err := json.Unmarshal(data, &packet); err != nil {
		return Packet{}, err
	}
	if err := packet.validateBound(); err != nil {
		return Packet{}, err
	}
	return packet, nil
}

func uniqueJSONValue(d *json.Decoder, depth int) (any, error) {
	if depth > 32 {
		return nil, fmt.Errorf("nesting limit exceeded")
	}
	token, err := d.Token()
	if err != nil {
		return nil, err
	}
	switch token {
	case json.Delim('{'):
		object := map[string]any{}
		for d.More() {
			token, err := d.Token()
			if err != nil {
				return nil, err
			}
			key, ok := token.(string)
			if !ok {
				return nil, fmt.Errorf("object key is not a string")
			}
			if _, exists := object[key]; exists {
				return nil, fmt.Errorf("duplicate object key")
			}
			value, err := uniqueJSONValue(d, depth+1)
			if err != nil {
				return nil, err
			}
			object[key] = value
		}
		if token, err := d.Token(); err != nil || token != json.Delim('}') {
			return nil, fmt.Errorf("unclosed object")
		}
		return object, nil
	case json.Delim('['):
		array := []any{}
		for d.More() {
			value, err := uniqueJSONValue(d, depth+1)
			if err != nil {
				return nil, err
			}
			array = append(array, value)
		}
		if token, err := d.Token(); err != nil || token != json.Delim(']') {
			return nil, fmt.Errorf("unclosed array")
		}
		return array, nil
	default:
		return token, nil
	}
}

// Compare exact JSON tags, not encoding/json's case-insensitive field lookup.
// Optional properties may be omitted, but explicit null never means an empty
// restriction list. Compiler validation separately enforces required fields.
func checkWireType(value any, shape reflect.Type) error {
	switch shape.Kind() {
	case reflect.Struct:
		object, ok := value.(map[string]any)
		if !ok {
			return fmt.Errorf("expected object")
		}
		fields := map[string]reflect.Type{}
		for i := 0; i < shape.NumField(); i++ {
			field := shape.Field(i)
			name := strings.Split(field.Tag.Get("json"), ",")[0]
			if name != "" && name != "-" {
				fields[name] = field.Type
			}
		}
		for key, child := range object {
			field, ok := fields[key]
			if !ok {
				return fmt.Errorf("unknown or wrongly cased property")
			}
			if err := checkWireType(child, field); err != nil {
				return err
			}
		}
	case reflect.Slice:
		array, ok := value.([]any)
		if !ok {
			return fmt.Errorf("expected array, not null")
		}
		for _, child := range array {
			if err := checkWireType(child, shape.Elem()); err != nil {
				return err
			}
		}
	case reflect.String:
		if _, ok := value.(string); !ok {
			return fmt.Errorf("expected string")
		}
	case reflect.Bool:
		if _, ok := value.(bool); !ok {
			return fmt.Errorf("expected boolean")
		}
	default:
		return fmt.Errorf("unsupported packet field type")
	}
	return nil
}

// encoding/json replaces unpaired UTF-16 surrogate escapes with U+FFFD. Refuse
// that lossy normalization; escaped backslashes and valid pairs remain legal.
// json.Valid has already checked string termination and escape lengths.
func unicodeEscapes(data []byte) error {
	for i := 0; i < len(data); i++ {
		if data[i] != '"' {
			continue
		}
		for i++; i < len(data) && data[i] != '"'; i++ {
			if data[i] != '\\' {
				continue
			}
			i++
			if data[i] != 'u' {
				continue
			}
			code, err := strconv.ParseUint(string(data[i+1:i+5]), 16, 16)
			if err != nil {
				return fmt.Errorf("context_json_invalid: Unicode escape")
			}
			i += 4
			if code >= 0xD800 && code <= 0xDBFF {
				if i+6 >= len(data) || data[i+1] != '\\' || data[i+2] != 'u' {
					return fmt.Errorf("context_json_invalid: unpaired Unicode surrogate")
				}
				low, err := strconv.ParseUint(string(data[i+3:i+7]), 16, 16)
				if err != nil || low < 0xDC00 || low > 0xDFFF {
					return fmt.Errorf("context_json_invalid: unpaired Unicode surrogate")
				}
				i += 6
			} else if code >= 0xDC00 && code <= 0xDFFF {
				return fmt.Errorf("context_json_invalid: unpaired Unicode surrogate")
			}
		}
	}
	return nil
}
