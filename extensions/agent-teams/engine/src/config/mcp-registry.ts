import { accessSync, constants, existsSync, statSync } from "fs";
import { readFile } from "fs/promises";
import { homedir } from "os";
import { delimiter, isAbsolute, join } from "path";

export interface UnifiedMcpRegistryServer {
  name: string;
  command: string;
  args: string[];
  enabled: boolean;
  startupTimeoutSec?: number;
  approval_mode?: string;
}

export interface UnifiedMcpRegistryLoadResult {
  servers: UnifiedMcpRegistryServer[];
  sourcePath?: string;
  warnings: string[];
}

export interface ClaudeCodeMcpServerConfig {
  command: string;
  args: string[];
  enabled: boolean;
  approval_mode?: string;
}

export interface ClaudeCodeSettingsSyncPlan {
  content?: string;
  added: string[];
  unchanged: string[];
  warnings: string[];
}
interface LoadUnifiedMcpRegistryOptions {
  candidates?: string[];
  commandExists?: (command: string) => boolean;
  homeDir?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function toClaudeCodeMcpServerConfig(
  server: UnifiedMcpRegistryServer,
): ClaudeCodeMcpServerConfig {
  return {
    command: server.command,
    args: [...server.args],
    enabled: server.enabled,
    ...(server.approval_mode !== undefined ? { approval_mode: server.approval_mode } : {}),
  };
}
function normalizeTimeout(
  value: unknown,
  name: string,
  warnings: string[],
): number | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) {
    warnings.push(`registry entry "${name}" has invalid timeout; ignoring timeout`);
    return undefined;
  }
  return Math.floor(value);
}

function normalizeApprovalMode(
  value: unknown,
  name: string,
  warnings: string[],
): string | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== "string") {
    warnings.push(
      `registry entry "${name}" has non-string approval_mode; ignoring approval_mode`,
    );
    return undefined;
  }
  return value;
}

function normalizeEntry(
  name: string,
  value: unknown,
  warnings: string[],
): UnifiedMcpRegistryServer | null {
  if (!isRecord(value)) {
    warnings.push(`registry entry "${name}" is not an object; skipping`);
    return null;
  }

  const command = value.command;
  if (typeof command !== "string" || command.trim().length === 0) {
    warnings.push(`registry entry "${name}" is missing command; skipping`);
    return null;
  }

  const argsValue = value.args;
  if (
    argsValue !== undefined &&
    (!Array.isArray(argsValue) || argsValue.some((item) => typeof item !== "string"))
  ) {
    warnings.push(`registry entry "${name}" has non-string args; skipping`);
    return null;
  }

  const enabledValue = value.enabled;
  if (enabledValue !== undefined && typeof enabledValue !== "boolean") {
    warnings.push(`registry entry "${name}" has non-boolean enabled; skipping`);
    return null;
  }

  const timeoutCandidate =
    value.timeout ?? value.startup_timeout_sec ?? value.startupTimeoutSec;
  const approvalMode = normalizeApprovalMode(value.approval_mode, name, warnings);

  return {
    name,
    command,
    args: (argsValue as string[] | undefined) ?? [],
    enabled: enabledValue ?? true,
    startupTimeoutSec: normalizeTimeout(timeoutCandidate, name, warnings),
    ...(approvalMode !== undefined ? { approval_mode: approvalMode } : {}),
  };
}

function pathEnvValue(): string {
  return process.env.PATH ?? process.env.Path ?? process.env.path ?? "";
}

function windowsExecutableExtensions(): string[] {
  return (process.env.PATHEXT ?? ".COM;.EXE;.BAT;.CMD")
    .split(";")
    .map((extension) => extension.trim())
    .filter(Boolean);
}

function commandPathCandidates(command: string): string[] {
  const trimmed = command.trim();
  if (process.platform !== "win32") return [trimmed];
  if (/\.[^\\/]+$/.test(trimmed)) return [trimmed];
  return [trimmed, ...windowsExecutableExtensions().map((extension) => `${trimmed}${extension}`)];
}

function executableFileExists(path: string): boolean {
  try {
    if (!statSync(path).isFile()) return false;
    if (process.platform !== "win32") {
      accessSync(path, constants.X_OK);
    }
    return true;
  } catch {
    return false;
  }
}

export function commandExistsOnPath(command: string): boolean {
  const trimmed = command.trim();
  if (!trimmed) return false;

  if (isAbsolute(trimmed) || /[\\/]/.test(trimmed)) {
    return commandPathCandidates(trimmed).some((candidate) => executableFileExists(candidate));
  }

  for (const directory of pathEnvValue().split(delimiter)) {
    if (!directory.trim()) continue;
    for (const candidate of commandPathCandidates(trimmed)) {
      if (executableFileExists(join(directory, candidate))) return true;
    }
  }

  return false;
}

export function getUnifiedMcpRegistryCandidates(homeDir = homedir()): string[] {
  return [join(homeDir, ".omx", "mcp-registry.json")];
}

export function getLegacyUnifiedMcpRegistryCandidate(homeDir = homedir()): string {
  return join(homeDir, ".omc", "mcp-registry.json");
}

export async function loadUnifiedMcpRegistry(
  options: LoadUnifiedMcpRegistryOptions = {},
): Promise<UnifiedMcpRegistryLoadResult> {
  const candidates =
    options.candidates ?? getUnifiedMcpRegistryCandidates(options.homeDir);
  const sourcePath = candidates.find((candidate) => existsSync(candidate));
  if (!sourcePath) {
    return { servers: [], warnings: [] };
  }

  const warnings: string[] = [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(await readFile(sourcePath, "utf-8"));
  } catch (error) {
    warnings.push(`failed to parse shared MCP registry at ${sourcePath}: ${String(error)}`);
    return { servers: [], sourcePath, warnings };
  }

  if (!isRecord(parsed)) {
    warnings.push(`shared MCP registry at ${sourcePath} must be a JSON object`);
    return { servers: [], sourcePath, warnings };
  }

  const servers: UnifiedMcpRegistryServer[] = [];
  const commandExists = options.commandExists ?? commandExistsOnPath;
  for (const [name, value] of Object.entries(parsed)) {
    const normalized = normalizeEntry(name, value, warnings);
    if (!normalized) continue;
    if (normalized.enabled && !commandExists(normalized.command)) {
      warnings.push(
        `registry entry "${name}" command "${normalized.command}" was not found; skipping enabled MCP server`,
      );
      continue;
    }
    servers.push(normalized);
  }

  return { servers, sourcePath, warnings };
}

export function planClaudeCodeMcpSettingsSync(
  existingContent: string,
  servers: UnifiedMcpRegistryServer[],
): ClaudeCodeSettingsSyncPlan {
  if (servers.length === 0) {
    return { added: [], unchanged: [], warnings: [] };
  }

  let parsed: unknown = {};
  const trimmed = existingContent.trim();
  if (trimmed.length > 0) {
    try {
      parsed = JSON.parse(existingContent);
    } catch (error) {
      return {
        added: [],
        unchanged: [],
        warnings: [`failed to parse Claude settings.json: ${String(error)}`],
      };
    }
  }

  if (!isRecord(parsed)) {
    return {
      added: [],
      unchanged: [],
      warnings: ["Claude settings.json must contain a JSON object"],
    };
  }

  const currentMcpServers = parsed.mcpServers;
  if (currentMcpServers !== undefined && !isRecord(currentMcpServers)) {
    return {
      added: [],
      unchanged: [],
      warnings: ['Claude settings.json field "mcpServers" must be an object'],
    };
  }

  const nextMcpServers: Record<string, unknown> = {
    ...(currentMcpServers ?? {}),
  };
  const added: string[] = [];
  const unchanged: string[] = [];

  for (const server of servers) {
    if (Object.hasOwn(nextMcpServers, server.name)) {
      unchanged.push(server.name);
      continue;
    }
    nextMcpServers[server.name] = toClaudeCodeMcpServerConfig(server);
    added.push(server.name);
  }

  if (added.length === 0) {
    return { added, unchanged, warnings: [] };
  }

  return {
    content: `${JSON.stringify(
      {
        ...parsed,
        mcpServers: nextMcpServers,
      },
      null,
      2,
    )}\n`,
    added,
    unchanged,
    warnings: [],
  };
}
