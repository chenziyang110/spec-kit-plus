package main

import (
	"fmt"
	"os"
	"reflect"
)

// This cache belongs to one run invocation. Only immutable content-addressed
// references enter it; state and live bindings always use readFile instead.
type e2eImmutableCache struct {
	entries   map[e2eRef]*e2eImmutableEntry
	reads     int
	readBytes int64
	hits      int
	verifying []*e2eImmutableEntry
}

type e2eImmutableReference struct {
	ref  e2eRef
	kind string
}

type e2eImmutableEntry struct {
	raw        []byte
	decoded    map[reflect.Type]reflect.Value
	validated  bool
	references []e2eImmutableReference
}

func (service *e2eService) resetReadRequest() {
	service.observed = map[string]string{}
	service.pendingBlobs = nil
	service.immutable = e2eImmutableCache{entries: map[e2eRef]*e2eImmutableEntry{}}
}

func (service *e2eService) readImmutable(ref e2eRef, kind string, retainBytes bool) (*e2eImmutableEntry, error) {
	// Capture the complete reference graph, including dependencies reached
	// through another cached snapshot. A later parent hit must recheck all
	// paths that its returned evidence pointers make consumable.
	for _, parent := range service.immutable.verifying {
		found := false
		for _, dependency := range parent.references {
			if dependency.ref == ref {
				found = true
				break
			}
		}
		if !found {
			parent.references = append(parent.references, e2eImmutableReference{ref: ref, kind: kind})
		}
	}
	// Recheck the path even on a hit. Cached bytes never authorize traversal
	// through a subsequently replaced symlink or a non-regular file.
	path, err := secureProjectPath(service.projectRoot, ref.Ref)
	if err == nil {
		var info os.FileInfo
		info, err = os.Lstat(path)
		if err == nil && !info.Mode().IsRegular() {
			err = fmt.Errorf("immutable reference must be a regular file: %s", ref.Ref)
		}
	}
	if err != nil {
		return nil, &e2eBindingError{Kind: "immutable_" + kind + "_unavailable", Path: ref.Ref, ExpectedSHA256: ref.SHA256, Reason: err.Error(), Immutable: true}
	}
	if entry, ok := service.immutable.entries[ref]; ok {
		service.immutable.hits++
		return entry, nil
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, &e2eBindingError{Kind: "immutable_" + kind + "_unavailable", Path: ref.Ref, ExpectedSHA256: ref.SHA256, Reason: err.Error(), Immutable: true}
	}
	service.immutable.reads++
	service.immutable.readBytes += int64(len(raw))
	digest := fileContentSHA256(raw)
	service.observed[ref.Ref] = digest
	if digest != ref.SHA256 {
		return nil, &e2eBindingError{Kind: "immutable_" + kind + "_corrupt", Path: ref.Ref, ExpectedSHA256: ref.SHA256, ObservedSHA256: digest, Reason: "immutable " + kind + " bytes changed: " + ref.Ref, Immutable: true}
	}
	entry := &e2eImmutableEntry{decoded: map[reflect.Type]reflect.Value{}}
	if retainBytes {
		entry.raw = raw
	}
	if service.immutable.entries == nil {
		service.immutable.entries = map[e2eRef]*e2eImmutableEntry{}
	}
	service.immutable.entries[ref] = entry
	return entry, nil
}

func (entry *e2eImmutableEntry) decode(output any) error {
	destination := reflect.ValueOf(output)
	if destination.Kind() != reflect.Pointer || destination.IsNil() {
		return fmt.Errorf("snapshot output must be a non-nil pointer")
	}
	target := destination.Elem()
	value, ok := entry.decoded[target.Type()]
	if !ok {
		decoded := reflect.New(target.Type())
		if err := e2eDecode(entry.raw, decoded.Interface()); err != nil {
			return err
		}
		value = decoded.Elem()
		entry.decoded[target.Type()] = value
	}
	// No caller receives a cache-owned map, slice, pointer or RawMessage.
	target.Set(e2eCloneJSONValue(value))
	return nil
}

func e2eCloneJSONValue(value reflect.Value) reflect.Value {
	// Scalars are immutable values; assigning them to the caller-owned target
	// copies them without allocating an intermediate reflective object.
	switch value.Kind() {
	case reflect.Interface, reflect.Pointer, reflect.Map, reflect.Slice, reflect.Struct, reflect.Array:
	default:
		return value
	}
	copy := reflect.New(value.Type()).Elem()
	switch value.Kind() {
	case reflect.Interface, reflect.Pointer:
		if !value.IsNil() {
			inner := e2eCloneJSONValue(value.Elem())
			if value.Kind() == reflect.Pointer {
				copy.Set(reflect.New(value.Type().Elem()))
				copy.Elem().Set(inner)
			} else {
				copy.Set(inner)
			}
		}
	case reflect.Map:
		if !value.IsNil() {
			copy.Set(reflect.MakeMapWithSize(value.Type(), value.Len()))
			iterator := value.MapRange()
			for iterator.Next() {
				copy.SetMapIndex(iterator.Key(), e2eCloneJSONValue(iterator.Value()))
			}
		}
	case reflect.Slice:
		if !value.IsNil() {
			copy.Set(reflect.MakeSlice(value.Type(), value.Len(), value.Len()))
			if value.Type().Elem().Kind() == reflect.Uint8 {
				// RawMessage/byte slices still receive their own backing storage.
				reflect.Copy(copy, value)
			} else {
				for i := 0; i < value.Len(); i++ {
					copy.Index(i).Set(e2eCloneJSONValue(value.Index(i)))
				}
			}
		}
	case reflect.Struct, reflect.Array:
		if value.Kind() == reflect.Struct {
			for i := 0; i < value.NumField(); i++ {
				copy.Field(i).Set(e2eCloneJSONValue(value.Field(i)))
			}
		} else {
			for i := 0; i < value.Len(); i++ {
				copy.Index(i).Set(e2eCloneJSONValue(value.Index(i)))
			}
		}
	}
	return copy
}
