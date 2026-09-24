package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"reflect"
	"strings"

	contextpacket "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/context"
)

// Decode the bounded snapshot without encoding/json's lossy float64 conversion
// or case-insensitive overwrites of typed state fields. This is a read boundary,
// not a new confirmation owner: schema, digest, status and dependency gates stay
// with the caller. In particular, never recalculate a stored confirmation digest
// to make a malformed or externally changed snapshot pass.
func decodeQuickShadowConfirmation(raw []byte) (quickConfirmationDoc, error) {
	zero := quickConfirmationDoc{}
	if err := contextpacket.ValidateQuickShadowJSON(raw); err != nil {
		return zero, err
	}
	if err := checkQuickShadowFieldNames(raw, reflect.TypeOf(zero), "$"); err != nil {
		return zero, err
	}
	var doc quickConfirmationDoc
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.UseNumber()
	if err := decoder.Decode(&doc); err != nil {
		return zero, fmt.Errorf("quick_shadow_confirmation_invalid: %w", err)
	}
	return doc, nil
}

// Audit only the typed owner surface. Dynamic maps (such as UI metadata) retain
// their own keys, including distinct "status" and "Status" entries. Unknown
// non-alias fields keep the existing owner's compatibility behavior and remain
// covered by the raw-state digest; they are not newly interpreted or approved.
// ValidateQuickShadowJSON has already rejected duplicate keys, lossy Unicode,
// trailing values, non-objects, excessive depth and input beyond 128 KiB.
func checkQuickShadowFieldNames(raw json.RawMessage, shape reflect.Type, location string) error {
	for shape.Kind() == reflect.Pointer {
		shape = shape.Elem()
	}
	if bytes.Equal(bytes.TrimSpace(raw), []byte("null")) {
		return nil // Preserve typed optional-null behavior; the owner enforces readiness.
	}
	switch shape.Kind() {
	case reflect.Struct:
		var object map[string]json.RawMessage
		if err := json.Unmarshal(raw, &object); err != nil {
			return fmt.Errorf("quick_shadow_confirmation_invalid: expected object at %s", location)
		}
		fields := make(map[string]reflect.Type, shape.NumField())
		for i := 0; i < shape.NumField(); i++ {
			field := shape.Field(i)
			if field.PkgPath != "" {
				continue
			}
			name := strings.Split(field.Tag.Get("json"), ",")[0]
			if name == "-" {
				continue
			}
			if name == "" {
				name = field.Name
			}
			fields[name] = field.Type
		}
		for name, value := range object {
			field, exact := fields[name]
			if !exact {
				for canonical := range fields {
					if strings.EqualFold(name, canonical) {
						return fmt.Errorf("quick_shadow_field_alias: require exact field %s.%s", location, canonical)
					}
				}
				continue
			}
			if err := checkQuickShadowFieldNames(value, field, location+"."+name); err != nil {
				return err
			}
		}
	case reflect.Slice, reflect.Array:
		var values []json.RawMessage
		if err := json.Unmarshal(raw, &values); err != nil {
			return fmt.Errorf("quick_shadow_confirmation_invalid: expected array at %s", location)
		}
		for i, value := range values {
			if err := checkQuickShadowFieldNames(value, shape.Elem(), fmt.Sprintf("%s[%d]", location, i)); err != nil {
				return err
			}
		}
	}
	return nil
}
