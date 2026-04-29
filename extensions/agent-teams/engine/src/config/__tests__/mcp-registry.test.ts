import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { chmod, mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import { delimiter, join } from "node:path";
import { tmpdir } from "node:os";
import {
  commandExistsOnPath,
  getUnifiedMcpRegistryCandidates,
  loadUnifiedMcpRegistry,
  planClaudeCodeMcpSettingsSync,
} from "../mcp-registry.js";

describe("unified MCP registry loader", () => {
  it("prefers ~/.omx/mcp-registry.json over ~/.omc/mcp-registry.json", async () => {
    const wd = await mkdtemp(join(tmpdir(), "omx-mcp-registry-"));
    try {
      const omxPath = join(wd, ".omx", "mcp-registry.json");
      const omcPath = join(wd, ".omc", "mcp-registry.json");
      await mkdir(join(wd, ".omx"), { recursive: true });
      await mkdir(join(wd, ".omc"), { recursive: true });

      await writeFile(
        omxPath,
        JSON.stringify({
          eslint: { command: "npx", args: ["@eslint/mcp@latest"], timeout: 11 },
        }),
      );
      await writeFile(
        omcPath,
        JSON.stringify({
          legacy_helper: { command: "legacy-helper", args: ["mcp"] },
        }),
      );

      const result = await loadUnifiedMcpRegistry({
        homeDir: wd,
        commandExists: () => true,
      });
      assert.equal(result.sourcePath, omxPath);
      assert.deepEqual(result.servers.map((server) => server.name), ["eslint"]);
      assert.equal(result.servers[0].startupTimeoutSec, 11);
    } finally {
      await rm(wd, { recursive: true, force: true });
    }
  });

  it("loads a legacy registry when it is passed explicitly as a candidate", async () => {
    const wd = await mkdtemp(join(tmpdir(), "omx-mcp-registry-"));
    try {
      const omcPath = join(wd, ".omc", "mcp-registry.json");
      await mkdir(join(wd, ".omc"), { recursive: true });
      await writeFile(
        omcPath,
        JSON.stringify({
          legacy_helper: { command: "legacy-helper", args: ["mcp"], enabled: false },
        }),
      );

      const result = await loadUnifiedMcpRegistry({
        candidates: [omcPath],
        commandExists: () => true,
      });
      assert.equal(result.sourcePath, omcPath);
      assert.equal(result.servers.length, 1);
      assert.equal(result.servers[0].name, "legacy_helper");
      assert.equal(result.servers[0].enabled, false);
    } finally {
      await rm(wd, { recursive: true, force: true });
    }
  });

  it("skips invalid entries but keeps valid entries from the same file", async () => {
    const wd = await mkdtemp(join(tmpdir(), "omx-mcp-registry-"));
    try {
      const registryPath = join(wd, "registry.json");
      await writeFile(
        registryPath,
        JSON.stringify({
          bad_type: "not-an-object",
          bad_args: { command: "npx", args: [1, 2, 3] },
          good: { command: "npx", args: ["@eslint/mcp@latest"], timeout: 7 },
        }),
      );

      const result = await loadUnifiedMcpRegistry({
        candidates: [registryPath],
        commandExists: () => true,
      });
      assert.equal(result.servers.length, 1);
      assert.equal(result.servers[0].name, "good");
      assert.equal(result.servers[0].startupTimeoutSec, 7);
      assert.equal(result.warnings.length >= 2, true);
    } finally {
      await rm(wd, { recursive: true, force: true });
    }
  });

  it("skips enabled entries whose command is not installed", async () => {
    const wd = await mkdtemp(join(tmpdir(), "omx-mcp-registry-"));
    try {
      const registryPath = join(wd, "registry.json");
      await writeFile(
        registryPath,
        JSON.stringify({
          missing_enabled: { command: "missing-mcp-server", args: ["mcp"] },
          missing_disabled: {
            command: "missing-disabled-mcp-server",
            args: ["mcp"],
            enabled: false,
          },
          good: { command: "npx", args: ["@eslint/mcp@latest"] },
        }),
      );

      const result = await loadUnifiedMcpRegistry({
        candidates: [registryPath],
        commandExists: (command) => command === "npx",
      });

      assert.deepEqual(
        result.servers.map((server) => server.name),
        ["missing_disabled", "good"],
      );
      assert.deepEqual(result.warnings, [
        'registry entry "missing_enabled" command "missing-mcp-server" was not found; skipping enabled MCP server',
      ]);
    } finally {
      await rm(wd, { recursive: true, force: true });
    }
  });

  it("preserves string approval_mode values and warns on non-string ones", async () => {
    const wd = await mkdtemp(join(tmpdir(), "omx-mcp-registry-"));
    try {
      const registryPath = join(wd, "registry.json");
      await writeFile(
        registryPath,
        JSON.stringify({
          eslint: {
            command: "npx",
            args: ["@eslint/mcp@latest"],
            approval_mode: "never",
          },
          invalid_mode: {
            command: "npx",
            args: ["@example/mcp"],
            approval_mode: 42,
          },
        }),
      );

      const result = await loadUnifiedMcpRegistry({
        candidates: [registryPath],
        commandExists: () => true,
      });
      assert.equal(result.servers.length, 2);
      assert.deepEqual(result.servers[0], {
        name: "eslint",
        command: "npx",
        args: ["@eslint/mcp@latest"],
        enabled: true,
        approval_mode: "never",
        startupTimeoutSec: undefined,
      });
      assert.deepEqual(result.servers[1], {
        name: "invalid_mode",
        command: "npx",
        args: ["@example/mcp"],
        enabled: true,
        startupTimeoutSec: undefined,
      });
      assert.deepEqual(result.warnings, [
        'registry entry "invalid_mode" has non-string approval_mode; ignoring approval_mode',
      ]);
    } finally {
      await rm(wd, { recursive: true, force: true });
    }
  });

  it("returns canonical home-based registry candidates", () => {
    const candidates = getUnifiedMcpRegistryCandidates("/tmp/home");
    assert.deepEqual(candidates, [join("/tmp/home", ".omx", "mcp-registry.json")]);
  });

  it("detects executable registry commands from PATH and PATHEXT", async () => {
    const wd = await mkdtemp(join(tmpdir(), "omx-mcp-command-"));
    const previousPath = process.env.PATH;
    const previousPathext = process.env.PATHEXT;
    try {
      await mkdir(wd, { recursive: true });
      const executableName =
        process.platform === "win32" ? "example-mcp.CMD" : "example-mcp";
      const executablePath = join(wd, executableName);
      await writeFile(executablePath, "echo example\n");
      if (process.platform !== "win32") {
        await chmod(executablePath, 0o755);
      } else {
        process.env.PATHEXT = ".CMD;.EXE";
      }

      process.env.PATH = [wd, previousPath].filter(Boolean).join(delimiter);

      assert.equal(commandExistsOnPath("example-mcp"), true);
      assert.equal(commandExistsOnPath(executablePath), true);
    } finally {
      if (typeof previousPath === "string") process.env.PATH = previousPath;
      else delete process.env.PATH;
      if (typeof previousPathext === "string") process.env.PATHEXT = previousPathext;
      else delete process.env.PATHEXT;
      await rm(wd, { recursive: true, force: true });
    }
  });

  it("does not treat directories on PATH as executable MCP commands", async () => {
    const wd = await mkdtemp(join(tmpdir(), "omx-mcp-command-"));
    const previousPath = process.env.PATH;
    try {
      await mkdir(join(wd, "directory-mcp"), { recursive: true });
      process.env.PATH = [wd, previousPath].filter(Boolean).join(delimiter);

      assert.equal(commandExistsOnPath("directory-mcp"), false);
    } finally {
      if (typeof previousPath === "string") process.env.PATH = previousPath;
      else delete process.env.PATH;
      await rm(wd, { recursive: true, force: true });
    }
  });

  it("plans Claude settings sync by adding only missing shared servers", () => {
    const plan = planClaudeCodeMcpSettingsSync(
      JSON.stringify(
        {
          theme: "dark",
          mcpServers: {
            existing_server: {
              command: "custom-existing-server",
              args: ["serve"],
              enabled: true,
            },
          },
        },
        null,
        2,
      ),
      [
        {
          name: "existing_server",
          command: "existing-server",
          args: ["mcp"],
          enabled: true,
        },
        {
          name: "eslint",
          command: "npx",
          args: ["@eslint/mcp@latest"],
          enabled: false,
          startupTimeoutSec: 9,
        },
      ],
    );

    assert.deepEqual(plan.added, ["eslint"]);
    assert.deepEqual(plan.unchanged, ["existing_server"]);
    assert.deepEqual(plan.warnings, []);

    const parsed = JSON.parse(plan.content ?? "{}") as {
      theme?: string;
      mcpServers?: Record<
        string,
        {
          command: string;
          args: string[];
          enabled: boolean;
          approval_mode?: string;
        }
      >;
    };
    assert.equal(parsed.theme, "dark");
    assert.deepEqual(parsed.mcpServers?.existing_server, {
      command: "custom-existing-server",
      args: ["serve"],
      enabled: true,
    });
    assert.deepEqual(parsed.mcpServers?.eslint, {
      command: "npx",
      args: ["@eslint/mcp@latest"],
      enabled: false,
    });
  });

  it("includes approval_mode when adding missing Claude MCP servers", () => {
    const plan = planClaudeCodeMcpSettingsSync(
      JSON.stringify({ mcpServers: {} }, null, 2),
      [
        {
          name: "eslint",
          command: "npx",
          args: ["@eslint/mcp@latest"],
          enabled: false,
          approval_mode: "never",
        },
      ],
    );

    const parsed = JSON.parse(plan.content ?? "{}") as {
      mcpServers?: Record<
        string,
        {
          command: string;
          args: string[];
          enabled: boolean;
          approval_mode?: string;
        }
      >;
    };

    assert.deepEqual(parsed.mcpServers?.eslint, {
      command: "npx",
      args: ["@eslint/mcp@latest"],
      enabled: false,
      approval_mode: "never",
    });
  });

  it('warns when Claude settings.json has a non-object "mcpServers" field', () => {
    const plan = planClaudeCodeMcpSettingsSync(
      JSON.stringify({ mcpServers: [] }),
      [
        {
          name: "eslint",
          command: "npx",
          args: ["@eslint/mcp@latest"],
          enabled: true,
        },
      ],
    );

    assert.equal(plan.content, undefined);
    assert.deepEqual(plan.added, []);
    assert.deepEqual(plan.unchanged, []);
    assert.match(plan.warnings[0] ?? "", /mcpServers/);
  });
});
