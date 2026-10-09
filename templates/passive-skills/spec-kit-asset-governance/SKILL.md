---
name: spec-kit-asset-governance
description: Place and name documents, reports, retained media, and temporary assets while doing authorized project work, including ordinary tasks outside sp or spx workflows. Use before creating or relocating these files, when a changed asset fails naming or location checks, or when the user explicitly requests an asset inventory or migration. Read-only encounters do not authorize moving existing files.
---

# Asset Governance

Continue the current authorized task. Passive skill invocation must not enter any `sp-*` or `spx-*` workflow, create workflow state, or demand a workflow command. Existing workflow files alone do not activate a workflow; retain every gate of a workflow already active in this conversation.

## Create in the right place

1. Identify the asset's purpose and existing owner from the request, applicable project instructions, and nearby live conventions. Reuse the existing canonical document when it owns the requested update. Source code, native tool filenames, registered workflow artifacts, and approved design/evidence packages retain their existing owners and paths.
2. Discover `assets.route` and `assets.check` through the project-local runtime API when their availability is unknown. Run `specify-runtime assets route --purpose <purpose> --path <candidate-project-relative-path> --format json` before retaining a new document, report, media asset, or scratch file. Use `assets explain` only when the returned rule or destination needs explanation. Rules come from the optional project `.asset-policy.json` and deterministic defaults; the customization template is `.specify/templates/asset-policy.json`.
3. Follow the returned action: reuse an existing owner, create at the returned path, use the named specialized owner, or resolve the reported conflict. Do not rename a canonical artifact to satisfy a generic naming rule. Preserve explicit user destinations; report a concrete policy conflict rather than silently changing their request or the policy.
4. Keep disposable output isolated by task and worker using `--purpose temporary --task-id <id> --worker-id <id> --retention <duration>`. Retain only evidence the current task needs; ordinary conversation and read-only inspection create no governance reports, inventories, receipts, or counters.
5. Before claiming the asset portion complete, run `specify-runtime assets check --path <changed-path> --format json`, repeating `--path` for the exact files produced or changed in this task. A write-before check uses `--path-only` and proves only placement, not final contents or references. Keep missing capability, unavailable checks, and violations explicit; never describe them as passed.

## Existing files and delegated work

Reading an old file does not authorize moving, deleting, deduplicating, archiving, or rewriting it. For an explicitly requested cleanup, inspect the bounded set and use the runtime's digest-bound migration plan and apply contracts; preserve live references, contents, ownership, and concurrent edits. Do not run a whole-repository migration opportunistically.

Give each worker the exact output paths or resolver inputs, task/worker identity, retention, write scope, and forbidden paths. Return worker results through the existing inline or runtime result channel. The leader checks the combined changed asset set once; workers do not create competing reports or shared indexes.

If this runtime predates `assets.route` or `assets.check`, follow applicable project conventions for the authorized work, retain original files, and state that deterministic asset verification is unavailable. Do not invoke Python `specify`, create a replacement workflow, or claim successful verification to hide the compatibility gap.
