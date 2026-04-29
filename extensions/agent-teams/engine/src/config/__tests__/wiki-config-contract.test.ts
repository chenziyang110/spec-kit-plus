import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { loadSurface } from "../../hooks/__tests__/prompt-guidance-test-helpers.js";

describe("project wiki config/generator documentation contract", () => {
  it("documents the dedicated specify_wiki MCP server block", () => {
    const doc = loadSurface("docs/reference/project-wiki.md");
    assert.match(doc, /\[mcp_servers\.specify_wiki\]/);
    assert.match(doc, /dist\/mcp\/wiki-server\.js/);
    assert.match(doc, /`omx setup` \/ the config generator/i);
    assert.match(doc, /bootstrap\/config path should treat `specify_wiki` as a first-party Specify server/i);
  });

  it("documents the Specify runtime storage path instead of legacy OMC storage", () => {
    const doc = loadSurface("docs/reference/project-wiki.md");
    assert.match(doc, /Wiki state is project-local and should live under/i);
    assert.match(doc, /`\.specify\/runtime\/wiki\/\*\.md`/);
    assert.match(doc, /The docs and code should never regress back to `\.omc\/wiki\/`/);
  });
});
