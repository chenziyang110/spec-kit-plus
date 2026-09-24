# Project launcher recovery

This guide covers the Python machine-local Specify launcher, not permission to
publish a release or replace a project's Go runtime with an unrelated binary.
See [installation](installation.md) for provisioning and
[optimization status](workflow-quality/optimization-status.md) for verification.

## Diagnose without hiding the failure

Keep the project configuration, project wrapper and machine binding files before
recovery. From the project root, use a known trusted Spec Kit Plus installation
to run `check`. Do not edit stored hashes, substitute a PATH-level executable or
delete binding records to turn an inconsistent installation into an unbound one.

A machine binding needs its own recorded Python interpreter and matching package
files. The shared dispatcher can contain another installation's repair hint;
that hint alone is not a dependency of every project. Removing another virtual
environment must not invalidate a healthy selected binding. Removing the selected
binding's own interpreter still makes that binding unavailable.

The checks compare generated entry, invoke and dispatcher contents as well as
recorded hashes and the actual runtime identity response. A changed invoke shim
is not accepted merely because its updated hash matches or it prints the expected
identity. Owned-script symlinks and malformed scripts are rejected. Ordinary
virtual-environment interpreter symlinks remain supported.

## Invalid project configuration

`invalid-project-config` is a blocking compatibility diagnostic. It means
`.specify/config.json` could not be read safely as a regular, non-link UTF-8
JSON object. Malformed JSON, duplicate keys, non-finite values, invalid Unicode,
access errors and special files are not an empty/unconfigured project.

Preserve the configuration and `.specify/bin`, stop concurrent writers, and
inspect the file type and permissions before reading the contents. Do not follow
links or read named pipes as JSON. Restore a known-good regular configuration or
correct the syntax without editing launcher bindings or stored digests. Then run
`check` through the intended trusted installation before resuming `integration
repair`. Do not delete the binding to enable environment/PATH fallback.

The compatibility diagnostic stops at this configuration error rather than
issuing misleading missing-runtime instructions or probing other launchers.
Missing regular configuration remains the existing unbound/bootstrap case; a
dangling configuration link does not. Config readers and both cooperating
launcher writers use the existing safe state reader and preserve invalid inputs.
Other local JSON inspected through the launcher's configuration loader, including
hook settings and integration manifests, now uses the same non-link file checks.

## Unreadable generated guidance

`unreadable-generated-guidance` means a generated workflow document, script,
context file or discovery directory could not be inspected safely. It is a
`repairable-block`, not a finding that the unseen contents are compatible.
Diagnosis reports the affected project-relative path once and continues checking
other readable inputs. Malformed UTF-8, special files and inaccessible paths no
longer abort or silently disappear from this scan. Linked directories are not
traversed; linked assets are left untouched and reported as uninspected.

Preserve the listed path and inspect its file type and permissions before
reading it. Restore the intended ordinary UTF-8 asset or directory through the
trusted installation, merging user modifications deliberately. Do not read pipes,
follow links or delete user content just to silence the diagnostic. Re-run `check`
after recovery. An optional asset that was never present is not an error, but a
file discovered and then lost before reading makes that scan incomplete.

Both launcher checks share one sorted, deduplicated discovery and the resulting
findings. Documents are read once per diagnostic invocation; only findings and
reused helper text are retained, not a persistent cache of whole documents.
A later invocation rereads changed files. This is not a filesystem snapshot,
regular-file size limit, deadline guarantee or installed-CLI performance claim.

## Exact wrapper with missing execution permission

On POSIX hosts, an unchanged project wrapper without execution permission is
reported unavailable. Run `integration repair` through the trusted installation
from the project root, then run `check` again. The wrapper installer can restore
permissions only when the existing contents exactly match its generated form.

Repair republishes that identical content as an independent file before applying
the normal executable mode. It does not chmod another project or an external
backup sharing the old inode. An already executable, identical wrapper is reused.
A failure to write the replacement is reported, not counted as successful repair.

## State path is a pipe, socket, directory or shared lock

The shared local-state readers and writers expect regular files. They reject
named pipes, sockets, directories and other special file types instead of waiting
for a pipe peer or replacing an IPC endpoint with a state file. Machine-binding
and dispatcher metadata readers using these helpers report unavailable when their
metadata path is a pipe; they do not consume the pipe or rewrite it.

Locks must also be regular files with a single hardlink. Initializing a shared
empty lock inode would otherwise modify an unrelated file. A waiter checks that
the lock pathname still identifies its acquired file before entering the protected
operation. A replaced or multiply linked lock is an error, not a reason to retry
work under a different lock. Ordinary hardlinked data files remain readable and
atomic data replacement continues to leave external backups intact.

Stop the cooperating processes and establish why the unexpected file type or
link exists before using the trusted repair path. Preserve user data and IPC
endpoints; do not read a suspect pipe as if it were a JSON file, delete a live
lock to force progress, or replace special files automatically. Descriptor checks
and POSIX nonblocking open narrow specific races but do not provide a general
hostile-writer sandbox, a deadline for every filesystem operation, or a size limit
for regular-file contents. Readers not using these shared helpers are outside
this change.

## Modified wrapper or damaged installation

A user-modified wrapper retains the existing conflict behavior. Back it up,
compare it with the generated template from the intended installation, and merge
changes deliberately. The preserve-conflicting-wrapper path leaves those bytes
and permissions intact; preservation is not a claim that the wrapper can run.

If the selected interpreter or pinned package files disappeared or changed,
restore or repair using the intended trusted installation. A stale repair hint
from another deleted environment is not a reason to modify healthy bindings.
After recovery, verify the selected launcher's runtime identity and re-run the
project compatibility checks before resuming work.

## Shared Hook asset installation

Shared Hook repair now reads packaged assets through the safe file reader and
publishes each destination using an independent atomic byte replacement. A
symbolic-link destination or linked `.specify/bin` parent is refused instead of
redirecting writes outside the project. A regular destination sharing a hardlink
with another file is replaced independently, leaving the other file unchanged.
Directories are not interpreted as copy folders, and damaged packaged links or
special files are reported rather than silently omitted.

The existing `preserve_modified` behavior remains: modified or untracked user
hooks, including final-path links, are retained and reported in the skipped list.
An unmodified manifest-owned hook may be refreshed and its new digest recorded.
The `include_node` selection and the four shipped script contents are unchanged.
Metadata copying and the POSIX executable-bit rule remain in effect.

Read, staging flush and replacement errors leave the current file and its
manifest record unchanged. Metadata or manifest errors after byte replacement
still raise, but the replacement may already exist. Previously completed files
in the same call are not rolled back. Preserve the failed installation, inspect
the reported error and rerun the trusted repair after resolving it; do not treat
an exception as successful installation or delete user hooks to force progress.

This is per-file publication, not a crash-atomic four-file installation or a
hostile-writer sandbox. Concurrent path changes between checks, cross-profile
installation races, full integration initialization and native Windows/macOS
execution remain separate validation boundaries.

## Limits

These are local installation consistency checks, not signatures or a sandbox.
A successful access precheck does not guarantee later execution: filesystem
policy and concurrent changes can still cause an operation to fail. Neither the
probe nor permission repair makes multiple files crash-atomic or provides rollback.
The existing project lock serializes cooperating configuration writers, not every
machine-global dispatcher update or external editor.

The focused regression suite exercises generated scripts and real children on
Linux, using a small instrumented CLI fixture. It is not full `specify init`,
wheel/profile acceptance or native Windows/macOS validation. Existing Windows
script generation and invocation conventions are unchanged by this increment.
