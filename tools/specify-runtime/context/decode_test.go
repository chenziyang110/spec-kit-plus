package context

import (
	"bytes"
	"encoding/json"
	"reflect"
	"strings"
	"testing"
)

func packetWire(t *testing.T, change func(*CompileRequest)) []byte {
	t.Helper()
	in := boundFixture()
	if change != nil {
		change(&in)
	}
	p, err := (Compiler{}).CompileBound(in)
	if err != nil {
		t.Fatal(err)
	}
	data, err := json.Marshal(p)
	if err != nil {
		t.Fatal(err)
	}
	return data
}

func TestDecodeRejectsAmbiguousOrLossyJSON(t *testing.T) {
	good := packetWire(t, nil)
	cases := map[string][]byte{
		"empty": nil, "null": []byte("null"), "array": []byte("[]"),
		"malformed": []byte("{"), "second-value": append(append([]byte{}, good...), good...),
		"oversized":         bytes.Repeat([]byte(" "), defaultMaxBytes+1),
		"missing-binding":   []byte(`{"schema_version":"context-packet-v2","bound":true}`),
		"duplicate-key":     bytes.Replace(good, []byte(`"goal":`), []byte(`"goal":"wrong","goal":`), 1),
		"escaped-duplicate": bytes.Replace(good, []byte(`"goal":`), []byte(`"\u0067oal":"wrong","goal":`), 1),
		"wrong-case":        bytes.Replace(good, []byte(`"task_id":`), []byte(`"Task_ID":`), 1),
		"unknown-key":       append([]byte(`{"claim_ready":true,`), good[1:]...),
		"null-optional":     bytes.Replace(good, []byte(`"constraints":["preserve existing UI"]`), []byte(`"constraints":null`), 1),
		"null-member":       bytes.Replace(good, []byte(`"constraints":["preserve existing UI"]`), []byte(`"constraints":[null]`), 1),
		"wrong-type":        bytes.Replace(good, []byte(`"bound":true`), []byte(`"bound":"true"`), 1),
		"nested-unknown":    bytes.Replace(good, []byte(`"path":"src/login.go"`), []byte(`"extra":true,"path":"src/login.go"`), 1),
		"nested-case":       bytes.Replace(good, []byte(`"path":"src/login.go"`), []byte(`"Path":"src/login.go"`), 1),
		"nested-duplicate":  bytes.Replace(good, []byte(`"path":"src/login.go"`), []byte(`"path":"wrong","path":"src/login.go"`), 1),
		"bad-time":          bytes.Replace(good, []byte(`"generated_at":"`), []byte(`"generated_at":"invalid-`), 1),
		"tamper":            bytes.Replace(good, []byte(`"repair login"`), []byte(`"changed goal"`), 1),
	}
	replacement := packetWire(t, func(r *CompileRequest) { r.Goal = "repair\ufffd" })
	cases["unpaired-high"] = bytes.Replace(replacement, []byte("\ufffd"), []byte(`\ud800`), 1)
	cases["unpaired-low"] = bytes.Replace(replacement, []byte("\ufffd"), []byte(`\udfff`), 1)
	cases["invalid-utf8"] = bytes.Replace(replacement, []byte("\ufffd"), []byte{0xff}, 1)
	cases["deep"] = []byte(strings.Repeat("[", 40) + "0" + strings.Repeat("]", 40))
	for name, data := range cases {
		t.Run(name, func(t *testing.T) {
			p, err := DecodeBound(data)
			if err == nil || !reflect.DeepEqual(p, Packet{}) {
				t.Fatalf("invalid wire accepted or partial packet returned: %v", err)
			}
		})
	}
}

func TestDecodeAcceptsUnicodeEscapesWithoutLosingIdentity(t *testing.T) {
	for _, goal := range []string{"修复登录", "repair😀", `literal\ud800`, `quoted "value"`, "replacement\ufffd"} {
		t.Run(goal, func(t *testing.T) {
			data := packetWire(t, func(r *CompileRequest) { r.Goal = goal })
			variants := [][]byte{data, append([]byte(" \n"), data...)}
			if strings.Contains(goal, "😀") {
				variants = append(variants, bytes.Replace(data, []byte("😀"), []byte(`\ud83d\ude00`), 1))
			}
			if strings.Contains(goal, "修") {
				variants = append(variants, bytes.Replace(data, []byte("修"), []byte(`\u4fee`), 1))
			}
			for _, raw := range variants {
				p, err := DecodeBound(raw)
				if err != nil {
					t.Fatal(err)
				}
				if p.Goal != goal {
					t.Fatal("decoded goal changed")
				}
				in := boundFixture()
				in.Goal = goal
				if err := p.VerifyAgainst(in); err != nil {
					t.Fatal(err)
				}
			}
		})
	}
}

func TestDecodeDoesNotAuthorizeFreshness(t *testing.T) {
	p, err := DecodeBound(packetWire(t, nil))
	if err != nil {
		t.Fatal(err)
	}
	changed := boundFixture()
	changed.StateDigest = strings.Repeat("d", 64)
	if p.VerifyAgainst(changed) == nil {
		t.Fatal("decoding bypassed fresh state verification")
	}
}

func TestVerificationRejectsInconsistentRedundantProjection(t *testing.T) {
	in := boundFixture()
	p, _ := (Compiler{}).CompileBound(in)
	p.RelevantArtifacts = []string{"other/file.go"}
	p.ContentDigest = p.digest() // Self-consistent hash cannot repair a false projection.
	if p.validateBound() == nil {
		t.Fatal("mismatched artifact projection accepted")
	}
}

func FuzzDecodeBoundNeverReturnsPartial(f *testing.F) {
	in := boundFixture()
	p, _ := (Compiler{}).CompileBound(in)
	data, _ := json.Marshal(p)
	for _, seed := range [][]byte{data, []byte("null"), []byte(`{"a":"\ud800"}`), []byte(`{"a":[1,2]}`)} {
		f.Add(seed)
	}
	f.Fuzz(func(t *testing.T, data []byte) {
		p, err := DecodeBound(data)
		if err != nil {
			if !reflect.DeepEqual(p, Packet{}) {
				t.Fatal("partial packet escaped failed decode")
			}
		} else if err := p.validateBound(); err != nil {
			t.Fatal(err)
		}
	})
}
