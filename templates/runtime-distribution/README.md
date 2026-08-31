# Spec Kit Plus runtime downloads

This repository distributes prebuilt `specify-runtime` binaries and checksums.
It does not contain the product's source code or private development history.

[Download a release](https://github.com/chenziyang110/spec-kit-plus-releases/releases)

## Platforms

| Platform | Release asset |
| --- | --- |
| Windows x64 | `specify-runtime-windows-amd64.exe` |
| Linux x64 | `specify-runtime-linux-amd64` |
| Linux ARM64 | `specify-runtime-linux-arm64` |
| macOS Intel | `specify-runtime-darwin-amd64` |
| macOS Apple Silicon | `specify-runtime-darwin-arm64` |

Download the asset for your platform and `SHA256SUMS` from the same release.
Verify the SHA-256 checksum before running the binary. Prefer a concrete release
tag when you need reproducible installation.

On Windows, use `Get-FileHash -Algorithm SHA256 <downloaded-file>` and compare
the result with the matching row in `SHA256SUMS`. On Linux, use
`sha256sum <downloaded-file>`; on macOS, use `shasum -a 256 <downloaded-file>`.

The runtime is a companion to Spec Kit Plus. Follow the CLI's compatibility
checks; downloading a binary does not guarantee it supports a newer CLI.

GitHub's automatically generated source archives contain only this distribution
repository's documentation, not the product's source code.
