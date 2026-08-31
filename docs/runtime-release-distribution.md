# Public runtime distribution

The source repository `chenziyang110/spec-kit-plus` remains private. The separate
public `chenziyang110/spec-kit-plus-releases` repository hosts only distribution
documentation, license notices, and runtime release assets. Never push the source
repository's Git history or source archive to the public repository.

The public repository's README comes from
`templates/runtime-distribution/README.md`; retain the project's existing LICENSE.
GitHub's automatic source ZIP/tar archives refer only to the public documentation
repository, not the private source revision embedded in each binary.

## Publication boundary

Each release contains exactly:

- `specify-runtime-linux-amd64`
- `specify-runtime-linux-arm64`
- `specify-runtime-darwin-amd64`
- `specify-runtime-darwin-arm64`
- `specify-runtime-windows-amd64.exe`
- `SHA256SUMS`

Build from a clean snapshot of one source revision. Use the same concrete version
in the CLI release and binary identity. Preserve the current protocol, complete
capabilities, source revision, and `dirty=false` release provenance checks.
Publish a draft only after all expected assets and checksums are verified.
Do not use GitHub's automatically generated release notes or copy private commit
messages, logs, source files, workflow files, or credentials into public notes.

Both `.github/workflows/release.yml` and
`.github/workflows/release-specify-runtime.yml` publish through
`scripts/publish-runtime-release.py`. The source repository's normal
`GITHUB_TOKEN` cannot publish to another repository. Keep the existing
`release-trigger.yml` source tag/version workflow in the private repository.

## Configure automated publication

This is an account-owner setup step. Do not reuse a broad personal CLI login
token as a durable workflow secret.

1. In GitHub Settings, open Developer settings -> Personal access tokens ->
   Fine-grained tokens -> Generate new token. Set an expiration date and select
   the `chenziyang110` resource owner.
2. Select **Only select repositories** and choose only
   `spec-kit-plus-releases`. Set repository **Contents: Read and write**;
   retain the required Metadata read permission. Do not grant access to the
   private source repository or administration/workflow permissions.
3. In the private source repository, open Settings -> Secrets and variables ->
   Actions. Add repository secret **PUBLIC_RELEASES_TOKEN** with that token.
   Enter the value directly in GitHub's secret form, never in chat, a commit,
   command argument, or plaintext file.
4. Check the account's Billing & plans settings if Actions reports that jobs
   cannot start because of failed payments or a spending limit. Credential setup
   alone does not resolve an Actions billing block.
5. Run the release workflow for the exact source release tag. Verify the run
   completes and all six assets appear in the **public** repository release.

If token creation, authorization, billing, or workflow execution fails, keep
automatic publication marked unavailable; do not claim that editing workflow
files enables a working automation. The account owner can return the workflow
URL and status for follow-up without returning any token.

## Verify a public release

Use an unauthenticated HTTP client to download the Windows asset and SHA256SUMS
from the versioned public URL. Check the hash before execution, then inspect
`version --format json` and `api handshake --format json`. Verify the concrete
version, expected source revision, `dirty=false`, and every required capability.
Run `specify init` in an isolated project with an empty runtime cache and no
runtime override. Confirm it succeeds without source compilation and pins the
project-local `.specify/bin/specify-runtime` entrypoint.

Cloud CI success, local regression success, successful publication, and anonymous
download verification are separate claims. Report any unavailable evidence
explicitly.
