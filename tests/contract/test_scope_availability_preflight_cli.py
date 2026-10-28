from typer.testing import CliRunner
from specify_cli import app

def test_public_preflight_help_exposes_exact_scope_flags():
    result=CliRunner().invoke(app,["hook","preflight","--help"])
    assert result.exit_code==0
    assert "--task-packet" in result.output and "--availability-json" in result.output

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import pytest
from specify_cli.hooks.engine import run_quality_hook

@pytest.mark.parametrize("args", [
    ["--availability-json", "{}"], ["--task-packet", ""],
    ["--task-packet", "packet.json", "--availability-json", "{"],
    ["--task-packet", "packet.json", "--availability-json", "null"],
    ["--task-packet", "packet.json", "--availability-json", "[]"],
    ["--task-packet", "packet.json", "--availability-json", ""],
])
def test_public_scope_options_refuse_invalid_input(tmp_path, monkeypatch, args):
    (tmp_path/".specify").mkdir()
    monkeypatch.chdir(tmp_path)
    result=CliRunner().invoke(app,["hook","preflight","--command","quick",*args])
    assert result.exit_code==2, result.output

@pytest.mark.parametrize("tag", ["claude-classic","claude-advanced","codex-classic","codex-advanced"])
def test_actual_installed_public_cli_matches_native_and_library(tag):
    base=os.environ.get("R5_PUBLIC_CLI_FIXTURE_ROOT")
    if not base: pytest.skip("Requires explicitly installed and native-owner seeded isolated four-profile fixture")
    lane=Path(base).parent
    project=Path(base)/tag
    pin=project/".specify/bin/specify-runtime.exe"
    before=pin.read_bytes()
    assert len(before)==31626752 and hashlib.sha256(before).hexdigest()=="80cc1176b880a7d99e95357ea619f5fe7c91258a7a7f15a9ff65584b8f868d4a"
    env=os.environ.copy();env.pop("SPECIFY_RUNTIME_BIN",None)
    env.update(SPECIFY_RUNTIME_ALLOW_DIRTY="1", SPECIFY_PROJECT_LAUNCHER_STATE_DIR=str(lane/"launcher-state"))
    observations=[]
    def call(label,argv,expected):
        start=time.time_ns();result=subprocess.run(argv,cwd=project,env=env,capture_output=True)
        name=tag+"-attempt"+os.environ.get("R5_PUBLIC_CLI_ATTEMPT","1")+"-"+label
        (lane/(name+".stdout.log")).write_bytes(result.stdout)
        (lane/(name+".stderr.log")).write_bytes(result.stderr)
        record={"argv":argv,"cwd":str(project),"started_at_ns":start,"finished_at_ns":time.time_ns(),"exit_code":result.returncode}
        (lane/(name+".command.json")).write_text(json.dumps(record,indent=2))
        assert result.returncode==expected,(label,result.stdout.decode("utf-8","replace"),result.stderr.decode("utf-8","replace"))
        value=json.loads(result.stdout);observations.append({"label":label,"result":value});return value
    def native(label,args,expected=0):return call(label,[str(pin),*args],expected)
    def cli(label,packet=None,binding=None,expected=0):
        args=[sys.executable,"-m","specify_cli","hook","preflight","--command","quick"]
        if packet is not None:args += ["--task-packet",packet]
        if binding is not None:args += ["--availability-json",json.dumps(binding)]
        return call(label,args,expected)
    packets={};bindings={}
    for number,read in [(1,["src/dependency.go"]),(2,None)]:
        workid="260805-0"+os.environ.get("R5_PUBLIC_CLI_ATTEMPT","1")+str(number);item="Q"+str(number)
        workspace=project/".planning/quick"/(workid+"-exec");workspace.mkdir(parents=True)
        (workspace/"STATUS.md").write_text('---\nid: "'+workid+'"\nslug: "exec"\ntitle: "CLI scope"\nstatus: gathering\nunderstanding_confirmed: false\n---\n\n## Understanding Checkpoint\n\nx\n\n## Execution\n\ny\n')
        row={"id":item,"deliverable":"change A","depends_on":[],"acceptance":"tests pass","write_scope":["src/a.go"]}
        if read is not None:row["read_scope"]=read
        payload={"source":{"kind":"prompt"},"decision":{"goal":"A","user_visible_result":"A works","scope":{"include":["A"],"exclude":[]},"items":[row],"reconfirmation_trigger":"scope change"}}
        stage=native(item+"stage",["quick","--project-root",str(project),"checkpoint-stage",workid,"--input-json",json.dumps(payload),"--format","json"])
        native(item+"confirm",["quick","--project-root",str(project),"checkpoint-confirm",workid,"--digest",stage["data"]["confirmation_digest"],"--format","json"])
        packet=native(item+"compile",["quick","--project-root",str(project),"packet-compile",workid,"--item",item,"--format","json"])["data"]["packet_path"];packets[item]=packet
        data=native(item+"native",["cognition","check","--task-packet",packet,"--format","json"],0 if read is not None else 10)["data"];bindings[item]=data["binding"]
        actual=cli(item+"public",packet,data["binding"],0 if read is not None else 10)
        assert actual["data"]["project_cognition"]["data"]["scope_availability"]==data
        library_code = "import json,sys;from pathlib import Path;from specify_cli.hooks.engine import run_quality_hook;print(json.dumps(run_quality_hook(Path.cwd(),'workflow.preflight',json.loads(sys.argv[1])).to_dict()))"
        library=call(item+"library",[sys.executable,"-c",library_code,json.dumps({"command_name":"quick","task_packet":packet,"availability_binding":data["binding"]})],0)
        # CLI print_json binds diagnostic resume argv to its installed launcher;
        # library to_dict keeps generic argv. All decision/data/blocker facts match.
        def decision(value):
            if isinstance(value,dict):
                return {k:decision(v) for k,v in value.items() if k!="resume"}
            if isinstance(value,list): return [decision(v) for v in value]
            return value
        assert decision(library)==decision(actual)
        assert actual["data"]["project_cognition"]["data"]["scope_availability"] == library["data"]["project_cognition"]["data"]["scope_availability"]
        assert data["global_status"]["dirty"] and not data["claim_ready"] and not data["source_changes_authorized"]
        assert data["review_required"] and data["human_accept_required"]
    assert cli("legacy-global")["status"]=="warn"
    source=project/"src/dependency.go";prior=source.read_bytes();source.write_bytes(prior+b" drift")
    assert not cli("source-drift",packets["Q1"],bindings["Q1"],10)["data"]["project_cognition"]["data"]["scope_availability"]["scope_ready"];source.write_bytes(prior)
    packetpath=project/packets["Q1"];prior=packetpath.read_bytes();packetpath.write_bytes(prior+b" ")
    assert cli("packet-drift",packets["Q1"],bindings["Q1"],10)["status"]=="blocked";packetpath.write_bytes(prior)
    old={**bindings["Q1"],"contract_version":1}
    assert cli("old-binding",packets["Q1"],old,10)["status"]=="blocked"
    native("related-mark",["cognition","mark-dirty","--reason","related read debt","--scope","src/dependency.go","--format","json"])
    for name,path in [("related","src/dependency.go"),("unknown","src/unknown.go")]:
        if name=="unknown":native("unknown-mark",["cognition","mark-dirty","--reason","unknown proof","--scope",path,"--format","json"])
        data=native(name+"native",["cognition","check","--task-packet",packets["Q1"],"--format","json"],10)["data"]
        actual=cli(name+"public",packets["Q1"],expected=10)
        assert actual["data"]["project_cognition"]["data"]["scope_availability"]==data
        assert any(d["relation"]==name for d in data["debt_assessments"])
    assert pin.read_bytes()==before
    (lane/(tag+"-outcomes.json")).write_text(json.dumps(observations,indent=2))
