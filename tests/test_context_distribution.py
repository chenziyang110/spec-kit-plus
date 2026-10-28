"""Validate context wire output and the declared bundle layout, not a full wheel.

The Go probe uses synthetic owner inputs. A structural packet is not live
repository evidence, workflow integration or product acceptance.
"""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import tomllib

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "tools/specify-runtime"
SCHEMA = "schemas/context-packet.schema.json"


def includes():
    with (ROOT / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]


def go(cwd, *args):
    executable = shutil.which("go")
    if executable is None:
        pytest.skip("Go is required for the real context-package check")
    env = os.environ.copy()
    env.update(GOTOOLCHAIN="local", GOPROXY="off", GOWORK="off", GOFLAGS="-mod=readonly")
    result = subprocess.run([executable, *args], cwd=cwd, env=env,
                            capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_context_schema_is_included_with_runtime():
    mapping = includes()
    wheel = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert "tools/specify-runtime" in wheel["only-include"]
    assert wheel["sources"]["tools/specify-runtime"] == "specify_cli/core_pack/tools/specify-runtime"
    assert "tools/specify-runtime" not in mapping  # Force inclusion bypasses exclusion rules.
    assert mapping.get(SCHEMA) == "specify_cli/core_pack/" + SCHEMA
    jsonschema.Draft202012Validator.check_schema(json.loads((ROOT / SCHEMA).read_text()))


def test_declared_context_bundle_runs_without_source_checkout(tmp_path):
    mapping = includes()
    wheel = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["tool"]["hatch"]["build"]["targets"]["wheel"]
    target = tmp_path / wheel["sources"]["tools/specify-runtime"]
    shutil.copytree(RUNTIME / "context", target / "context")
    shutil.copy2(RUNTIME / "go.mod", target / "go.mod")
    schema_target = tmp_path / mapping[SCHEMA]
    schema_target.parent.mkdir(parents=True)
    shutil.copy2(ROOT / SCHEMA, schema_target)
    assert schema_target.read_bytes() == (ROOT / SCHEMA).read_bytes()
    events = [json.loads(line) for line in go(target, "test", "-count=1", "-json", "./context").splitlines()]
    passed = {e.get("Test") for e in events if e.get("Action") == "pass"}
    assert {"TestBoundPacketMatchesSchemaSurface", "TestBoundContextPreservesEveryInput",
            "TestBindingRejectsLossyUnicodeInputs", "TestDecodeDoesNotAuthorizeFreshness"} <= passed
    assert not any(e.get("Action") in {"fail", "skip"} for e in events)


PROBE = r'''
package main
import (
 "encoding/json"
 "os"
 "strings"
 ctx "github.com/chenziyang110/spec-kit-plus/tools/specify-runtime/context"
)
func main() {
 packets := []ctx.Packet{}
 for _, goal := range []string{"repair", "修复登录😀", "literal\\ud800"} {
  in := ctx.CompileRequest{TaskID:"Q1", Workflow:"quick", Goal:goal,
   Scope:[]string{"src/"}, Acceptance:[]string{"verify behavior"},
   ForbiddenActions:[]string{"do not deploy"}, StateRef:"runtime://fixture/Q1",
   StateDigest:strings.Repeat("a",64), SourceRevision:strings.Repeat("b",40)}
  p, err := (ctx.Compiler{}).CompileBound(in); if err != nil { panic(err) }
  data, err := json.Marshal(p); if err != nil { panic(err) }
  decoded, err := ctx.DecodeBound(data); if err != nil { panic(err) }
  if err := decoded.VerifyAgainst(in); err != nil { panic(err) }
  packets = append(packets, decoded)
 }
 if err := json.NewEncoder(os.Stdout).Encode(packets); err != nil { panic(err) }
}
'''


def test_actual_go_wire_satisfies_canonical_json_schema(tmp_path):
    driver = tmp_path / "probe.go"
    driver.write_text(PROBE, encoding="utf-8")
    packets = json.loads(go(RUNTIME, "run", str(driver)))
    validator = jsonschema.Draft202012Validator(
        json.loads((ROOT / SCHEMA).read_text()), format_checker=jsonschema.FormatChecker())
    assert len(packets) == 3
    for packet in packets:
        validator.validate(packet)
    for field in ("scope", "acceptance", "forbidden_actions"):
        bad = copy.deepcopy(packets[0])
        bad[field] = None
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(bad)
    bad = copy.deepcopy(packets[0])
    bad["claim_ready"] = True
    with pytest.raises(jsonschema.ValidationError):
        validator.validate(bad)
