# Protected external configuration for Do

An existing project build script can read an external local configuration
without copying it into the project. Require runtime capability
`do.protected-inputs.v1` and the installed shared helper
`.specify/scripts/shared/do_protected_process.py` (Python 3.11+).

Set `SPECIFY_OFFICIAL_CONFIG` in the local environment inherited by native
tools before preparing. Its value must be an absolute, readable regular file
outside the project. Keep the value out of tool arguments, checked-in files
and chat messages. For interactive PowerShell setup, the value can be entered
in your own local PowerShell 7 console, outside agent/tool transcripts, with
masked input and without putting the value into command history:

```powershell
$env:SPECIFY_OFFICIAL_CONFIG = Read-Host -MaskInput 'External configuration file'
```

Use a symbolic binding in the compact prepare input:

```json
{
  "agent_id": "build-agent",
  "adapter_id": "codex",
  "goal": "Build a local test package",
  "output_scope": ["output"],
  "command": {
    "operation": "package",
    "argv": ["pwsh", "-NoProfile", "-File", "packets/Build-WebInstaller.ps1", "-ConfigHeader", "{{external:official_config}}"],
    "external_inputs": {
      "official_config": {"environment": "SPECIFY_OFFICIAL_CONFIG"}
    },
    "checks": [{"kind": "file", "result_path": "output/installer.exe"}]
  }
}
```

Full definitions declare the same `external_inputs` field. Tokens occupy an
entire data argument after a fixed project script; command expressions,
executables, script names, working directories and ordinary path parameters
cannot be external bindings. Prepare is read-only. Missing bindings return
the exact field, binding/environment names and how to supply them, without
returning the actual value. This does not create a failed session.

Pass prepare's canonical `start_input` to start. Record next's `started_input`,
refresh next, and pass its `protected_execution` packet unchanged on stdin
to its `execution_argv` from the project root. The local environment must be
inherited; do not expand the symbolic argv in the native tool call. The helper
checks project source hashes and the external file's content/path binding,
then passes the resolved file path directly to the script using a process
argument list. Runtime itself does not execute commands.

Child stdout/stderr are discarded at the process handles, rather than saved
and redacted. The helper returns symbolic argv, opaque identity, exit status
and binding digests. Record those safe facts and the actual native tool call
identity/times, with an empty summary. Protected sessions allow exit-code and
file metadata checks; log, JSON/JUnit content snapshots and native observation
attachments are refused. Recovery and closeout descriptions must be sanitized.
Use the helper's outcome for status: a failed post-check cannot become passed
because the child exited zero. Interrupted calls still require recovery.

Playbooks, sessions and Spec Kit evidence contain binding/environment names,
project-relative source/output names and hashes, never resolved external paths
or configuration contents. The helper does not copy external files. Additional
guards reject accidentally pasted paths/configuration in metadata. A file or
binding change invalidates evidence, including steps allowed to write sources.
Keep configuration immutable for the duration of the operation. Pre/post hash
checks detect observed changes; they do not provide an atomic filesystem view.

Use trusted scripts: they retain their normal filesystem permissions and may
write their own outputs. This mechanism suppresses Spec Kit tool output; it
does not hide operating-system process arguments or control a builder's own
file logging. A timeout/cancellation still requires existing process/effect
inspection and explicit recovery before retrying.
