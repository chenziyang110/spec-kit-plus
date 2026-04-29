# Project Wiki Reference

The project wiki is the local, file-backed knowledge surface for the bundled Specify runtime.

## Config

`omx setup` / the config generator installs the first-party wiki MCP server as:

```toml
[mcp_servers.specify_wiki]
command = "node"
args = ["dist/mcp/wiki-server.js"]
enabled = true
startup_timeout_sec = 5
```

The bootstrap/config path should treat `specify_wiki` as a first-party Specify server. Do not recreate the retired `omx_wiki` MCP name in generated config.

## Storage

Wiki state is project-local and should live under `.specify/runtime/wiki/*.md`.
These tools should operate only on `.specify/runtime/wiki/`.
The docs and code should never regress back to `.omc/wiki/`.

## Routing

Prefer `$wiki` for explicit wiki workflows and avoid implicit bare `wiki` noun activation. A plain sentence that mentions a wiki should not silently switch the agent into wiki mode.

## Tools

The MCP surface includes `wiki_ingest`, `wiki_query`, `wiki_read`, `wiki_list`, `wiki_add`, `wiki_delete`, `wiki_lint`, and `wiki_refresh`.

Do **not** add vector embeddings to the wiki implementation. Keep the storage auditable, deterministic, and easy to diff.

## Regression Locks

The approved source-fix regression list is:

- Unicode-safe slugging
- CRLF-safe frontmatter parsing
- single-pass unescape
- punctuation filtering
- CJK + accented-Latin tokenization support
- reserved-file guard
