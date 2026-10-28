from pathlib import Path
import pytest
from specify_cli.hooks import project_cognition as cognition
from specify_cli.hooks.preflight import workflow_preflight_hook
from specify_cli.specify_runtime import SpecifyRuntimeError

@pytest.mark.parametrize("availability,ready,status,relation", [("ready",True,"ok","unrelated"),("degraded",False,"blocked","related"),("unavailable",False,"blocked","unknown"),("ready",False,"blocked","unknown")])
def test_scoped_preflight_preserves_native_decision(monkeypatch, tmp_path, availability, ready, status, relation):
    calls=[]
    native={"contract_version":2,"status":"ok" if ready else "blocked","availability":availability,
            "scope_ready":ready,"global_status":{"dirty":True},"debt_assessments":[{"relation":relation}],
            "binding":{"contract_version":2},"reasons":[] if ready else ["dependency proof unknown"],
            "claim_ready":False,"source_changes_authorized":False}
    def run(args, **kwargs):
        calls.append(args)
        return {"status":"ok"} if args[0]=="api" else native
    monkeypatch.setattr(cognition,"run_specify_runtime",run)
    result=workflow_preflight_hook(tmp_path,{"command_name":"quick","task_packet":"packets/Q1.json",
                                          "availability_binding":{"contract_version":2}})
    assert result.status==status
    nested=result.data["project_cognition"]["data"]
    assert nested["scope_availability"]==native
    assert native["global_status"]["dirty"] is True
    assert calls[0][3]=="cognition.scope-availability.v2"
    assert "--task-packet" in calls[1] and "--availability-json" in calls[1]
    if not ready: assert result.errors and not result.warnings

@pytest.mark.parametrize("failure", ["capability","read"])
def test_scoped_errors_remain_blocked(monkeypatch,tmp_path,failure):
    def run(args,**kwargs):
        if args[0]=="api":
            return {"status":"blocked" if failure=="capability" else "ok"}
        raise SpecifyRuntimeError("old binding or changed source")
    monkeypatch.setattr(cognition,"run_specify_runtime",run)
    result=workflow_preflight_hook(tmp_path,{"command_name":"quick","packet_file":"packets/Q1.json"})
    assert result.status=="blocked" and result.errors and not result.warnings

def test_scoped_ready_does_not_bypass_workflow_guard(monkeypatch,tmp_path):
    monkeypatch.setattr(cognition,"run_specify_runtime",lambda args,**kw: {"status":"ok"} if args[0]=="api" else
                        {"contract_version":2,"status":"ok","availability":"ready","scope_ready":True})
    result=workflow_preflight_hook(tmp_path,{"command_name":"implement","feature_dir":"feature",
                                           "task_packet":"packets/T001.json"})
    assert result.status=="blocked" and any("workflow-state" in e for e in result.errors)

@pytest.mark.parametrize("key", ["claude", "codex"])
@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_both_profiles_render_scoped_nohook_and_hook_contract(tmp_path, key, profile):
    from specify_cli.integrations import get_integration
    from specify_cli.integrations.manifest import IntegrationManifest
    from specify_cli.launcher import write_runtime_launcher_config
    project=tmp_path/(key+profile)
    fixture=tmp_path/"renderer-only-runtime"
    fixture.write_bytes(b"renderer fixture only")
    write_runtime_launcher_config(project,fixture)
    integration=get_integration(key)
    manifest=IntegrationManifest(key,project)
    integration.setup(project,manifest,parsed_options={"workflow_profile":profile},script_type="ps")
    prefix="sp" if profile=="classic" else "spx"
    quick=integration.skills_dest(project)/(prefix+"-quick")
    content="\n".join(p.read_text(encoding="utf-8") for p in quick.rglob("*.md"))
    assert "cognition.scope-availability.v2" in content
    assert "--task-packet" in content and "--availability-json" in content
    assert "Missing legacy `read_scope`" in content
    assert "human" in content and "Accept" in content
    assert "{{spec-kit-include:" not in content
