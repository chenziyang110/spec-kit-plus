import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { loadSurface } from "../../hooks/__tests__/prompt-guidance-test-helpers.js";

describe("project wiki config/generator documentation contract", () => {
  it("documents the dedicated omx_wiki MCP server block", () => {
    const doc = loadSurface("docs/reference/project-wiki.md");
    assert.match(doc, /\[mcp_servers\.omx_wiki\]/);
    assert.match(doc, /dist\/mcp\/wiki-server\.js/);
    assert.match(doc, /`omx setup` \/ the config generator/i);
    assert.match(doc, /bootstrap\/config path should treat `omx_wiki` as a first-party OMX server/i);
  });

  it("documents the OMX-native storage path instead of legacy OMC storage", () => {
    const doc = loadSurface("docs/reference/project-wiki.md");
    assert.match(doc, /Wiki state is project-local and should live under/i);
    assert.match(doc, /`\.omx\/wiki\/\*\.md`/);
    assert.match(doc, /The docs and code should never regress back to `\.omc\/wiki\/`/);
  });
});
