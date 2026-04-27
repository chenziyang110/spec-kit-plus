# Constitution Profiles

`specify init` can seed one of four built-in constitution profiles through
`--constitution-profile`.

## Profiles

| Profile | Default | Best for | Emphasis |
| --- | --- | --- | --- |
| `product` | Yes | Applications, services, full product repos | Balanced delivery, handbook/project-map navigation, observability, no silent fallbacks |
| `minimal` | No | Small repos, internal tools, low-ceremony teams | Lean workflow, smallest useful change, proportionate verification |
| `library` | No | Packages, CLIs, SDKs, shared modules | Public surface stability, SemVer, release notes, migration guidance |
| `regulated` | No | Security-sensitive, privacy-sensitive, or audited repos | Traceability, security and privacy by default, audit evidence, controlled change |

## Usage

```bash
specify init my-project --ai claude --constitution-profile library
specify init my-project --ai codex --constitution-profile regulated
```

## Behavior

- The selected profile is persisted in `.specify/init-options.json` as
  `constitution_profile`.
- `specify init` rewrites `.specify/templates/constitution-template.md` only
  when that template is still a built-in managed version.
- Existing custom constitution templates are preserved.
- `.specify/memory/constitution.md` is still materialized only when it does not
  already exist.

## Guidance

- Use `product` unless the repository has a clear reason to optimize for a
  different contract.
- Use `minimal` when heavyweight navigation or release governance would be more
  ceremony than signal.
- Use `library` when downstream consumers rely on your public surface.
- Use `regulated` when auditability, privacy, or control evidence is a first
  class requirement.
