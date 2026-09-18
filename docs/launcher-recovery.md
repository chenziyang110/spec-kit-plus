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
